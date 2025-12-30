"""
TF-IDF Vectorizer - Feature extraction dari teks berita
"""

import json
from typing import List, Dict, Optional, Tuple
import logging
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.nlp.preprocessor import get_preprocessor
from app.config import NLP_CONFIG

logger = logging.getLogger(__name__)


class TFIDFVectorizer:
    """
    TF-IDF Vectorizer untuk ekstraksi fitur dari teks berita
    Digunakan untuk content-based filtering
    """
    
    def __init__(
        self,
        max_features: int = None,
        ngram_range: Tuple[int, int] = None,
        min_df: int = 2,
        max_df: float = 0.95
    ):
        """
        Initialize TF-IDF Vectorizer
        
        Args:
            max_features: Maksimal fitur yang digunakan
            ngram_range: Range n-gram (min, max)
            min_df: Minimum document frequency
            max_df: Maximum document frequency
        """
        self.max_features = max_features or NLP_CONFIG.get("max_features_tfidf", 5000)
        self.ngram_range = ngram_range or NLP_CONFIG.get("ngram_range", (1, 2))
        self.min_df = min_df
        self.max_df = max_df
        
        self.preprocessor = get_preprocessor(use_stemming=True, remove_stopwords=True)
        
        self.vectorizer = TfidfVectorizer(
            max_features=self.max_features,
            ngram_range=self.ngram_range,
            min_df=self.min_df,
            max_df=self.max_df,
            lowercase=True,
            sublinear_tf=True  # Apply sublinear tf scaling
        )
        
        self.is_fitted = False
        self.feature_names = []
    
    def fit(self, texts: List[str]) -> 'TFIDFVectorizer':
        """
        Fit vectorizer dengan corpus teks
        
        Args:
            texts: List of texts
            
        Returns:
            self
        """
        # Preprocess all texts
        processed_texts = [self.preprocessor.preprocess(text) for text in texts]
        
        # Fit vectorizer
        self.vectorizer.fit(processed_texts)
        self.feature_names = self.vectorizer.get_feature_names_out().tolist()
        self.is_fitted = True
        
        logger.info(f"TF-IDF Vectorizer fitted with {len(self.feature_names)} features")
        
        return self
    
    def transform(self, texts: List[str]) -> np.ndarray:
        """
        Transform texts ke TF-IDF vectors
        
        Args:
            texts: List of texts
            
        Returns:
            TF-IDF matrix (sparse)
        """
        if not self.is_fitted:
            raise ValueError("Vectorizer belum di-fit. Panggil fit() terlebih dahulu.")
        
        processed_texts = [self.preprocessor.preprocess(text) for text in texts]
        return self.vectorizer.transform(processed_texts)
    
    def fit_transform(self, texts: List[str]) -> np.ndarray:
        """
        Fit dan transform dalam satu langkah
        
        Args:
            texts: List of texts
            
        Returns:
            TF-IDF matrix
        """
        processed_texts = [self.preprocessor.preprocess(text) for text in texts]
        
        tfidf_matrix = self.vectorizer.fit_transform(processed_texts)
        self.feature_names = self.vectorizer.get_feature_names_out().tolist()
        self.is_fitted = True
        
        logger.info(f"TF-IDF Vectorizer fitted with {len(self.feature_names)} features")
        
        return tfidf_matrix
    
    def get_top_keywords(self, text: str, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Dapatkan top keywords dari satu teks
        
        Args:
            text: Input text
            top_n: Jumlah keywords yang diambil
            
        Returns:
            List of (keyword, score) tuples
        """
        # Untuk single text, gunakan vectorizer khusus dengan min_df=1
        processed_text = self.preprocessor.preprocess(text)
        
        if not processed_text.strip():
            return []
        
        try:
            # Create a simple vectorizer for single document
            simple_vectorizer = TfidfVectorizer(
                max_features=self.max_features,
                ngram_range=self.ngram_range,
                min_df=1,  # Allow words that appear in just 1 doc
                max_df=1.0,  # No upper limit
                lowercase=True
            )
            
            vector = simple_vectorizer.fit_transform([processed_text]).toarray()[0]
            feature_names = simple_vectorizer.get_feature_names_out().tolist()
            
            # Get indices of top scores
            top_indices = vector.argsort()[-top_n:][::-1]
            
            keywords = []
            for idx in top_indices:
                if vector[idx] > 0:
                    keywords.append((feature_names[idx], float(vector[idx])))
            
            return keywords
            
        except Exception as e:
            logger.warning(f"Error extracting keywords: {e}")
            return []
    
    def compute_similarity(self, texts: List[str]) -> np.ndarray:
        """
        Hitung cosine similarity antar semua texts
        
        Args:
            texts: List of texts
            
        Returns:
            Similarity matrix (n x n)
        """
        tfidf_matrix = self.fit_transform(texts)
        similarity_matrix = cosine_similarity(tfidf_matrix)
        
        return similarity_matrix
    
    def find_similar(
        self, 
        query_text: str, 
        corpus_texts: List[str], 
        top_n: int = 5
    ) -> List[Tuple[int, float]]:
        """
        Cari texts yang paling mirip dengan query
        
        Args:
            query_text: Text query
            corpus_texts: Corpus untuk pencarian
            top_n: Jumlah hasil
            
        Returns:
            List of (index, similarity_score) tuples
        """
        # Fit dengan corpus
        corpus_vectors = self.fit_transform(corpus_texts)
        
        # Transform query
        query_vector = self.transform([query_text])
        
        # Compute similarities
        similarities = cosine_similarity(query_vector, corpus_vectors)[0]
        
        # Get top indices
        top_indices = similarities.argsort()[-top_n:][::-1]
        
        results = [(int(idx), float(similarities[idx])) for idx in top_indices]
        
        return results
    
    def vector_to_json(self, vector: np.ndarray) -> str:
        """
        Convert vector ke JSON string untuk storage
        
        Args:
            vector: TF-IDF vector
            
        Returns:
            JSON string
        """
        if hasattr(vector, 'toarray'):
            vector = vector.toarray()
        
        # Only store non-zero values for efficiency
        if len(vector.shape) == 2:
            vector = vector[0]
        
        non_zero_indices = np.nonzero(vector)[0]
        sparse_dict = {
            str(int(idx)): float(vector[idx]) 
            for idx in non_zero_indices
        }
        
        return json.dumps(sparse_dict)
    
    def json_to_vector(self, json_str: str, size: int = None) -> np.ndarray:
        """
        Convert JSON string back ke vector
        
        Args:
            json_str: JSON string dari vector_to_json
            size: Ukuran vector (default: max_features)
            
        Returns:
            numpy array
        """
        size = size or self.max_features
        vector = np.zeros(size)
        
        sparse_dict = json.loads(json_str)
        for idx_str, value in sparse_dict.items():
            idx = int(idx_str)
            if idx < size:
                vector[idx] = value
        
        return vector


class StockProfileBuilder:
    """
    Builder untuk membuat profil saham dari berita
    Profil ini digunakan untuk content-based filtering
    """
    
    def __init__(self):
        self.vectorizer = TFIDFVectorizer()
    
    def build_profile_from_news(
        self, 
        news_texts: List[str],
        weights: Optional[List[float]] = None
    ) -> np.ndarray:
        """
        Bangun profil saham dari kumpulan berita
        
        Args:
            news_texts: List of news content
            weights: Optional weights for each news (e.g., based on recency)
            
        Returns:
            Profile vector
        """
        if not news_texts:
            return np.zeros(self.vectorizer.max_features)
        
        # Transform all news
        tfidf_matrix = self.vectorizer.fit_transform(news_texts)
        
        # Convert to array
        tfidf_array = tfidf_matrix.toarray()
        
        # Apply weights if provided
        if weights:
            weights = np.array(weights).reshape(-1, 1)
            tfidf_array = tfidf_array * weights
        
        # Aggregate: mean of all news vectors
        profile = np.mean(tfidf_array, axis=0)
        
        return profile
    
    def compute_stock_similarity(
        self,
        stock_profiles: Dict[str, np.ndarray]
    ) -> Dict[str, Dict[str, float]]:
        """
        Hitung similarity antar profil saham
        
        Args:
            stock_profiles: Dict of stock_code -> profile_vector
            
        Returns:
            Dict of stock_code -> {other_stock: similarity}
        """
        stock_codes = list(stock_profiles.keys())
        vectors = np.array([stock_profiles[code] for code in stock_codes])
        
        # Compute similarity matrix
        similarity_matrix = cosine_similarity(vectors)
        
        # Convert to dict
        result = {}
        for i, code in enumerate(stock_codes):
            result[code] = {}
            for j, other_code in enumerate(stock_codes):
                if i != j:
                    result[code][other_code] = float(similarity_matrix[i, j])
        
        return result


if __name__ == "__main__":
    # Test vectorizer
    vectorizer = TFIDFVectorizer()
    
    sample_texts = [
        "Bank BCA mencatatkan laba bersih yang meningkat signifikan pada kuartal ketiga",
        "Saham perbankan menguat seiring sentimen positif dari laporan keuangan",
        "Sektor teknologi mengalami koreksi akibat aksi jual investor asing",
        "Harga minyak dunia naik mendorong penguatan saham energi",
        "Bank Mandiri ekspansi kredit ke sektor UMKM dengan bunga kompetitif"
    ]
    
    # Test fit_transform
    tfidf_matrix = vectorizer.fit_transform(sample_texts)
    print(f"TF-IDF Matrix shape: {tfidf_matrix.shape}")
    
    # Test keywords extraction
    print("\nTop keywords for first text:")
    keywords = vectorizer.get_top_keywords(sample_texts[0], top_n=5)
    for kw, score in keywords:
        print(f"  {kw}: {score:.4f}")
    
    # Test similarity
    print("\nSimilarity matrix:")
    sim_matrix = vectorizer.compute_similarity(sample_texts)
    print(sim_matrix.round(3))
    
    # Test find_similar
    print("\nMost similar to 'laba bank meningkat':")
    similar = vectorizer.find_similar("laba bank meningkat", sample_texts, top_n=3)
    for idx, score in similar:
        print(f"  [{idx}] {score:.4f}: {sample_texts[idx][:50]}...")
