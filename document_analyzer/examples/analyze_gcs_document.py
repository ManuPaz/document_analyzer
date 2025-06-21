import os
from document_analyzer.gcp.gcs_client import GCSClient
from document_analyzer.ai.document_analyzer import DocumentAnalyzer

# Set the GCS folder to analyze
GCS_FOLDER = "raw/financial_documents/gft"

def process_file(analyzer, gcs_file_path):
    """Downloads, analyzes, and uploads batches for a single file."""
    print(f"\n--- Processing: {gcs_file_path} ---")
    try:
        local_path = analyzer.download_document(gcs_file_path)
        text = analyzer.extract_text(local_path)
        batches = analyzer.batch_text(text, batch_size=1000)
        
        gcs_batches_path = analyzer.save_and_upload_batches(batches, gcs_file_path)
        print(f"Batches for {os.path.basename(local_path)} uploaded to: {gcs_batches_path}")
    except Exception as e:
        print(f"Failed to process {gcs_file_path}. Error: {e}")

if __name__ == "__main__":
    gcs = GCSClient()
    analyzer = DocumentAnalyzer(gcs)

    # List documents in the folder
    files = analyzer.list_documents(GCS_FOLDER)
    print("Files in GCS folder:")
    for idx, f in enumerate(files):
        print(f"[{idx}] {f}")
    print("[all] To process all documents")

    # Select a file or process all
    if not files:
        print("No files found in the folder.")
        exit(0)
    
    selection = input("Select a file by index or type 'all': ")

    if selection.lower() == 'all':
        for f in files:
            process_file(analyzer, f)
        print("\nAll files processed.")
    else:
        try:
            selected_idx = int(selection)
            if 0 <= selected_idx < len(files):
                selected_file = files[selected_idx]
                process_file(analyzer, selected_file)
            else:
                print("Invalid index.")
        except ValueError:
            print("Invalid input. Please enter a number or 'all'.") 