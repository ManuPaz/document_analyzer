import os
from document_analyzer.gcp.gcs_client import GCSClient

class PromptStore:
    def __init__(self, gcs_client: GCSClient, bucket_folder: str = "prompts"):
        self.gcs_client = gcs_client
        self.bucket_folder = bucket_folder

    def get_prompt(self, prompt_name: str, version: int = None) -> str:
        """
        Fetches the prompt text from GCS. If version is None, fetches the latest version.
        """
        prefix = f"{self.bucket_folder}/{prompt_name}/"
        files = self.gcs_client.list_files(prefix)
        if not files:
            raise FileNotFoundError(f"No prompts found for {prompt_name}")
        # Filtrar versiones
        versions = []
        for f in files:
            base = os.path.basename(f)
            if base.startswith("v") and base.endswith(".txt"):
                try:
                    v = int(base[1:-4])
                    versions.append((v, f))
                except Exception:
                    continue
        if not versions:
            raise FileNotFoundError(f"No versioned prompts found for {prompt_name}")
        versions.sort(reverse=True)
        if version is None:
            prompt_file = versions[0][1]
        else:
            prompt_file = next((f for v, f in versions if v == version), None)
            if not prompt_file:
                raise FileNotFoundError(f"Prompt version v{version} not found for {prompt_name}")
        # Descargar el prompt
        local_path = f"temp_{prompt_name}_v{version or versions[0][0]}.txt"
        self.gcs_client.bucket.blob(prompt_file).download_to_filename(local_path)
        with open(local_path, "r", encoding="utf-8") as f:
            prompt_text = f.read()
        os.remove(local_path)
        return prompt_text

    def upload_prompt(self, prompt_name: str, version: int, prompt_text: str):
        """
        Uploads a new version of a prompt to GCS.
        """
        remote_path = f"{self.bucket_folder}/{prompt_name}/v{version}.txt"
        local_path = f"temp_{prompt_name}_v{version}.txt"
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(prompt_text)
        self.gcs_client.upload_blob(local_path, remote_path)
        os.remove(local_path)
        print(f"Prompt {prompt_name} v{version} uploaded to {remote_path}") 