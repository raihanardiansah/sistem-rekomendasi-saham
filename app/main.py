"""
Sistem Rekomendasi Saham - Main Application
Streamlit UI untuk interaksi dengan sistem
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Import modules
from app.config import UI_CONFIG
from app.database import init_db, get_session, Stock, News, StockAnalysis
from app.scraper.news_manager import NewsManager
from app.recommendation.content_based import ContentBasedRecommender

# Page config
st.set_page_config(
    page_title=UI_CONFIG["page_title"],
    page_icon=UI_CONFIG["page_icon"],
    layout=UI_CONFIG["layout"],
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    .positive {
        color: #28a745;
        font-weight: bold;
    }
    .negative {
        color: #dc3545;
        font-weight: bold;
    }
    .neutral {
        color: #6c757d;
        font-weight: bold;
    }
    .recommendation-strong-buy {
        background-color: #28a745;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        font-weight: bold;
    }
    .recommendation-buy {
        background-color: #7cb342;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        font-weight: bold;
    }
    .recommendation-hold {
        background-color: #ffc107;
        color: black;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        font-weight: bold;
    }
    .recommendation-sell {
        background-color: #ff7043;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        font-weight: bold;
    }
    .recommendation-strong-sell {
        background-color: #dc3545;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 5px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_stock_list():
    """Load stock list from database"""
    session = get_session()
    stocks = session.query(Stock).order_by(Stock.kode).all()
    session.close()
    return stocks


@st.cache_resource
def init_database():
    """Initialize database"""
    init_db()
    # Load stocks from CSV if empty
    session = get_session()
    count = session.query(Stock).count()
    
    if count == 0:
        # Load from CSV
        try:
            from app.config import STOCKS_LIST_PATH
            df = pd.read_csv(STOCKS_LIST_PATH)
            
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
            st.success(f"✅ Loaded {len(df)} stocks into database")
        except Exception as e:
            st.error(f"Error loading stocks: {e}")
            session.rollback()
    
    session.close()


def render_sidebar():
    """Render sidebar dengan filters"""
    st.sidebar.markdown("## 🎯 Filter & Pengaturan")
    
    # Get stocks
    stocks = get_stock_list()
    stock_codes = [s.kode for s in stocks]
    stock_options = {f"{s.kode} - {s.nama}": s.kode for s in stocks}
    
    # Stock selection
    st.sidebar.markdown("### 📊 Pilih Saham")
    selected_display = st.sidebar.multiselect(
        "Pilih saham untuk dianalisis:",
        options=list(stock_options.keys()),
        default=[],
        help="Pilih satu atau lebih saham"
    )
    selected_stocks = [stock_options[s] for s in selected_display]
    
    # Search by code
    search_code = st.sidebar.text_input(
        "Atau cari kode saham:",
        placeholder="Contoh: BBCA",
        help="Ketik kode saham"
    ).upper()
    
    if search_code and search_code in stock_codes:
        if search_code not in selected_stocks:
            selected_stocks.append(search_code)
    
    # Sector filter
    st.sidebar.markdown("### 🏢 Filter Sektor")
    sectors = list(set([s.sektor for s in stocks if s.sektor]))
    selected_sector = st.sidebar.selectbox(
        "Filter berdasarkan sektor:",
        options=["Semua Sektor"] + sorted(sectors),
        index=0
    )
    
    # Index filter
    st.sidebar.markdown("### 📈 Filter Index")
    index_options = ["Semua Index", "IHSG", "LQ45", "IDX30"]
    selected_index = st.sidebar.selectbox(
        "Filter berdasarkan index:",
        options=index_options,
        index=0
    )
    
    # News settings
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Pengaturan")
    
    max_news = st.sidebar.slider(
        "Maksimal berita per saham:",
        min_value=5,
        max_value=30,
        value=10,
        step=5
    )
    
    days_back = st.sidebar.slider(
        "Analisis berita (hari):",
        min_value=7,
        max_value=90,
        value=30,
        step=7
    )
    
    return {
        "selected_stocks": selected_stocks,
        "selected_sector": selected_sector if selected_sector != "Semua Sektor" else None,
        "selected_index": selected_index if selected_index != "Semua Index" else None,
        "max_news": max_news,
        "days_back": days_back
    }


def render_news_update_section():
    """Section untuk update berita"""
    st.markdown("## 🔄 Update Berita")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        stocks = get_stock_list()
        stock_options = {f"{s.kode} - {s.nama}": s.kode for s in stocks}
        
        update_stocks = st.multiselect(
            "Pilih saham untuk update berita:",
            options=list(stock_options.keys()),
            default=[],
            key="update_stocks"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        update_button = st.button("🔄 Update Berita", type="primary", use_container_width=True)
    
    if update_button and update_stocks:
        selected_codes = [stock_options[s] for s in update_stocks]
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        manager = NewsManager()
        
        try:
            all_stats = []
            for i, code in enumerate(selected_codes):
                status_text.text(f"Mengambil berita untuk {code}...")
                stats = manager.update_news_for_stock(code, max_per_source=5)
                all_stats.append(stats)
                progress_bar.progress((i + 1) / len(selected_codes))
            
            # Show results
            total_new = sum(s['new_saved'] for s in all_stats)
            total_found = sum(s['total_found'] for s in all_stats)
            
            st.success(f"✅ Selesai! Ditemukan {total_found} berita, {total_new} berita baru disimpan.")
            
            # Show details
            with st.expander("📋 Detail Update"):
                for stats in all_stats:
                    st.write(f"**{stats['stock_code']}**: {stats['new_saved']} baru dari {stats['total_found']} ditemukan")
        
        except Exception as e:
            st.error(f"❌ Error: {e}")
        
        finally:
            manager.close()
            status_text.empty()
    
    elif update_button:
        st.warning("⚠️ Pilih minimal satu saham untuk update berita")


def render_stock_analysis(stock_code: str, recommender: ContentBasedRecommender, days_back: int):
    """Render analisis untuk satu saham"""
    
    with st.spinner(f"Menganalisis {stock_code}..."):
        analysis = recommender.analyze_stock(stock_code, days_back=days_back)
    
    if "error" in analysis:
        st.error(f"❌ {analysis['error']}")
        return
    
    if "warning" in analysis:
        st.warning(f"⚠️ {analysis['warning']}")
        return
    
    # Header
    st.markdown(f"### {analysis['stock_code']} - {analysis['stock_name']}")
    st.caption(f"Sektor: {analysis.get('sektor', 'N/A')}")
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    sentiment = analysis['sentiment']
    
    with col1:
        sentiment_color = "🟢" if sentiment['avg_score'] > 0.2 else "🔴" if sentiment['avg_score'] < -0.2 else "🟡"
        st.metric(
            label="Sentimen Rata-rata",
            value=f"{sentiment_color} {sentiment['avg_score']:.2f}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="Jumlah Berita",
            value=analysis['news_count']
        )
    
    with col3:
        st.metric(
            label="Positif / Negatif",
            value=f"{sentiment['positive_count']} / {sentiment['negative_count']}"
        )
    
    with col4:
        st.metric(
            label="Netral",
            value=sentiment['neutral_count']
        )
    
    # Sentiment distribution chart
    col1, col2 = st.columns(2)
    
    with col1:
        # Pie chart
        fig_pie = go.Figure(data=[go.Pie(
            labels=['Positif', 'Negatif', 'Netral'],
            values=[sentiment['positive_count'], sentiment['negative_count'], sentiment['neutral_count']],
            marker_colors=['#28a745', '#dc3545', '#6c757d'],
            hole=0.4
        )])
        fig_pie.update_layout(
            title="Distribusi Sentimen",
            height=300,
            showlegend=True
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Keywords
        st.markdown("**🔑 Keywords Utama:**")
        keywords = analysis.get('keywords', [])
        if keywords:
            for kw, score in keywords[:8]:
                st.write(f"• {kw} ({score:.3f})")
        else:
            st.write("Tidak ada keywords")
    
    # Recent news
    st.markdown("**📰 Berita Terbaru:**")
    recent_news = analysis.get('recent_news', [])
    
    if recent_news:
        for news in recent_news[:5]:
            sentiment_badge = "🟢" if news['sentiment_label'] == 'positif' else "🔴" if news['sentiment_label'] == 'negatif' else "🟡"
            
            date_str = news['published_date'].strftime('%d %b %Y') if news['published_date'] else 'N/A'
            
            st.markdown(f"""
            {sentiment_badge} **{news['title'][:80]}{'...' if len(news['title']) > 80 else ''}**  
            <small>📅 {date_str} | 📰 {news['source']} | Score: {news['sentiment_score']:.2f}</small>
            """, unsafe_allow_html=True)
    else:
        st.info("Tidak ada berita terbaru")


def render_recommendations(filters: dict):
    """Render rekomendasi saham"""
    st.markdown("## 🎯 Rekomendasi Saham")
    
    recommender = ContentBasedRecommender()
    
    try:
        with st.spinner("Menganalisis dan membuat rekomendasi..."):
            recommendations = recommender.get_recommendations(
                stock_codes=filters['selected_stocks'] if filters['selected_stocks'] else None,
                sektor=filters['selected_sector'],
                index_filter=filters['selected_index'],
                top_n=10
            )
        
        if not recommendations:
            st.warning("⚠️ Tidak ada rekomendasi yang tersedia. Pastikan sudah ada berita di database.")
            return
        
        # Display recommendations
        for i, rec in enumerate(recommendations):
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([1, 2, 1.5, 1.5, 1.5])
                
                with col1:
                    st.markdown(f"### #{i+1}")
                
                with col2:
                    st.markdown(f"**{rec['stock_code']}**")
                    st.caption(rec['stock_name'][:30])
                
                with col3:
                    sentiment = rec['sentiment']
                    sentiment_color = "positive" if sentiment['avg_score'] > 0.2 else "negative" if sentiment['avg_score'] < -0.2 else "neutral"
                    st.markdown(f"<span class='{sentiment_color}'>Sentimen: {sentiment['avg_score']:.2f}</span>", unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"**Score: {rec['score']:.1f}**")
                    st.caption(f"{rec['news_count']} berita")
                
                with col5:
                    label = rec['recommendation']
                    label_class = f"recommendation-{label.lower().replace(' ', '-')}"
                    st.markdown(f"<span class='{label_class}'>{label}</span>", unsafe_allow_html=True)
                
                st.markdown("---")
        
        # Visualization
        st.markdown("### 📊 Visualisasi Skor")
        
        df_rec = pd.DataFrame([{
            'Kode': r['stock_code'],
            'Score': r['score'],
            'Sentimen': r['sentiment']['avg_score'],
            'Jumlah Berita': r['news_count'],
            'Rekomendasi': r['recommendation']
        } for r in recommendations])
        
        # Bar chart
        fig_bar = px.bar(
            df_rec,
            x='Kode',
            y='Score',
            color='Sentimen',
            color_continuous_scale=['red', 'yellow', 'green'],
            title='Skor Rekomendasi per Saham'
        )
        fig_bar.update_layout(height=400)
        st.plotly_chart(fig_bar, use_container_width=True)
        
        # Scatter plot
        fig_scatter = px.scatter(
            df_rec,
            x='Sentimen',
            y='Score',
            size='Jumlah Berita',
            color='Rekomendasi',
            text='Kode',
            title='Sentimen vs Score',
            color_discrete_map={
                'Strong Buy': '#28a745',
                'Buy': '#7cb342',
                'Hold': '#ffc107',
                'Sell': '#ff7043',
                'Strong Sell': '#dc3545'
            }
        )
        fig_scatter.update_traces(textposition='top center')
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)
    
    finally:
        recommender.close()


def render_similar_stocks(stock_code: str):
    """Render saham serupa"""
    st.markdown(f"### 🔄 Saham Serupa dengan {stock_code}")
    
    recommender = ContentBasedRecommender()
    
    try:
        with st.spinner("Mencari saham serupa..."):
            similar = recommender.find_similar_stocks(stock_code, top_n=5)
        
        if not similar:
            st.info("Tidak ditemukan saham serupa. Pastikan ada berita yang cukup.")
            return
        
        for s in similar:
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**{s['stock_code']}** - {s['stock_name']}")
            
            with col2:
                st.write(f"Similarity: {s['similarity']:.2%}")
            
            with col3:
                if s.get('sentiment'):
                    st.write(f"Sentimen: {s['sentiment'].get('avg_score', 0):.2f}")
    
    finally:
        recommender.close()


def main():
    """Main application"""
    
    # Initialize database
    init_database()
    
    # Header
    st.markdown('<p class="main-header">📈 Sistem Rekomendasi Saham</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Content-Based Filtering dengan Analisis Berita</p>', unsafe_allow_html=True)
    
    # Sidebar
    filters = render_sidebar()
    
    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 Rekomendasi",
        "📊 Analisis Saham",
        "🔄 Update Berita",
        "📈 Statistik"
    ])
    
    with tab1:
        render_recommendations(filters)
    
    with tab2:
        st.markdown("## 📊 Analisis Detail Saham")
        
        if filters['selected_stocks']:
            recommender = ContentBasedRecommender()
            
            try:
                for stock_code in filters['selected_stocks']:
                    with st.expander(f"📊 {stock_code}", expanded=True):
                        render_stock_analysis(stock_code, recommender, filters['days_back'])
                        
                        st.markdown("---")
                        render_similar_stocks(stock_code)
            
            finally:
                recommender.close()
        else:
            st.info("👈 Pilih saham di sidebar untuk melihat analisis detail")
    
    with tab3:
        render_news_update_section()
    
    with tab4:
        st.markdown("## 📈 Statistik Database")
        
        session = get_session()
        
        # Stock stats
        total_stocks = session.query(Stock).count()
        total_news = session.query(News).count()
        analyzed_news = session.query(News).filter(News.sentiment_score.isnot(None)).count()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Saham", total_stocks)
        
        with col2:
            st.metric("Total Berita", total_news)
        
        with col3:
            st.metric("Berita Teranalisis", analyzed_news)
        
        # News by source
        from sqlalchemy import func
        source_stats = session.query(
            News.source,
            func.count(News.id)
        ).group_by(News.source).all()
        
        if source_stats:
            st.markdown("### Berita per Sumber")
            df_source = pd.DataFrame(source_stats, columns=['Sumber', 'Jumlah'])
            
            fig = px.pie(df_source, values='Jumlah', names='Sumber', title='Distribusi Berita per Sumber')
            st.plotly_chart(fig, use_container_width=True)
        
        # News by sector
        sector_stats = session.query(
            Stock.sektor,
            func.count(News.id)
        ).join(News).group_by(Stock.sektor).all()
        
        if sector_stats:
            st.markdown("### Berita per Sektor")
            df_sector = pd.DataFrame(sector_stats, columns=['Sektor', 'Jumlah'])
            df_sector = df_sector.sort_values('Jumlah', ascending=True)
            
            fig = px.bar(df_sector, x='Jumlah', y='Sektor', orientation='h', title='Jumlah Berita per Sektor')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        session.close()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<p style='text-align: center; color: #666;'>Sistem Rekomendasi Saham v1.0 | "
        "Content-Based Filtering dengan NLP</p>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
