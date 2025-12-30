"""
Script untuk test scraping berita
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.scraper.news_manager import NewsManager


def test_scraper():
    """Test news scraper"""
    print("=" * 50)
    print("Test News Scraper")
    print("=" * 50)
    
    manager = NewsManager()
    
    # Test stocks
    test_stocks = ["BBCA", "TLKM", "ASII"]
    
    for stock in test_stocks:
        print(f"\n🔍 Mengambil berita untuk {stock}...")
        stats = manager.update_news_for_stock(stock, max_per_source=3)
        
        print(f"   Total ditemukan: {stats['total_found']}")
        print(f"   Baru disimpan: {stats['new_saved']}")
        print(f"   Duplikat: {stats['duplicates']}")
        
        if stats['sources']:
            for source, data in stats['sources'].items():
                print(f"   • {source}: {data['saved']}/{data['found']}")
    
    # Show stats
    print("\n📊 Statistik Database:")
    db_stats = manager.get_news_stats()
    print(f"   Total berita: {db_stats['total_news']}")
    print(f"   Teranalisis: {db_stats['analyzed_news']}")
    
    manager.close()
    print("\n✅ Test selesai!")


if __name__ == "__main__":
    test_scraper()
