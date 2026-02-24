import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Kafka Settings 
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC_HN_RAW = "hn-raw-stories"

# BigQuery Settings
BQ_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
BQ_DATASET_ID = "hn_analytics"
BQ_TABLE_ID = "trending_stories"

#  Hacker News API 
HN_BASE_URL = "https://hacker-news.firebaseio.com/v0"

# NLP Settings 
# Sentiment threshold: > 0.05 is positive, < -0.05 is negative
SENTIMENT_THRESHOLD = 0.05