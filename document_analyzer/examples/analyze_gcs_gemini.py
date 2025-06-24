from document_analyzer.gcp.gcs_client import GCSClient
from document_analyzer.ai.llm.base import BaseLLMModel
from document_analyzer.ai.document_analyze import DocumentAnalyzerAgent

if __name__ == "__main__":
    gcs = GCSClient()
    llm = BaseLLMModel(model_name="gemini-2.0-flash-lite")
    agent = DocumentAnalyzerAgent(gcs_client=gcs, user_id="usuario1", llm=llm,llm_token_limit=2000000)

    folder = "batches/financial_documents/millerind"
    folder_out= "metadata/financial_documents/millerind/"
    # 1. Generar metadatos para todos los documentos
    agent.generate_metadata_files(folder,folder_out)
    if False:
        # 2. Ejemplo de análisis interactivo
        task = "Summarize the main financial highlights from these documents."
        relevant_files = agent.analyze(folder, task)
        if relevant_files:
            agent.run_task_on_files(relevant_files, task, folder)

    agent.save_conversation() 