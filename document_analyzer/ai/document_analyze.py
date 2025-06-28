import os
import json
from datetime import datetime
from typing import List, Dict, Any
import numpy as np
from tqdm import tqdm
from document_analyzer.gcp.gcs_client import GCSClient
from document_analyzer.config.llm_config import get_llm_token_limit
from document_analyzer.ai.prompt_store import PromptStore
from document_analyzer.ai.utils import format_text_braces, load_file_content, extract_text_from_content

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
            Crea un documento con formato "TITULO DOCUMENTO: TEXTO DOCUMENTO" para cada documento
            y genera un solo archivo de metadata combinado, guardándolo en el folder 'mix'.
        """
        files = self.list_preprocessed_files(folder)
        files = self.select_relevant_files(files, "")
        prompt_template = self.prompt_store.get_prompt("metadata", version=5)
        if mode == "mix":
            prompt_template = self.prompt_store.get_prompt("mix", version=2)
            print(f"Generando metadata combinada (mix) para todos los documentos en {folder}...")
            
            # Crear documento con formato diferenciado por documentos
            combined_document = ""
            local_paths = []
            
            for file in files:
                local_path = self._download_file(file)
                local_paths.append(local_path)
                with open(local_path, "r", encoding="utf-8") as f:
                    batches = json.load(f)
                
                # Obtener el título del documento (nombre del archivo sin extensión)
                document_title = os.path.splitext(os.path.basename(file))[0]
                
                if type(batches)==dict:
                    document_text =   " ".join([f"key: {key} info: {value}\n" for key,value in batches.items()])
                # Concatenar todos los batches del documento
                else:
                    document_text = " ".join(batches)
                
                # Agregar al documento combinado con el formato solicitado
                combined_document +="-----DOCUMENT TITLE-----\n"
                combined_document += f"{document_title}"
                combined_document +="-----DOCUMENT TEXT-----\n"
                combined_document += f"{document_text}\n\n"
                combined_document +="-----END DOCUMENT-----\n"
            
            import re
            folder_name = re.sub(r'[\\/]', '_', folder.strip('/\\'))
            metadata_filename = f"mix.json"
          
            combined_document= format_text_braces(combined_document)
            # Procesar el documento combinado con el prompt
            metadata, _, _ = self._process_batches_to_metadata([combined_document], prompt_template, files)
            self._save_and_upload_metadata(metadata, metadata_filename,folder_out)
            
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

    def analyze_token_lengths(self, folder: str, subfolders: List[str] = None, analyze_by_subfolder: bool = False, max_files: int = 10000) -> Dict[str, Any]:
        """
        Analiza las longitudes de tokens de todos los archivos en un folder de GCS.
        
        Args:
            folder: Ruta del folder en GCS a analizar
            subfolders: Lista opcional de subfolders específicos a analizar dentro del folder
            analyze_by_subfolder: Si True, agrupa archivos por subfolder y calcula estadísticas por subfolder
            max_files: Número máximo de archivos a procesar (si hay más, se toma una muestra)
            
        Returns:
            Diccionario con estadísticas de longitudes de tokens para cada subfolder analizado
        """
        results = {}
        
        if subfolders:
            # Analizar solo los subfolders especificados
            for subfolder in subfolders:
                subfolder_path = f"{folder}/{subfolder}".replace("//", "/")
                if self._folder_exists(subfolder_path):
                    if analyze_by_subfolder:
                        results[subfolder] = self._analyze_folder_token_lengths_by_subfolder(subfolder_path, max_files)
                    else:
                        results[subfolder] = self._analyze_folder_token_lengths(subfolder_path, max_files)
                else:
                    print(f"Subfolder '{subfolder}' no encontrado en '{folder}'")
        else:
            # Analizar el folder principal
            if analyze_by_subfolder:
                results[folder] = self._analyze_folder_token_lengths_by_subfolder(folder, max_files)
            else:
                results[folder] = self._analyze_folder_token_lengths(folder, max_files)
        
        return results
    
    def _folder_exists(self, folder_path: str) -> bool:
        """Verifica si un folder existe en GCS."""
        try:
            files = self.gcs_client.list_files(folder_path)
            return len(files) > 0
        except Exception:
            return False
    
    def _analyze_folder_token_lengths(self, folder_path: str, max_files: int = 10000) -> Dict[str, float]:
        """
        Analiza las longitudes de tokens de todos los archivos en un folder específico.
        
        Args:
            folder_path: Ruta completa del folder en GCS
            max_files: Número máximo de archivos a procesar (si hay más, se toma una muestra)
            
        Returns:
            Diccionario con estadísticas de longitudes de tokens
        """
        files = self.list_preprocessed_files(folder_path)
        if not files:
            print(f"No se encontraron archivos en '{folder_path}'")
            return {}
        
        # Aplicar muestreo si hay demasiados archivos
        total_files = len(files)
        if total_files > max_files:
            print(f"⚠️  Hay {total_files:,} archivos. Tomando muestra de {max_files:,} archivos...")
            import random
            random.seed(42)  # Para reproducibilidad
            files = random.sample(files, max_files)
        
        token_lengths = []
        local_paths = []
        
        try:
            # Procesar cada archivo para obtener las longitudes de tokens
            for file in tqdm(files, desc=f"Procesando archivos en {folder_path}", unit="archivo"):
                local_path = self._download_file(file)
                local_paths.append(local_path)
                
                try:
                    # Cargar contenido del archivo usando la función unificada
                    content = load_file_content(local_path)
                    
                    # Extraer texto unificado del contenido
                    total_text = extract_text_from_content(content)
                    
                    # Calcular longitud de tokens
                    token_length = self.count_tokens(total_text)
                    token_lengths.append(token_length)
                    
                except Exception as e:
                    print(f"  ❌ Error procesando {file}: {str(e)}")
                    continue
            
            # Calcular estadísticas
            if token_lengths:
                stats = self._calculate_token_statistics(token_lengths)
                print(f"\n📊 Estadísticas para '{folder_path}':")
                print(f"  📁 Archivos analizados: {len(token_lengths):,} (de {total_files:,} total)")
                print(f"  📏 Longitud mínima: {stats['min']:,} tokens")
                print(f"  📏 Longitud máxima: {stats['max']:,} tokens")
                print(f"  📏 Longitud media: {stats['mean']:,.2f} tokens")
                print(f"  📏 Mediana: {stats['median']:,.2f} tokens")
                print(f"  📏 Desviación estándar: {stats['std']:,.2f} tokens")
                
                print(f"  📈 Deciles:")
                for decile_name, value in stats['deciles'].items():
                    print(f"     {decile_name}: {value:,.0f} tokens")
                return stats
            else:
                print(f"No se pudieron procesar archivos en '{folder_path}'")
                return {}
                
        finally:
            # Limpiar archivos temporales
            for local_path in local_paths:
                try:
                    os.remove(local_path)
                except:
                    pass
    
    def _calculate_token_statistics(self, token_lengths: List[int]) -> Dict[str, float]:
        """
        Calcula estadísticas descriptivas de una lista de longitudes de tokens.
        
        Args:
            token_lengths: Lista de longitudes de tokens
            
        Returns:
            Diccionario con estadísticas calculadas
        """
        if not token_lengths:
            return {}
        
        lengths_array = np.array(token_lengths)
        
        # Calcular deciles del 0.1 al 0.9
        deciles = {}
        for i in range(1, 10):
            percentile = i * 0.1
            deciles[f"decile_{percentile:.1f}"] = float(np.percentile(lengths_array, percentile * 100))
        
        return {
            "min": float(np.min(lengths_array)),
            "max": float(np.max(lengths_array)),
            "mean": float(np.mean(lengths_array)),
            "median": float(np.median(lengths_array)),
            "std": float(np.std(lengths_array)),
            "deciles": deciles,
            "total_files": len(token_lengths)
        }

    def _analyze_folder_token_lengths_by_subfolder(self, folder_path: str, max_files: int = 10000) -> Dict[str, Any]:
        """
        Analiza las longitudes de tokens agrupando archivos por subfolder.
        Calcula estadísticas sobre la suma de longitudes de cada subfolder.
        
        Args:
            folder_path: Ruta completa del folder en GCS
            max_files: Número máximo de archivos a procesar por subfolder
            
        Returns:
            Diccionario con estadísticas por archivo y por subfolder
        """
        files = self.list_preprocessed_files(folder_path)
        if not files:
            print(f"No se encontraron archivos en '{folder_path}'")
            return {}
        
        # Agrupar archivos por subfolder
        subfolder_files = {}
        for file in files:
            # Extraer el subfolder del path del archivo
            relative_path = file.replace(folder_path, "").strip("/")
            if "/" in relative_path:
                subfolder = relative_path.split("/")[0]
            else:
                subfolder = "root"
            
            if subfolder not in subfolder_files:
                subfolder_files[subfolder] = []
            subfolder_files[subfolder].append(file)
        
        # Aplicar muestreo sobre subfolders si hay demasiados
        total_subfolders = len(subfolder_files)
        if total_subfolders > max_files:
            print(f"⚠️  Hay {total_subfolders:,} subfolders. Tomando muestra de {max_files:,} subfolders...")
            import random
            random.seed(42)
            sampled_subfolders = random.sample(list(subfolder_files.keys()), max_files)
            subfolder_files = {k: subfolder_files[k] for k in sampled_subfolders}
        
        results = {
            "by_file": {},
            "by_subfolder": {},
            "summary": {}
        }
        
        total_processed = 0
        total_files = sum(len(files) for files in subfolder_files.values())
        subfolder_total_lengths = []  # Para calcular estadísticas sobre subfolders
        
        print(f"📁 Analizando {len(subfolder_files)} subfolders con {total_files:,} archivos total...")
        
        # Procesar cada subfolder usando la función base
        for subfolder, subfolder_file_list in subfolder_files.items():
            print(f"\n📂 Procesando subfolder: {subfolder} ({len(subfolder_file_list):,} archivos)")
            
            # Usar la función base para procesar el subfolder
            subfolder_stats = self._analyze_folder_token_lengths(f"{folder_path}/{subfolder}", max_files=len(subfolder_file_list))
            
            if subfolder_stats:
                # Calcular la suma total de tokens del subfolder
                subfolder_total_tokens = subfolder_stats['mean'] * subfolder_stats['total_files']
                subfolder_total_lengths.append(subfolder_total_tokens)
                
                # Guardar estadísticas del subfolder
                subfolder_stats["subfolder"] = subfolder
                subfolder_stats["files_processed"] = subfolder_stats['total_files']
                subfolder_stats["total_tokens"] = subfolder_total_tokens
                results["by_subfolder"][subfolder] = subfolder_stats
                
                total_processed += subfolder_stats['total_files']
                
                print(f"  ✅ {subfolder}: {subfolder_stats['total_files']:,} archivos, {subfolder_stats['mean']:,.0f} tokens promedio, {subfolder_total_tokens:,.0f} tokens total")
            else:
                print(f"  ❌ {subfolder}: No se pudieron procesar archivos")
        
        # Calcular estadísticas sobre los subfolders (suma de longitudes)
        if subfolder_total_lengths:
            subfolder_statistics = self._calculate_token_statistics(subfolder_total_lengths)
            
            results["summary"] = {
                "total_files_processed": total_processed,
                "total_files_available": total_files,
                "subfolders_analyzed": len(results["by_subfolder"]),
                "subfolder_statistics": subfolder_statistics,  # Estadísticas sobre suma de longitudes por subfolder
                "note": "Statistics calculated on total token length per subfolder (sum of all files in subfolder)"
            }
            
            print(f"\n📊 RESUMEN GENERAL (estadísticas sobre subfolders):")
            print(f"  📁 Archivos procesados: {total_processed:,} (de {total_files:,} disponibles)")
            print(f"  📂 Subfolders analizados: {len(results['by_subfolder'])}")
            print(f"  📏 Tokens total promedio por subfolder: {subfolder_statistics['mean']:,.0f}")
            print(f"  📏 Tokens total mínimo por subfolder: {subfolder_statistics['min']:,.0f}")
            print(f"  📏 Tokens total máximo por subfolder: {subfolder_statistics['max']:,.0f}")
        
        return results