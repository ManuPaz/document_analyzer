from google.cloud import storage
from .config import Config

class GCSClient:
    """
    Google Cloud Storage client for file operations in a specific bucket.
    """
    def __init__(self, bucket_name: str = None):
        """
        Initializes the GCS client and sets the target bucket.
        
        Args:
            bucket_name (str, optional): Name of the GCS bucket to use. 
                                       If None, uses the default bucket from config.
        """
        self.client = storage.Client(project=Config.GCP_PROJECT_ID)
        
        # Use provided bucket or default from config
        if bucket_name is not None:
            self.bucket = self.client.bucket(bucket_name)
        else:
            self.bucket = self.client.bucket(Config.GCS_BUCKET)
        
        # Store bucket name for reference
        self.bucket_name = bucket_name or Config.GCS_BUCKET

    def upload_blob(self, source_file_name: str, destination_blob_name: str) -> None:
        """
        Uploads a file to the configured GCS bucket.

        Args:
            source_file_name (str): Path to the local file to upload.
            destination_blob_name (str): Destination path in the bucket.
        """
        blob = self.bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)
        print(f"File {source_file_name} uploaded to gs://{self.bucket_name}/{destination_blob_name}.")

    def list_files(self, folder: str = ""):
        """
        Lists all files in the given folder of the GCS bucket.
        Args:
            folder (str): The folder path in the bucket.
        Returns:
            list: List of file names (str).
        """
        blobs = self.bucket.list_blobs(prefix=folder)
        return [blob.name for blob in blobs if not blob.name.endswith("/")]
    
    def get_bucket_name(self) -> str:
        """
        Returns the name of the currently configured bucket.
        
        Returns:
            str: Name of the bucket being used.
        """
        return self.bucket_name 