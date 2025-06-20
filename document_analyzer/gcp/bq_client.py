from google.cloud import bigquery
from .config import Config

class BigQueryClient:
    """
    Google BigQuery client for executing SQL queries in a specific dataset.
    """
    def __init__(self):
        """
        Initializes the BigQuery client.
        """
        self.client = bigquery.Client(project=Config.GCP_PROJECT_ID)
        self.dataset = Config.BQ_DATASET

    def query(self, sql: str):
        """
        Executes a SQL query and returns the result.

        Args:
            sql (str): SQL query string.
        Returns:
            google.cloud.bigquery.table.RowIterator: Query result iterator.
        """
        query_job = self.client.query(sql)
        return query_job.result() 