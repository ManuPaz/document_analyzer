from document_analyzer.gcp.gcs_client import GCSClient
from document_analyzer.ai.prompt_store import PromptStore

if __name__ == "__main__":
    gcs = GCSClient()
    store = PromptStore(gcs)

    # Leer el prompt desde el archivo
    with open("financial_analysis_prompt.txt", "r", encoding="utf-8") as f:
        prompt_text = f.read()

    # Subir el prompt como "mix" versión 2
    store.upload_prompt("mix", 2, prompt_text)
    print("Financial analysis prompt uploaded successfully as 'mix' version 2.") 