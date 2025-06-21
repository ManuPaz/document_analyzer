import sys
import sys 
sys.path.append("document_analyzer")
from urllib.parse import urlparse
from gcp.gcs_client import GCSClient
from document_analyzer.ai.document_downloader import DocumentDownloader

def build_gcs_folder(url: str) -> str:
    """
    Constructs the GCS folder path using the URL, following the convention:
    raw/application/domain, where domain is extracted from the URL.
    Removes 'https', 'http', 'www.' and '.com' as specified.
    """
    parsed = urlparse(url)
    # Remove 'www.' and '.com' from netloc
    domain = parsed.netloc.replace('www.', '').replace('.com', '')
    application = 'financial_documents'
    print(f"    domain  = {    domain }")
    return f"raw/{application}/{domain}"

def main():
    """
    Downloads all document files from the given URL (or default GFT Publications and News page)
    and uploads them to a Google Cloud Storage bucket, using a GCS folder path built from the URL.
    """
    # Read URL from command-line arguments, or use default
    default_url = "https://www.gft.com/int/en/about-us/investor-relations/publications-and-news"
    url = sys.argv[1] if len(sys.argv) > 1 else default_url
    gcs_folder = build_gcs_folder(url)
    print(f"Using URL: {url}")
    print(f"GCS folder: {gcs_folder}")
    # Initialize the GCS client
    gcs = GCSClient()
    # Initialize the document downloader with the GCS client
    downloader = DocumentDownloader(gcs)
    # Start the process
    downloader.process_url(url, gcs_folder=gcs_folder)

if __name__ == "__main__":
    main() 