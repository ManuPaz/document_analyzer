import os
from gcp.gcs_client import GCSClient

class DocumentAnalyzer:
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