from gcp.gcs_client import GCSClient
from gcp.bq_client import BigQueryClient
import sys 
sys.path.append("document_analyzer")
if __name__ == "__main__":
    """
    Example usage of GCSClient and BigQueryClient classes.
    """
    # GCS Example
    # gcs = GCSClient()
    # gcs.upload_blob("local.txt", "folder/remote.txt")

    # BigQuery Example
    # bq = BigQueryClient()
    # for row in bq.query("SELECT * FROM `your-project.your-dataset.your-table` LIMIT 5"):
    #     print(row)
    pass 