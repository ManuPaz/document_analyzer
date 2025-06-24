import os
import json
from document_analyzer.gcp.gcs_client import GCSClient

class DocumentProcessor:
    """
    Analyzes documents stored in a GCS bucket.
    """

    def __init__(self, gcs_client: GCSClient, local_folder: str = "downloads"):
        self.gcs_client = gcs_client
        self.local_folder = local_folder

    def list_documents(self, folder: str):
        """
        Lists all documents in the given GCS folder.
        """
        return self.gcs_client.list_files(folder)

    def download_document(self, gcs_path: str):
        """
        Downloads a document from GCS to a local folder.
        """
        os.makedirs(self.local_folder, exist_ok=True)
        local_path = os.path.join(self.local_folder, os.path.basename(gcs_path))
        blob = self.gcs_client.bucket.blob(gcs_path)
        blob.download_to_filename(local_path)
        return local_path

    def extract_text(self, file_path: str):
        """
        Extracts text from a document (PDF, DOCX, etc.) using LangChain loaders.
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            from langchain.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            docs = loader.load()
            return " ".join([doc.page_content for doc in docs])
        elif ext == ".docx":
            from langchain.document_loaders import Docx2txtLoader
            loader = Docx2txtLoader(file_path)
            docs = loader.load()
            return " ".join([doc.page_content for doc in docs])
        else:
            raise ValueError("Unsupported file type for text extraction.")

    def batch_text(self, text: str, batch_size: int = 1000):
        """
        Splits text into batches of approximately batch_size characters.
        """
        return [text[i:i+batch_size] for i in range(0, len(text), batch_size)]

    def save_batches_to_json(self, batches, original_filename, output_folder="batches"):
        """
        Saves the batches as a JSON file locally.
        Args:
            batches (list): List of text batches.
            original_filename (str): The original file name (to build the output name).
            output_folder (str): Local folder to save the JSON file.
        Returns:
            str: Path to the saved JSON file.
        """
        os.makedirs(output_folder, exist_ok=True)
        base = os.path.splitext(os.path.basename(original_filename))[0]
        output_path = os.path.join(output_folder, f"{base}_batches.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(batches, f, ensure_ascii=False, indent=2)
        return output_path

    def upload_batches_to_gcs(self, local_path, gcs_folder="batches"):
        """
        Uploads the local JSON file with batches to GCS.
        Args:
            local_path (str): Path to the local JSON file.
            gcs_folder (str): Folder in GCS to upload the file.
        Returns:
            str: GCS path where the file was uploaded.
        """
        filename = os.path.basename(local_path)
        destination_blob = os.path.join(gcs_folder, filename)
        self.gcs_client.upload_blob(local_path, destination_blob)
        print(f"Batches uploaded to {destination_blob}")
        return destination_blob

    def save_and_upload_batches(self, batches, original_gcs_path, output_folder="batches"):
        """
        Saves batches to a local JSON file and uploads it to GCS, preserving the folder structure
        but replacing 'raw' with 'batches' at the root.

        Args:
            batches (list): List of text batches.
            original_gcs_path (str): The original GCS path of the document.
            output_folder (str): Local temporary folder to save the JSON file.

        Returns:
            str: GCS path where the file was uploaded.
        """
        # Build the new GCS path for the batches JSON file
        parts = original_gcs_path.split('/')
        if parts and parts[0] == "raw":
            parts[0] = "batches"
        
        base, _ = os.path.splitext(os.path.basename(original_gcs_path))
        batch_filename = f"{base}_batches.json"
        
        # Replace original filename with new batch filename
        if len(parts) > 1:
            gcs_batches_path = os.path.join(*parts[:-1], batch_filename).replace("\\", "/")
        else:
            gcs_batches_path = batch_filename

        # Save locally
        local_path = self.save_batches_to_json(batches, base, output_folder)

        # Upload to the new path in GCS
        self.gcs_client.upload_blob(local_path, gcs_batches_path)
        print(f"Batches uploaded to {gcs_batches_path}")
        os.remove(local_path) # Clean up local file
        return gcs_batches_path 