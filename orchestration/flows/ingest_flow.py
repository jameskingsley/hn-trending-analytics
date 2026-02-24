import requests
import os
import io
import json
import matplotlib.pyplot as plt
from prefect import flow, task
from google.cloud import bigquery
from google.oauth2 import service_account
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
from dotenv import load_dotenv
from clearml import Task
from wordcloud import WordCloud

# Load env variables
load_dotenv()

# Initialize Sentiment Tool
analyzer = SentimentIntensityAnalyzer()

#  Helper for BigQuery Credentials 
def get_bq_client():
    """Matches the logic in main.py for consistent cloud/local auth."""
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        creds_info = json.loads(creds_json)
        credentials = service_account.Credentials.from_service_account_info(creds_info)
        return bigquery.Client(credentials=credentials, project=creds_info.get("project_id"))
    else:
        file_path = "config/google_credentials.json"
        if os.path.exists(file_path):
            return bigquery.Client.from_service_account_json(file_path)
        return None

@task(retries=2, retry_delay_seconds=5)
def fetch_hn_data(limit=15):
    """Fetch top stories from Hacker News."""
    print(f"--- Starting fetch for top {limit} stories ---")
    ids_url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    ids = requests.get(ids_url).json()[:limit]
    
    stories = []
    for i, item_id in enumerate(ids):
        item_url = f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"
        data = requests.get(item_url).json()
        if data and 'title' in data:
            stories.append({
                "id": data.get("id"),
                "title": data.get("title"),
                "url": data.get("url"),
                "score": data.get("score"),
                "sentiment_score": analyzer.polarity_scores(data.get("title"))['compound'],
                "ingested_at": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            })
    return stories

@task
def load_to_bigquery(data):
    """Batch load data into BigQuery using the credential helper."""
    client = get_bq_client()
    if not client:
        print("BigQuery client could not be initialized.")
        return

    table_id = f"{client.project}.hn_analytics.trending_stories"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND",
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
    )

    print(f"--- Batch loading {len(data)} rows to BigQuery ---")
    
    try:
        load_job = client.load_table_from_json(data, table_id, job_config=job_config)
        load_job.result()
        print("Success! Data is now in BigQuery.")
    except Exception as e:
        print(f"Load job failed: {e}")

@flow(name="Hacker News Data Pipeline")
def hn_ingestion_flow():
    # ClearML task management
    cl_task = Task.init(project_name='HN Analytics', task_name='Data Ingestion + Visuals', reuse_last_task_id=False)
    logger = cl_task.get_logger()

    # Fetch Data
    limit = 100
    raw_stories = fetch_hn_data(limit=limit)
    
    if raw_stories:
        # Log Metrics to ClearML
        avg_sentiment = sum(s['sentiment_score'] for s in raw_stories) / len(raw_stories)
        logger.report_scalar("Metrics", "Avg Sentiment", iteration=1, value=avg_sentiment)
        logger.report_scalar("Metrics", "Stories Ingested", iteration=1, value=len(raw_stories))

        # Generate & Log WordCloud
        try:
            text = " ".join(s['title'] for s in raw_stories)
            wc = WordCloud(width=800, height=400, background_color='white').generate(text)
            
            plt.figure(figsize=(10, 5))
            plt.imshow(wc, interpolation='bilinear')
            plt.axis("off")
            
            logger.report_matplotlib_figure(
                title="HN Topic Cloud", 
                series="Daily Cloud", 
                figure=plt, 
                iteration=1
            )
        except Exception as e:
            print(f"Could not generate WordCloud: {e}")

        # Load to BigQuery
        load_to_bigquery(raw_stories)
    
    cl_task.close()
 
if __name__ == "__main__":
    hn_ingestion_flow.serve(
        name="HN-Hourly-Ingestion-Deployment",
        cron="0 */4 * * *", 
        tags=["production", "automation"],
        description="Automated pipeline to fetch HN data, analyze sentiment, and log to BigQuery/ClearML."
    )