import os
from dotenv import load_dotenv
load_dotenv()
class Config:
    """
    Loads and provides access to environment variables required for Google Cloud services.
    Raises an error if any required variable is missing.
    """
    load_dotenv()
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
    GCS_BUCKET = os.getenv("GCS_BUCKET")
    BQ_DATASET = os.getenv("BQ_DATASET")
    GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    required_vars = [GCP_PROJECT_ID, GCS_BUCKET, BQ_DATASET, GOOGLE_APPLICATION_CREDENTIALS]
    if not all(required_vars):
        raise ValueError("Missing required environment variables for Google Cloud configuration.") 