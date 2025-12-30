"""
Recommendation Scorer - Sistem scoring untuk rekomendasi saham
"""

from typing import Dict, Optional
import numpy as np
import logging

from app.config import RECOMMENDATION_CONFIG

logger = logging.getLogger(__name__)


class RecommendationScorer:
    """
    Scoring system untuk menghitung skor rekomendasi saham
    
    Score dihitung berdasarkan:
    1. Sentiment Score - Rata-rata sentimen berita
    2. Frequency Score - Jumlah berita (coverage)
    3. Recency Score - Seberapa baru berita terakhir
    4. Consistency Score - Konsistensi sentimen
    """
    
    def __init__(
        self,
        sentiment_weight: float = None,
        frequency_weight: float = None,
        recency_weight: float = None,
        consistency_weight: float = None
    ):
        """
        Initialize scorer dengan weights
        
        Args:
            sentiment_weight: Bobot untuk sentiment score
            frequency_weight: Bobot untuk frequency score
            recency_weight: Bobot untuk recency score
            consistency_weight: Bobot untuk consistency score
        """
        self.sentiment_weight = sentiment_weight or RECOMMENDATION_CONFIG.get("sentiment_weight", 0.4)
        self.frequency_weight = frequency_weight or RECOMMENDATION_CONFIG.get("frequency_weight", 0.2)
        self.recency_weight = recency_weight or RECOMMENDATION_CONFIG.get("recency_weight", 0.2)
        self.consistency_weight = consistency_weight or RECOMMENDATION_CONFIG.get("similarity_weight", 0.2)
        
        # Normalize weights
        total_weight = (
            self.sentiment_weight + 
            self.frequency_weight + 
            self.recency_weight + 
            self.consistency_weight
        )
        
        self.sentiment_weight /= total_weight
        self.frequency_weight /= total_weight
        self.recency_weight /= total_weight
        self.consistency_weight /= total_weight
    
    def calculate_score(
        self,
        sentiment_summary: Dict,
        news_count: int,
        recency_days: int,
        similarity_score: float = 0.0
    ) -> Dict:
        """
        Hitung skor rekomendasi total
        
        Args:
            sentiment_summary: Hasil dari sentiment analyzer
            news_count: Jumlah berita
            recency_days: Usia berita terakhir dalam hari
            similarity_score: Optional similarity score (untuk content-based)
            
        Returns:
            Dict dengan semua scores dan recommendation
        """
        # 1. Sentiment Score (normalize to 0-100)
        avg_sentiment = sentiment_summary.get('avg_score', 0)
        sentiment_score = self._normalize_sentiment(avg_sentiment)
        
        # 2. Frequency Score (more news = higher score, with diminishing returns)
        frequency_score = self._calculate_frequency_score(news_count)
        
        # 3. Recency Score (newer = higher score)
        recency_score = self._calculate_recency_score(recency_days)
        
        # 4. Consistency Score (based on sentiment distribution)
        consistency_score = self._calculate_consistency_score(sentiment_summary)
        
        # Calculate weighted total score (0-100)
        total_score = (
            sentiment_score * self.sentiment_weight +
            frequency_score * self.frequency_weight +
            recency_score * self.recency_weight +
            consistency_score * self.consistency_weight
        )
        
        # Add similarity bonus if provided
        if similarity_score > 0:
            total_score = total_score * 0.9 + (similarity_score * 100) * 0.1
        
        # Determine recommendation label
        recommendation_label = self._get_recommendation_label(total_score, avg_sentiment)
        
        return {
            "total_score": round(total_score, 2),
            "sentiment_score": round(sentiment_score, 2),
            "frequency_score": round(frequency_score, 2),
            "recency_score": round(recency_score, 2),
            "consistency_score": round(consistency_score, 2),
            "recommendation_label": recommendation_label,
            "weights": {
                "sentiment": self.sentiment_weight,
                "frequency": self.frequency_weight,
                "recency": self.recency_weight,
                "consistency": self.consistency_weight
            }
        }
    
    def _normalize_sentiment(self, sentiment: float) -> float:
        """
        Normalize sentiment dari range (-1, 1) ke (0, 100)
        """
        # sentiment: -1 to 1 -> 0 to 100
        normalized = (sentiment + 1) / 2 * 100
        return max(0, min(100, normalized))
    
    def _calculate_frequency_score(self, news_count: int) -> float:
        """
        Hitung frequency score dengan diminishing returns
        
        Formula: score = 100 * (1 - e^(-count/20))
        - 0 news = 0
        - 5 news ≈ 22
        - 10 news ≈ 39
        - 20 news ≈ 63
        - 50 news ≈ 92
        """
        if news_count <= 0:
            return 0
        
        score = 100 * (1 - np.exp(-news_count / 20))
        return min(100, score)
    
    def _calculate_recency_score(self, days: int) -> float:
        """
        Hitung recency score (exponential decay)
        
        Formula: score = 100 * e^(-days/30)
        - 0 days = 100
        - 7 days ≈ 79
        - 14 days ≈ 63
        - 30 days ≈ 37
        - 60 days ≈ 14
        """
        if days <= 0:
            return 100
        
        score = 100 * np.exp(-days / 30)
        return max(0, score)
    
    def _calculate_consistency_score(self, sentiment_summary: Dict) -> float:
        """
        Hitung consistency score berdasarkan distribusi sentimen
        
        Score tinggi jika sentimen konsisten (mostly positive atau mostly negative)
        Score rendah jika sentimen mixed
        """
        total = sentiment_summary.get('total', 0)
        if total == 0:
            return 50  # Neutral
        
        positive = sentiment_summary.get('positive_count', 0)
        negative = sentiment_summary.get('negative_count', 0)
        neutral = sentiment_summary.get('neutral_count', 0)
        
        # Calculate dominance ratio
        max_count = max(positive, negative, neutral)
        dominance = max_count / total
        
        # Higher dominance = more consistent
        consistency = dominance * 100
        
        # Bonus for clear positive/negative trend
        if positive > negative and positive > neutral:
            # Positive dominant - bonus
            consistency = min(100, consistency * 1.1)
        elif negative > positive and negative > neutral:
            # Negative dominant - slight penalty (bearish news is concerning)
            consistency = consistency * 0.9
        
        return consistency
    
    def _get_recommendation_label(self, score: float, sentiment: float) -> str:
        """
        Determine recommendation label based on score and sentiment
        
        Returns: Strong Buy, Buy, Hold, Sell, Strong Sell
        """
        # Kombinasi score dan sentiment untuk label
        if score >= 75 and sentiment > 0.3:
            return "Strong Buy"
        elif score >= 60 and sentiment > 0.1:
            return "Buy"
        elif score >= 40 or (sentiment > -0.2 and sentiment < 0.2):
            return "Hold"
        elif score >= 25 or sentiment > -0.4:
            return "Sell"
        else:
            return "Strong Sell"
    
    def compare_stocks(self, stock_scores: Dict[str, Dict]) -> list:
        """
        Bandingkan multiple stocks dan rank mereka
        
        Args:
            stock_scores: Dict of stock_code -> score_result
            
        Returns:
            Sorted list of stocks by total_score
        """
        ranked = []
        
        for code, scores in stock_scores.items():
            ranked.append({
                "stock_code": code,
                "total_score": scores.get("total_score", 0),
                "recommendation": scores.get("recommendation_label", "Hold"),
                "details": scores
            })
        
        ranked.sort(key=lambda x: x["total_score"], reverse=True)
        
        # Add rank
        for i, item in enumerate(ranked):
            item["rank"] = i + 1
        
        return ranked


