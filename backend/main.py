import os
import json
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from prefect.runner import Runner

# Load local .env for development
load_dotenv()

# --- BigQuery Client Helper ---
def get_bq_client():
    creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        try:
            creds_info = json.loads(creds_json)
            credentials = service_account.Credentials.from_service_account_info(creds_info)
            return bigquery.Client(credentials=credentials, project=creds_info.get("project_id"))
        except Exception as e:
            print(f"❌ Error loading credentials from ENV: {e}")
            return None
    else:
        file_path = "config/google_credentials.json"
        if os.path.exists(file_path):
            return bigquery.Client.from_service_account_json(file_path)
        return None

# --- Background Task for Prefect Worker ---
async def run_prefect_worker():
    """Starts the Prefect worker inside the FastAPI process."""
    try:
        from orchestration.flows.ingest_flow import hn_ingestion_flow
        
        print("🚀 Prefect Worker: Initializing Runner...")
        # Create the runner
        runner = Runner(name="hn-analytics-runner")
        
        # Deploy the flow to the runner
        # Note: We must await this to avoid the "coroutine never awaited" warning
        await runner.add_flow(
            hn_ingestion_flow,
            name="HN-Hourly-Ingestion-Deployment",
            cron="0 */4 * * *",
            tags=["production"]
        )
        
        print("✅ Prefect Worker: Polling for scheduled runs...")
        # Start the runner - this keeps running in the background task
        await runner.start()
        
    except Exception as e:
        print(f"❌ Prefect Worker Failed: {e}")

# --- Lifespan Management ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize BigQuery
    global client
    client = get_bq_client()
    
    # Start the worker in the background
    # We don't await this here, because we want the API to continue starting
    bg_task = asyncio.create_task(run_prefect_worker())
    
    yield
    
    # Cleanup
    if client:
        client.close()
    bg_task.cancel()

app = FastAPI(title="Hacker News Analytics API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "online", "message": "API & Worker are live!"}

@app.get("/trending")
def get_trending(limit: int = 10):
    if not client:
        return {"error": "BigQuery client not initialized."}
    
    query = f"""
        SELECT id, title, url, score, sentiment_score, ingested_at
        FROM `{client.project}.hn_analytics.trending_stories`
        ORDER BY ingested_at DESC, score DESC
        LIMIT {limit}
    """
    try:
        query_job = client.query(query)
        results = query_job.result()
        stories = [{
            "id": row.id, "title": row.title, "url": row.url, "score": row.score,
            "sentiment": round(row.sentiment_score, 2) if row.sentiment_score is not None else 0,
            "timestamp": row.ingested_at.strftime("%Y-%m-%d %H:%M:%S")
        } for row in results]
        return {"total": len(stories), "data": stories}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000)