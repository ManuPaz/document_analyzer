from document_analyzer.gcp.gcs_client import GCSClient
from document_analyzer.ai.prompt_store import PromptStore

if __name__ == "__main__":
    gcs = GCSClient()
    store = PromptStore(gcs)

    prompt_name = input("Prompt name (e.g. metadata): ")
    version = int(input("Prompt version (e.g. 1): "))
    print("Paste your prompt below. End with a line containing only 'END':")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    prompt_text = "\n".join(lines)

    store.upload_prompt(prompt_name, version, prompt_text)
    print(f"Prompt '{prompt_name}' version {version} uploaded successfully.") 