class TrendAnalyzer:
    """
    Analisis trend sentimen dari waktu ke waktu
    """
    
    def __init__(self):
        pass
    
    def analyze_sentiment_trend(
        self,
        sentiments_by_date: Dict[str, float]
    ) -> Dict:
        """
        Analisis trend sentimen
        
        Args:
            sentiments_by_date: Dict of date_string -> avg_sentiment
            
        Returns:
            Trend analysis result
        """
        if not sentiments_by_date or len(sentiments_by_date) < 2:
            return {
                "trend": "insufficient_data",
                "direction": 0,
                "strength": 0
            }
        
        # Sort by date
        sorted_dates = sorted(sentiments_by_date.keys())
        values = [sentiments_by_date[d] for d in sorted_dates]
        
        # Simple linear regression for trend
        n = len(values)
        x = np.arange(n)
        
        # Calculate slope
        mean_x = np.mean(x)
        mean_y = np.mean(values)
        
        numerator = sum((x[i] - mean_x) * (values[i] - mean_y) for i in range(n))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Determine trend
        if slope > 0.02:
            trend = "improving"
            direction = 1
        elif slope < -0.02:
            trend = "declining"
            direction = -1
        else:
            trend = "stable"
            direction = 0
        
        # Trend strength (0-1)
        strength = min(1.0, abs(slope) * 10)
        
        return {
            "trend": trend,
            "direction": direction,
            "strength": round(strength, 4),
            "slope": round(slope, 6),
            "start_sentiment": round(values[0], 4),
            "end_sentiment": round(values[-1], 4),
            "avg_sentiment": round(mean_y, 4)
        }


if __name__ == "__main__":
    # Test scorer
    scorer = RecommendationScorer()
    
    # Test cases
    test_cases = [
        {
            "name": "Strong Positive",
            "sentiment": {"avg_score": 0.7, "positive_count": 8, "negative_count": 1, "neutral_count": 1, "total": 10},
            "news_count": 25,
            "recency": 2
        },
        {
            "name": "Moderate Positive",
            "sentiment": {"avg_score": 0.3, "positive_count": 5, "negative_count": 2, "neutral_count": 3, "total": 10},
            "news_count": 15,
            "recency": 7
        },
        {
            "name": "Neutral",
            "sentiment": {"avg_score": 0.0, "positive_count": 3, "negative_count": 3, "neutral_count": 4, "total": 10},
            "news_count": 10,
            "recency": 14
        },
        {
            "name": "Negative",
            "sentiment": {"avg_score": -0.5, "positive_count": 1, "negative_count": 7, "neutral_count": 2, "total": 10},
            "news_count": 20,
            "recency": 3
        }
    ]
    
    print("=" * 60)
    print("Recommendation Scoring Test")
    print("=" * 60)
    
    for tc in test_cases:
        result = scorer.calculate_score(
            sentiment_summary=tc["sentiment"],
            news_count=tc["news_count"],
            recency_days=tc["recency"]
        )
        
        print(f"\n{tc['name']}:")
        print(f"  Total Score: {result['total_score']:.2f}")
        print(f"  Sentiment: {result['sentiment_score']:.2f}")
        print(f"  Frequency: {result['frequency_score']:.2f}")
        print(f"  Recency: {result['recency_score']:.2f}")
        print(f"  Consistency: {result['consistency_score']:.2f}")
        print(f"  Recommendation: {result['recommendation_label']}")
