"""
Content-Based Filtering Recommender
Rekomendasi saham berdasarkan kemiripan konten berita
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging
from collections import defaultdict

from app.database import get_session, Stock, News, StockAnalysis
from app.nlp.sentiment import get_sentiment_analyzer
from app.nlp.vectorizer import TFIDFVectorizer, StockProfileBuilder
from app.config import RECOMMENDATION_CONFIG

logger = logging.getLogger(__name__)


class ContentBasedRecommender:
    """
    Content-Based Filtering Recommender untuk saham
    
    Sistem ini merekomendasikan saham berdasarkan:
    1. Kemiripan profil berita antar saham
    2. Sentimen berita
    3. Frekuensi dan recency berita
    """
    
    def __init__(self):
        self.session = get_session()
        self.sentiment_analyzer = get_sentiment_analyzer()
        self.vectorizer = TFIDFVectorizer()
        self.profile_builder = StockProfileBuilder()
        
        # Config
        self.top_n = RECOMMENDATION_CONFIG.get("top_n_recommendations", 10)
        self.min_news = RECOMMENDATION_CONFIG.get("min_news_count", 3)
        
        # Cache
        self._stock_profiles: Dict[str, np.ndarray] = {}
        self._stock_sentiments: Dict[str, Dict] = {}
        self._similarity_matrix: Optional[Dict] = None
    
    def analyze_stock(self, stock_code: str, days_back: int = 30) -> Dict:
        """
        Analisis lengkap untuk satu saham
        
        Args:
            stock_code: Kode saham
            days_back: Ambil berita dalam N hari terakhir
            
        Returns:
            Dict dengan hasil analisis
        """
        stock = self.session.query(Stock).filter(
            Stock.kode == stock_code.upper()
        ).first()
        
        if not stock:
            return {"error": f"Stock {stock_code} tidak ditemukan"}
        
        # Get news
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        news_list = self.session.query(News).filter(
            News.stock_id == stock.id,
            News.scraped_at >= cutoff_date
        ).order_by(News.published_date.desc()).all()
        
        if len(news_list) < self.min_news:
            return {
                "stock_code": stock_code,
                "stock_name": stock.nama,
                "warning": f"Berita terlalu sedikit ({len(news_list)} < {self.min_news})",
                "news_count": len(news_list),
                "sentiment": None,
                "recommendation": None
            }
        
        # Analyze sentiment for each news
        sentiments = []
        news_data = []
        
        for news in news_list:
            # Use cached sentiment or analyze
            if news.sentiment_score is not None:
                sentiment_result = {
                    'sentiment_score': news.sentiment_score,
                    'sentiment_label': news.sentiment_label
                }
            else:
                text = f"{news.title} {news.content or ''}"
                sentiment_result = self.sentiment_analyzer.analyze(text)
                
                # Update database
                news.sentiment_score = sentiment_result['sentiment_score']
                news.sentiment_label = sentiment_result['sentiment_label']
            
            sentiments.append(sentiment_result)
            news_data.append({
                'id': news.id,
                'title': news.title,
                'source': news.source,
                'published_date': news.published_date,
                'sentiment_score': sentiment_result['sentiment_score'],
                'sentiment_label': sentiment_result['sentiment_label']
            })
        
        # Commit sentiment updates
        try:
            self.session.commit()
        except:
            self.session.rollback()
        
        # Calculate sentiment summary
        sentiment_summary = self.sentiment_analyzer.get_sentiment_summary(sentiments)
        
        # Build stock profile (TF-IDF vector)
        news_texts = [f"{n.title} {n.content or ''}" for n in news_list]
        
        # Weight by recency (more recent = higher weight)
        weights = self._calculate_recency_weights(news_list)
        profile = self.profile_builder.build_profile_from_news(news_texts, weights)
        
        # Cache profile
        self._stock_profiles[stock_code.upper()] = profile
        self._stock_sentiments[stock_code.upper()] = sentiment_summary
        
        # Get top keywords
        combined_text = " ".join(news_texts)
        keywords = self.vectorizer.get_top_keywords(combined_text, top_n=10)
        
        return {
            "stock_code": stock_code.upper(),
            "stock_name": stock.nama,
            "sektor": stock.sektor,
            "news_count": len(news_list),
            "sentiment": sentiment_summary,
            "keywords": keywords,
            "recent_news": news_data[:5],  # Top 5 recent news
            "analysis_date": datetime.utcnow().isoformat()
        }
    
    def _calculate_recency_weights(self, news_list: List[News]) -> List[float]:
        """
        Hitung weight berdasarkan recency
        Berita lebih baru = weight lebih tinggi
        """
        if not news_list:
            return []
        
        now = datetime.utcnow()
        weights = []
        
        for news in news_list:
            if news.published_date:
                days_old = (now - news.published_date).days
            else:
                days_old = (now - news.scraped_at).days
            
            # Exponential decay: weight = e^(-days/30)
            weight = np.exp(-days_old / 30)
            weights.append(max(weight, 0.1))  # Minimum weight 0.1
        
        # Normalize
        total = sum(weights)
        if total > 0:
            weights = [w / total for w in weights]
        
        return weights
    
    def find_similar_stocks(
        self, 
        stock_code: str, 
        top_n: int = 5,
        exclude_same_sector: bool = False
    ) -> List[Dict]:
        """
        Cari saham yang mirip berdasarkan profil berita
        
        Args:
            stock_code: Kode saham referensi
            top_n: Jumlah rekomendasi
            exclude_same_sector: Exclude saham dari sektor yang sama
            
        Returns:
            List of similar stocks dengan similarity score
        """
        stock_code = stock_code.upper()
        
        # Ensure reference stock is analyzed
        if stock_code not in self._stock_profiles:
            self.analyze_stock(stock_code)
        
        if stock_code not in self._stock_profiles:
            return []
        
        reference_profile = self._stock_profiles[stock_code]
        reference_stock = self.session.query(Stock).filter(
            Stock.kode == stock_code
        ).first()
        
        # Get all other stocks with news
        all_stocks = self.session.query(Stock).all()
        
        similarities = []
        
        for stock in all_stocks:
            if stock.kode == stock_code:
                continue
            
            if exclude_same_sector and stock.sektor == reference_stock.sektor:
                continue
            
            # Analyze if not cached
            if stock.kode not in self._stock_profiles:
                result = self.analyze_stock(stock.kode)
                if "error" in result or "warning" in result:
                    continue
            
            if stock.kode not in self._stock_profiles:
                continue
            
            # Calculate similarity
            other_profile = self._stock_profiles[stock.kode]
            
            # Cosine similarity
            similarity = self._cosine_similarity(reference_profile, other_profile)
            
            if similarity > 0.1:  # Threshold
                similarities.append({
                    "stock_code": stock.kode,
                    "stock_name": stock.nama,
                    "sektor": stock.sektor,
                    "similarity": round(similarity, 4),
                    "sentiment": self._stock_sentiments.get(stock.kode, {})
                })
        
        # Sort by similarity
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        
        return similarities[:top_n]
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Hitung cosine similarity antara dua vector"""
        if vec1 is None or vec2 is None:
            return 0.0
        
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)
    
    def get_recommendations(
        self,
        stock_codes: Optional[List[str]] = None,
        sektor: Optional[str] = None,
        index_filter: Optional[str] = None,
        top_n: int = 10
    ) -> List[Dict]:
        """
        Dapatkan rekomendasi saham
        
        Args:
            stock_codes: Filter specific stocks (optional)
            sektor: Filter by sector (optional)
            index_filter: Filter by index membership (optional)
            top_n: Number of recommendations
            
        Returns:
            List of recommended stocks dengan scores
        """
        from app.recommendation.scoring import RecommendationScorer
        scorer = RecommendationScorer()
        
        # Build query
        query = self.session.query(Stock)
        
        if stock_codes:
            query = query.filter(Stock.kode.in_([s.upper() for s in stock_codes]))
        
        if sektor:
            query = query.filter(Stock.sektor == sektor)
        
        if index_filter:
            query = query.filter(Stock.index_member.contains(index_filter))
        
        stocks = query.all()
        
        recommendations = []
        
        for stock in stocks:
            # Analyze stock
            analysis = self.analyze_stock(stock.kode)
            
            if "error" in analysis or "warning" in analysis:
                continue
            
            # Calculate recommendation score
            score_result = scorer.calculate_score(
                sentiment_summary=analysis['sentiment'],
                news_count=analysis['news_count'],
                recency_days=self._get_latest_news_age(stock.kode)
            )
            
            recommendations.append({
                "stock_code": stock.kode,
                "stock_name": stock.nama,
                "sektor": stock.sektor,
                "sub_sektor": stock.sub_sektor,
                "index_member": stock.index_member,
                "news_count": analysis['news_count'],
                "sentiment": analysis['sentiment'],
                "keywords": analysis['keywords'][:5],
                "score": score_result['total_score'],
                "score_details": score_result,
                "recommendation": score_result['recommendation_label']
            })
        
        # Sort by score
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        return recommendations[:top_n]
    
    def _get_latest_news_age(self, stock_code: str) -> int:
        """Get age of latest news in days"""
        stock = self.session.query(Stock).filter(
            Stock.kode == stock_code.upper()
        ).first()
        
        if not stock:
            return 999
        
        latest_news = self.session.query(News).filter(
            News.stock_id == stock.id
        ).order_by(News.published_date.desc()).first()
        
        if not latest_news or not latest_news.published_date:
            return 999
        
        age = (datetime.utcnow() - latest_news.published_date).days
        return max(0, age)
    
    def get_sector_analysis(self, sektor: str) -> Dict:
        """
        Analisis agregat untuk satu sektor
        
        Args:
            sektor: Nama sektor
            
        Returns:
            Sector analysis summary
        """
        stocks = self.session.query(Stock).filter(
            Stock.sektor == sektor
        ).all()
        
        if not stocks:
            return {"error": f"Sektor '{sektor}' tidak ditemukan"}
        
        sector_sentiments = []
        stock_analyses = []
        
        for stock in stocks:
            analysis = self.analyze_stock(stock.kode)
            
            if "sentiment" in analysis and analysis["sentiment"]:
                sector_sentiments.append(analysis["sentiment"]["avg_score"])
                stock_analyses.append({
                    "stock_code": stock.kode,
                    "stock_name": stock.nama,
                    "sentiment": analysis["sentiment"]["avg_score"],
                    "news_count": analysis["news_count"]
                })
        
        if not sector_sentiments:
            return {
                "sektor": sektor,
                "warning": "Tidak ada data sentimen yang cukup",
                "stock_count": len(stocks)
            }
        
        # Sort by sentiment
        stock_analyses.sort(key=lambda x: x['sentiment'], reverse=True)
        
        return {
            "sektor": sektor,
            "stock_count": len(stocks),
            "avg_sentiment": round(np.mean(sector_sentiments), 4),
            "min_sentiment": round(min(sector_sentiments), 4),
            "max_sentiment": round(max(sector_sentiments), 4),
            "top_stocks": stock_analyses[:5],
            "bottom_stocks": stock_analyses[-5:] if len(stock_analyses) > 5 else []
        }
    
    def close(self):
        """Close database session"""
        self.session.close()


if __name__ == "__main__":
    # Test recommender
    recommender = ContentBasedRecommender()
    
    # Analyze single stock
    print("Analyzing BBCA...")
    result = recommender.analyze_stock("BBCA")
    print(f"Result: {result}")
    
    # Find similar stocks
    print("\nFinding similar stocks to BBCA...")
    similar = recommender.find_similar_stocks("BBCA", top_n=5)
    for s in similar:
        print(f"  {s['stock_code']}: {s['similarity']:.4f}")
    
    recommender.close()
