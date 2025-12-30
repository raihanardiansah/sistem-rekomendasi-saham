"""
Script untuk test analisis sentimen
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.nlp.sentiment import SentimentAnalyzer


def test_sentiment():
    """Test sentiment analyzer"""
    print("=" * 50)
    print("Test Sentiment Analyzer")
    print("=" * 50)
    
    analyzer = SentimentAnalyzer()
    
    # Test cases
    test_texts = [
        # Positive
        "BBCA mencatatkan laba bersih yang melonjak signifikan sebesar 20% year on year, saham menguat ke level tertinggi sepanjang sejarah",
        "Analis merekomendasikan strong buy untuk saham TLKM dengan target harga Rp 4.500, prospek dividen menarik",
        "Sektor perbankan bullish setelah laporan keuangan menunjukkan pertumbuhan kredit yang solid",
        
        # Negative
        "Saham GOTO anjlok 10% setelah laporan keuangan menunjukkan kerugian yang membengkak dan cash burn tinggi",
        "Analis merekomendasikan jual untuk saham WIKA karena beban utang yang semakin berat",
        "Sektor properti bearish akibat suku bunga tinggi dan penjualan yang merosot tajam",
        
        # Neutral
        "TLKM melaporkan pendapatan yang relatif stabil di kuartal ini, tidak ada kejutan signifikan",
        "Saham ASII bergerak sideways menunggu rilis laporan keuangan kuartal berikutnya",
        "Pasar saham Indonesia mixed dengan volume perdagangan normal",
        
        # Mixed/Complex
        "Meski ada tekanan dari kenaikan suku bunga, BMRI berhasil membukukan laba yang sangat positif",
        "ADRO untung besar dari harga batubara tinggi, namun risiko transisi energi menjadi ancaman jangka panjang",
    ]
    
    print("\n" + "-" * 50)
    
    for text in test_texts:
        result = analyzer.analyze(text)
        
        # Color code
        if result['sentiment_label'] == 'positif':
            label_display = "🟢 POSITIF"
        elif result['sentiment_label'] == 'negatif':
            label_display = "🔴 NEGATIF"
        else:
            label_display = "🟡 NETRAL"
        
        print(f"\n📝 {text[:70]}...")
        print(f"   {label_display} | Score: {result['sentiment_score']:.4f} | Confidence: {result['confidence']:.2f}")
        
        if result['positive_words']:
            pos_words = [w[0] for w in result['positive_words'][:3]]
            print(f"   ➕ Kata positif: {', '.join(pos_words)}")
        
        if result['negative_words']:
            neg_words = [w[0] for w in result['negative_words'][:3]]
            print(f"   ➖ Kata negatif: {', '.join(neg_words)}")
    
    print("\n" + "=" * 50)
    print("✅ Test selesai!")


if __name__ == "__main__":
    test_sentiment()
