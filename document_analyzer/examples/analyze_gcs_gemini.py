import argparse
from document_analyzer.gcp.gcs_client import GCSClient
from document_analyzer.ai.llm.base import BaseLLMModel
from document_analyzer.ai.document_analyze import DocumentAnalyzerAgent

if __name__ == "__main__":
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Analizar documentos desde GCS usando Gemini')
    parser.add_argument('--topic', type=str, default='investors.unidata.it', 
                       help='Tópico de los documentos a analizar (default: gft)')
    parser.add_argument('--mode', type=str, default='mix', 
                       help='Analisis mode: metadata or mix')
    parser.add_argument('--folder_in', type=str, default='metadata', 
                       help='Folder in')
    parser.add_argument('--folder_out', type=str, default='mix', 
                       help='Folder out')
    parser.add_argument('--bucket', type=str, default=None,
                       help='Nombre del bucket de GCS a usar (si no se especifica, usa el bucket por defecto)')
    args = parser.parse_args()
    
    gcs = GCSClient(bucket_name=args.bucket)
    llm = BaseLLMModel(model_name="gemini-2.0-flash-lite")
    agent = DocumentAnalyzerAgent(gcs_client=gcs, user_id="usuario1", llm=llm,llm_token_limit=2000000)
    topic = args.topic
    mode = args.mode 
    folder_in = args.folder_in
    folder_out = args.folder_out
    print(f"🔧 Usando bucket: {gcs.get_bucket_name()}")
    print(f"Args: mode = {mode}, topic = {topic}, folder in {folder_in}, folder out {folder_out}")
    folder = f"{folder_in}/financial_documents/{topic}"
    folder_out= f"{folder_out}/financial_documents/{topic}"
    # 1. Generar metadatos para todos los documentos
    agent.generate_metadata_files(folder,folder_out,mode=mode)
    if False:
        # 2. Ejemplo de análisis interactivo
        task = "Summarize the main financial highlights from these documents."
        relevant_files = agent.analyze(folder, task)
        if relevant_files:
            agent.run_task_on_files(relevant_files, task, folder)

    agent.save_conversation() 