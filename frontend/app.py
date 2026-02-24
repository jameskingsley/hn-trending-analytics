import streamlit as st
import requests
import pandas as pd
from wordcloud import WordCloud
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

# Page Configuration
st.set_page_config(
    page_title="HN Sentiment Analytics",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Advanced CSS for High-Contrast UI
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: bold !important; font-size: 2rem !important; }
    [data-testid="stMetricLabel"] { color: #A0A0A0 !important; text-transform: uppercase; letter-spacing: 1px; }
    .stMetric { background-color: #1e2130; padding: 20px; border-radius: 8px; border: 1px solid #31333f; }
    .main { background-color: #0e1117; }
    a { text-decoration: none; color: #1f77b4; font-weight: bold; }
    /* Horizontal Divider Color */
    hr { border-color: #31333f !important; }
    </style>
    """, unsafe_allow_html=True)

# Data Fetching
@st.cache_data(ttl=300) # Cache data for 5 minutes
def get_data(limit=100):
    try:
        url = f"http://127.0.0.1:8000/trending?limit={limit}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get("data", [])
        return None
    except Exception:
        return None

# Sidebar
with st.sidebar:
    st.header("Dashboard Controls")
    num_stories = st.slider("Sample Size", 10, 500, 100)
    if st.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
    st.divider()
    st.caption("Infrastructure: Prefect + BigQuery + FastAPI")

# Header
st.title("Hacker News Analytics")
st.markdown("##### Real-time sentiment and topic analysis of the global tech front page.")
st.write("---")

data = get_data(num_stories)

if data:
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # METRICS PANEL 
    avg_sent = df['sentiment'].mean()
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    m_col1.metric("Total Stories", len(df))
    m_col2.metric("Avg Sentiment", f"{avg_sent:.2f}")
    m_col3.metric("Highest Score", int(df['score'].max()))
    m_col4.metric("Status", "Live")

    st.write("###")

    # TREND LINE SECTION 
    st.subheader("Sentiment Timeline")
    trend_df = df.groupby('timestamp')['sentiment'].mean().reset_index().sort_values('timestamp')
    
    fig_trend = px.line(trend_df, x='timestamp', y='sentiment', 
                        line_shape="spline", render_mode="svg")
    fig_trend.update_traces(line_color='#00FF41', line_width=3)
    fig_trend.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color="white"), xaxis_title="Time of Ingestion", yaxis_title="Mean Sentiment"
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    st.write("---")

    # VISUALIZATION ROW 
    v_col1, v_col2 = st.columns([1.2, 0.8])

    with v_col1:
        st.subheader("Topic Heatmap")
        text = " ".join(title for title in df.title)
        if text.strip():
            wc = WordCloud(width=1000, height=500, background_color="#0e1117", 
                           colormap="cool", max_words=100).generate(text)
            fig_wc, ax = plt.subplots(figsize=(12, 6))
            ax.imshow(wc, interpolation='bilinear'); ax.axis("off")
            fig_wc.patch.set_facecolor('#0e1117')
            st.pyplot(fig_wc)
        else:
            st.info("No text data available for WordCloud.")

    with v_col2:
        st.subheader("Mood Distribution")
        df['mood'] = df['sentiment'].apply(lambda x: 'Positive' if x > 0.05 else ('Negative' if x < -0.05 else 'Neutral'))
        mood_counts = df['mood'].value_counts().reset_index()
        fig_bar = px.bar(mood_counts, x='mood', y='count', color='mood',
                         color_discrete_map={'Positive': '#00FF41', 'Neutral': '#707070', 'Negative': '#FF3131'})
        fig_bar.update_layout(showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                              font=dict(color="white"), xaxis_title=None, yaxis_title="Count")
        st.plotly_chart(fig_bar, use_container_width=True)

    st.write("---")

    # --- LIVE FEED ---
    st.subheader("Detailed Sentiment Feed")
    display_df = df.sort_values(by="timestamp", ascending=False)

    for _, row in display_df.iterrows():
        # High-visibility logic
        if row['sentiment'] > 0.05:
            text_color = "#00FF41"
            label = "POSITIVE"
        elif row['sentiment'] < -0.05:
            text_color = "#FF3131"
            label = "NEGATIVE"
        else:
            text_color = "#000000" # Dimmer grey for neutral
            label = "NEUTRAL"

        with st.container():
            st.markdown(f"**[{row['title']}]({row['url']})**")
            st.markdown(
                f"<span style='color:{text_color}; font-weight:bold;'>{label} ({row['sentiment']:.2f})</span> | "
                f"<span style='color:#FFFFFF;'>{row['score']} Upvotes</span> | "
                f"<span style='color:#707070;'>{row['timestamp'].strftime('%H:%M:%S')}</span>", 
                unsafe_allow_html=True
            )
            st.divider()
else:
    st.error("Fatal Error: API Backend Unreachable. Check FastAPI on port 8000.")