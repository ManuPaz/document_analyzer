import sys 
sys.path.append("document_analyzer")
from gcp.gcs_client import GCSClient
from ai.document_analyzer import DocumentAnalyzer

# Set the GCS folder to analyze
GCS_FOLDER = "raw/documents/gft"

if __name__ == "__main__":
    gcs = GCSClient()
    analyzer = DocumentAnalyzer(gcs)

    # List documents in the folder
    files = analyzer.list_documents(GCS_FOLDER)
    print("Files in GCS folder:")
    for idx, f in enumerate(files):
        print(f"[{idx}] {f}")

    # Select a file (for demo, pick the first one)
    if not files:
        print("No files found in the folder.")
        exit(0)
    selected_idx = int(input("Select a file by index: "))
    selected_file = files[selected_idx]
    print(f"Selected: {selected_file}")

    # Download and extract text
    local_path = analyzer.download_document(selected_file)
    text = analyzer.extract_text(local_path)
    batches = analyzer.batch_text(text, batch_size=1000)

    print(f"Extracted {len(batches)} batches of text. First batch:\n")
    print(batches[0]) 