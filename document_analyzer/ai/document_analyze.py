import os
import json
from datetime import datetime
from typing import List, Dict, Any
from document_analyzer.gcp.gcs_client import GCSClient
from document_analyzer.agents.llm_factory import LLMFactory
from document_analyzer.config.llm_config import get_llm_token_limit
from document_analyzer.ai.prompt_store import PromptStore


class DocumentAnalyzerAgent:
    """
    LLM-powered agent for interactive document analysis and conversation history management.
    """

    def __init__(
        self, gcs_client: GCSClient, user_id: str, llm=None, llm_token_limit: int = None
    ):
        self.gcs_client = gcs_client
        self.user_id = user_id
        self.llm = llm  # Puede ser BaseLLMModel, OpenAI, etc.
        self.conversation: List[Dict[str, Any]] = []
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Detectar modelo y asignar límite de tokens
        if llm_token_limit is not None:
            self.llm_token_limit = llm_token_limit
        elif hasattr(llm, "model_name"):
            self.llm_token_limit = get_llm_token_limit(
                getattr(llm, "model_name", "gemini-2.0-flash-lite")
            )
        else:
            self.llm_token_limit = 1000000
        self.prompt_store = PromptStore(self.gcs_client)

    def list_preprocessed_files(self, folder: str) -> List[str]:
        """List all preprocessed batch files in the folder."""
        return self.gcs_client.list_files(folder)

    def select_relevant_files(self, files: List[str], task: str) -> List[str]:
        """
        Use the LLM to select relevant files for the given task.
        Returns a list of file paths or an empty list if none are relevant.
        """
        # Aquí puedes usar embeddings, un prompt, o un agente LangChain para filtrar
        # Por simplicidad, aquí solo devuelve todos los archivos
        return files

    def analyze(self, folder: str, task: str) -> List[str]:
        """
        Main entrypoint: selects relevant files and performs the analysis task.
        Returns the list of relevant files or a message if none are found.
        """
        files = self.list_preprocessed_files(folder)
        relevant_files = self.select_relevant_files(files, task)
        if not relevant_files:
            print("No relevant documents found for your task.")
            self._log_interaction(task, "No relevant documents found.", [])
            return []
        print(f"Relevant files: {relevant_files}")
        self._log_interaction(task, f"Relevant files: {relevant_files}", relevant_files)
        return relevant_files

    def run_task_on_files(self, files: List[str], task: str, folder: str):
        """
        Runs the LLM on the selected files for the given task.
        """
        for file in files:
            # Descarga el batch y pásalo al LLM
            local_path = self._download_file(file)
            with open(local_path, "r", encoding="utf-8") as f:
                batches = json.load(f)
            # Aquí puedes iterar por los batches y hacer preguntas/resúmenes, etc.
            # Ejemplo simple: concatenar y preguntar al LLM
            text = " ".join(batches)
            prompt = f"{task}\n\n{text[:3000]}"
            if hasattr(self.llm, "generate_text"):
                response = self.llm.generate_text(prompt)
            else:
                response = self.llm(prompt)
            print(f"Response for {file}:\n{response}\n")
            self._log_interaction(task, response, [file])
            os.remove(local_path)

    def _download_file(self, gcs_path: str) -> str:
        """Download a file from GCS to a temp local path."""
        local_path = f"temp_{os.path.basename(gcs_path)}"
        self.gcs_client.bucket.blob(gcs_path).download_to_filename(local_path)
        return local_path

    def _log_interaction(
        self,
        question: str,
        answer: str,
        files: List[str],
        input_tokens: int = None,
        output_tokens: int = None,
    ):
        """Log the interaction in the conversation history."""
        self.conversation.append(
            {
                "timestamp": datetime.now().isoformat(),
                "question": question,
                "answer": answer,
                "files": files,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            }
        )

    def save_conversation(self):
        """Save the conversation history to GCS under conversations/{user_id}/."""
        folder = f"conversations/{self.user_id}/"
        filename = f"{self.session_id}.json"
        local_path = filename
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(self.conversation, f, ensure_ascii=False, indent=2)
        self.gcs_client.upload_blob(local_path, os.path.join(folder, filename))
        os.remove(local_path)
        print(f"Conversation saved to {folder}{filename}")

    def count_tokens(self, text: str) -> int:
        """
        Counts tokens using the LLM's tokenizer if available, else falls back to length//4.
        """
        if hasattr(self.llm, "get_num_tokens"):
            return self.llm.get_num_tokens(text)
        return max(1, len(text) // 4)

    def _process_batches_to_metadata(self, batches, prompt_template, files_ref):
        """
        Procesa una lista de batches (texto), genera la metadata usando el LLM y devuelve el dict de metadata y los totales de tokens.
        files_ref: lista de archivos referenciados (para logging)
        """
        # Juntar batches sin superar el límite de tokens
        joined_batches = []
        current = ""
        for batch in batches:
            if len(current) + len(batch) <= self.llm_token_limit:
                current += " " + batch
            else:
                joined_batches.append(current.strip())
                current = batch
        if current:
            joined_batches.append(current.strip())
        total_input_tokens = 0
        total_output_tokens = 0
        if len(joined_batches) == 1:
            text = joined_batches[0]
            prompt = (
                prompt_template + "\n\nDocument:\n" + text[: self.llm_token_limit]
            )
            input_tokens = self.count_tokens(prompt)
            if hasattr(self.llm, "generate_text"):
                response = self.llm.generate_text(prompt)
            else:
                response = self.llm(prompt)
            output_tokens = self.count_tokens(response)
            total_input_tokens += input_tokens
            total_output_tokens += output_tokens
            # Try to parse the response as JSON
            try:
                metadata = json.loads(response)
            except Exception:
                import re
                match = re.search(r"\{.*\}", response, re.DOTALL)
                if match:
                    try:
                        metadata = json.loads(match.group(0))
                    except Exception:
                        print(f"Could not parse metadata. LLM response:\n{response}")
                        metadata = {}
                else:
                    print(f"Could not parse metadata. LLM response:\n{response}")
                    metadata = {}
            self._log_interaction(
                prompt, response, files_ref, input_tokens, output_tokens
            )
        else:
            batch_prompts = []
            batch_responses = []
            batch_input_tokens = []
            batch_output_tokens = []
            for i, batch in enumerate(joined_batches):
                prompt = (
                    prompt_template.replace("following document", f"following text, which is the batch {i} of a document")
                    + "\n\nText:\n"
                    + batch[: self.llm_token_limit]
                )
                input_tokens = self.count_tokens(prompt)
                if hasattr(self.llm, "generate_text"):
                    response = self.llm.generate_text(prompt)
                else:
                    response = self.llm(prompt)
                output_tokens = self.count_tokens(response)
                total_input_tokens += input_tokens
                total_output_tokens += output_tokens
                batch_prompts.append(prompt)
                batch_responses.append(response)
                batch_input_tokens.append(input_tokens)
                batch_output_tokens.append(output_tokens)
            batch_jsons = []
            for resp in batch_responses:
                try:
                    batch_jsons.append(json.loads(resp))
                except Exception:
                    import re
                    match = re.search(r"\{.*\}", resp, re.DOTALL)
                    if match:
                        batch_jsons.append(json.loads(match.group(0)))
                    else:
                        print(f"Could not parse batch response: {resp}")
                        batch_jsons.append({})
            if not batch_jsons:
                print(f"No valid batch responses.")
                return {"total_input_tokens": total_input_tokens, "total_output_tokens": total_output_tokens}, total_input_tokens, total_output_tokens
            keys = list(batch_jsons[0].keys())
            metadata = {}
            for key in keys:
                values = [bj.get(key, "") for bj in batch_jsons]
                reduce_prompt = f"""You are combining the results of a document analysis. The key to combine is '{key}'. Here are the values for this key from different batches: {values}\nGenerate the final value for '{key}'.Return only a valid JSON object with only one field: the key. And the value must be in the same format as in the inputs: ie, if the inputs are lists, list, if the inputs are strings, string ..."""
                print(reduce_prompt)
                reduce_input_tokens = self.count_tokens(reduce_prompt)
                if hasattr(self.llm, "generate_text"):
                    response = self.llm.generate_text(reduce_prompt)
                else:
                    response = self.llm(reduce_prompt)
                reduce_output_tokens = self.count_tokens(response)
                total_input_tokens += reduce_input_tokens
                total_output_tokens += reduce_output_tokens
                try:
                    metadata[key] = json.loads(response)[key]
                except Exception:
                    import re
                    match = re.search(r"\{.*\}", response, re.DOTALL)
                    if match:
                        try:
                            metadata[key] = json.loads(match.group(0))[key]
                        except Exception:
                            print(f"Could not parse batch response: {response}")
                            metadata[key] = {}
                    else:
                        print(f"Could not parse batch response: {response}")
                        metadata[key] = {}
                self._log_interaction(
                    reduce_prompt,
                    response,
                    files_ref,
                    reduce_input_tokens,
                    reduce_output_tokens,
                )
        metadata["total_input_tokens"] = total_input_tokens
        metadata["total_output_tokens"] = total_output_tokens
        return metadata, total_input_tokens, total_output_tokens

    def _save_and_upload_metadata(self, metadata, local_filename, gcs_folder):
        """Guarda el archivo local y lo sube a GCS en el folder indicado."""
        with open(local_filename, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        gcs_metadata_path = os.path.join(gcs_folder, local_filename).replace("\\", "/")
        self.gcs_client.upload_blob(local_filename, gcs_metadata_path)
        print(f"Metadata uploaded to {gcs_metadata_path}")
        os.remove(local_filename)

    def generate_metadata_files(self, folder: str, folder_out: str, mode: str = "metadata"):
        """
        Si mode == 'metadata':
            Para cada documento en el folder, lee todos sus batches y genera un archivo de metadata individual.
        Si mode == 'mix':
            Junta todos los batches de todos los documentos y genera un solo archivo de metadata, guardándolo en el folder 'mix'.
        """
        files = self.list_preprocessed_files(folder)
        files = self.select_relevant_files(files, "")
        prompt_template = self.prompt_store.get_prompt("metadata", version=5)
        if mode == "mix":
            print(f"Generando metadata combinada (mix) para todos los documentos en {folder}...")
            all_batches = []
            local_paths = []
            for file in files:
                local_path = self._download_file(file)
                local_paths.append(local_path)
                with open(local_path, "r", encoding="utf-8") as f:
                    batches = json.load(f)
                    all_batches.extend(batches)
            import re
            folder_name = re.sub(r'[\\/]', '_', folder.strip('/\\'))
            metadata_filename = f"{folder_name}_mix.json"
            metadata, _, _ = self._process_batches_to_metadata(all_batches, prompt_template, files)
            self._save_and_upload_metadata(metadata, metadata_filename, "mix")
            for lp in local_paths:
                os.remove(lp)
            return
        # --- Modo normal (uno por documento) ---
        for file in files:
            print(f"Generating metadata for {file}...")
            local_path = self._download_file(file)
            with open(local_path, "r", encoding="utf-8") as f:
                batches = json.load(f)
            base = os.path.splitext(os.path.basename(file))[0]
            metadata_filename = f"{base}_metadata.json"
            metadata, _, _ = self._process_batches_to_metadata(batches, prompt_template, [file])
            self._save_and_upload_metadata(metadata, metadata_filename, folder_out)
            os.remove(local_path)