"""
Script untuk inisialisasi database dan load data awal
Jalankan ini sebelum menjalankan aplikasi untuk pertama kali
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from app.database import init_db, get_session, Stock
from app.config import STOCKS_LIST_PATH


def setup_database():
    """Initialize database dan load stock data"""
    print("=" * 50)
    print("Setup Database Sistem Rekomendasi Saham")
    print("=" * 50)
    
    # Initialize tables
    print("\n1. Membuat tabel database...")
    init_db()
    
    # Load stock data
    print("\n2. Memuat data saham...")
    session = get_session()
    
    try:
        # Check if stocks already exist
        existing_count = session.query(Stock).count()
        
        if existing_count > 0:
            print(f"   ⚠️  Database sudah memiliki {existing_count} saham")
            response = input("   Apakah ingin reset dan load ulang? (y/n): ")
            
            if response.lower() == 'y':
                session.query(Stock).delete()
                session.commit()
                print("   ✅ Data saham lama dihapus")
            else:
                print("   ⏭️  Skip loading, menggunakan data existing")
                return
        
        # Load from CSV
        if not os.path.exists(STOCKS_LIST_PATH):
            print(f"   ❌ File tidak ditemukan: {STOCKS_LIST_PATH}")
            return
        
        df = pd.read_csv(STOCKS_LIST_PATH)
        print(f"   📄 Membaca {len(df)} saham dari CSV")
        
        # Insert stocks
        for _, row in df.iterrows():
            stock = Stock(
                kode=row['kode'],
                nama=row['nama'],
                sektor=row.get('sektor', ''),
                sub_sektor=row.get('sub_sektor', ''),
                index_member=row.get('index_member', 'IHSG')
            )
            session.add(stock)
        
        session.commit()
        print(f"   ✅ Berhasil memuat {len(df)} saham ke database")
        
        # Show summary
        print("\n3. Ringkasan data:")
        
        # By sector
        sector_counts = df['sektor'].value_counts()
        print("\n   Saham per Sektor:")
        for sektor, count in sector_counts.head(5).items():
            print(f"   • {sektor}: {count}")
        
        # By index
        print("\n   Saham per Index:")
        lq45_count = len(df[df['index_member'].str.contains('LQ45', na=False)])
        idx30_count = len(df[df['index_member'].str.contains('IDX30', na=False)])
        print(f"   • LQ45: {lq45_count}")
        print(f"   • IDX30: {idx30_count}")
        print(f"   • IHSG (semua): {len(df)}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        session.rollback()
    
    finally:
        session.close()
    
    print("\n" + "=" * 50)
    print("✅ Setup selesai!")
    print("=" * 50)
    print("\nUntuk menjalankan aplikasi:")
    print("  streamlit run app/main.py")


if __name__ == "__main__":
    setup_database()
