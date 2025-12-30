# 📈 Sistem Rekomendasi Saham

Sistem rekomendasi saham berbasis **Content-Based Filtering** yang menganalisis berita untuk memberikan rekomendasi investasi.

## 🚀 Fitur

- ✅ Pilih saham berdasarkan kode/nama
- ✅ Filter berdasarkan index (IHSG, LQ45, IDX30)
- ✅ Scraping berita dari portal berita Indonesia
- ✅ Analisis sentimen berita (Bahasa Indonesia)
- ✅ Rekomendasi berbasis content-based filtering
- ✅ Visualisasi data dan insight

## 📋 Persyaratan

- Python 3.9+
- pip (Python package manager)

## ⚙️ Instalasi

1. **Clone atau buka folder proyek**

2. **Buat virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Aktifkan virtual environment**
   
   Windows:
   ```bash
   venv\Scripts\activate
   ```
   
   Linux/Mac:
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Inisialisasi database**
   ```bash
   python -m app.database
   ```

## 🎮 Menjalankan Aplikasi

```bash
streamlit run app/main.py
```

Aplikasi akan terbuka di browser: `http://localhost:8501`

## 📁 Struktur Proyek

```
sistem-rekomendasi-saham/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entry point Streamlit
│   ├── config.py            # Konfigurasi
│   ├── database.py          # Database models
│   ├── scraper/             # News scraper
│   ├── nlp/                 # NLP processing
│   ├── recommendation/      # Recommendation engine
│   └── data/
│       ├── stocks.db        # SQLite database
│       └── stocks_list.csv  # Daftar saham
├── requirements.txt
└── README.md
```

## 🔧 Konfigurasi

Edit `app/config.py` untuk menyesuaikan:
- Sumber berita
- Parameter NLP
- Bobot rekomendasi

## 📊 Metode yang Digunakan

1. **Sentiment Analysis** - Analisis sentimen berita Bahasa Indonesia
2. **TF-IDF** - Ekstraksi fitur dari teks berita
3. **Cosine Similarity** - Mengukur kemiripan antar saham
4. **Scoring Algorithm** - Menghitung skor rekomendasi

## 📝 Lisensi

MIT License
