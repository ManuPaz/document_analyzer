import sys
import argparse
from urllib.parse import urlparse
from document_analyzer.gcp.gcs_client import GCSClient
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
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Descargar publicaciones desde una URL')
    parser.add_argument('--url', type=str, default="https://investors.unidata.it/investors/presentations/?lang=en",
                       help='URL de la página a procesar (default: https://investors.unidata.it/investors/presentations/?lang=en)')
    parser.add_argument('--bucket', type=str, default=None,
                       help='Nombre del bucket de GCS a usar (si no se especifica, usa el bucket por defecto)')
    args = parser.parse_args()
    
    url = args.url
    gcs_folder = build_gcs_folder(url)
    print(f"🔧 Usando bucket: {GCSClient(bucket_name=args.bucket).get_bucket_name()}")
    print(f"🌐 Usando URL: {url}")
    print(f"📁 GCS folder: {gcs_folder}")
    
    # Initialize the GCS client
    gcs = GCSClient(bucket_name=args.bucket)
    # Initialize the document downloader with the GCS client
    downloader = DocumentDownloader(gcs)
    # Start the process
    downloader.process_url(url, gcs_folder=gcs_folder)

if __name__ == "__main__":
    main() 