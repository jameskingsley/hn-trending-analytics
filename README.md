# Hacker News Trending Analytics & Ingestion Pipeline
An automated, end-to-end data engineering pipeline that tracks the "vibe" of the tech world. This system scrapes Hacker News, performs sentiment analysis using VADER, stores historical data in Google BigQuery, and serves insights via a FastAPI backend and a Streamlit dashboard.

### The Tech Stack
Orchestration: Prefect (Self-hosted worker within FastAPI).

Storage: Google BigQuery (Serverless Data Warehouse).

Backend: FastAPI (Async Python API).

Frontend: Streamlit (Data Visualization).

Analysis: VADER Sentiment Analysis.

Experiment Tracking: ClearML (Logging metrics and topic clouds).

Deployment: Render (API/Worker) & Streamlit Cloud (UI).

#### Architecture
Ingestion: A Prefect worker runs every 4 hours to fetch the top 100 stories from the HN API.

Processing: Titles are processed for sentiment scores and keyword extraction.

Logging: Batch statistics and WordClouds are pushed to ClearML for monitoring.

Warehouse: Data is appended to a BigQuery table for long-term historical analysis.

Consumption: FastAPI serves the data, which is then visualized in a Streamlit dashboard.

##### Installation & Local Setup
1. Clone the repository
2. Environment Variables
3. Create a .env file in the root directory:

###### Google Credentials
* Place your Google Service Account JSON in config/google_credentials.json. Note: This file is git-ignored for security.
* Install Dependencies
#### Running the Project
* Start the Backend (API + Prefect Worker)
* The Prefect worker starts automatically on lifespan and begins polling for the 4-hour schedule.

* Start the Frontend
# Deployment Notes
##### Render (API)
* Environment Variable: Copy the contents of your google_credentials.json into a Render variable named GOOGLE_CREDENTIALS_JSON.

* Start Command: uvicorn backend.main:app --host 0.0.0.0 --port $PORT

##### Streamlit Cloud
* Connect the repository and point to app.py.

* Ensure the BASE_URL in app.py points to your Render API URL

###### Frontend Dashboard
Link: 