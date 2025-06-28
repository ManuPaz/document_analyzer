import argparse
from document_analyzer.gcp.gcs_client import GCSClient
from document_analyzer.ai.llm.base import BaseLLMModel
from document_analyzer.ai.document_analyze import DocumentAnalyzerAgent

if __name__ == "__main__":
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Analizar longitudes de tokens de documentos en GCS')
    parser.add_argument('--folder', type=str, required=True,
                       help='Folder de GCS a analizar (ej: metadata/financial_documents/investors.unidata.it)')
    parser.add_argument('--subfolders', type=str, nargs='*', default=None,
                       help='Lista opcional de subfolders específicos a analizar')
    parser.add_argument('--bucket', type=str, default=None,
                       help='Nombre del bucket de GCS a usar (si no se especifica, usa el bucket por defecto)')
    parser.add_argument('--analyze_by_subfolder', action='store_true',
                       help='Analizar archivos agrupados por subfolder (proporciona estadísticas por archivo y por subfolder)')
    parser.add_argument('--max_files', type=int, default=100,
                       help='Número máximo de archivos a procesar por subfolder (default: 10000)')
    parser.add_argument('--save_results', action='store_true',
                       help='Guardar los resultados en un archivo JSON')
    args = parser.parse_args()
    
    # Inicializar cliente GCS y agente
    gcs = GCSClient(bucket_name=args.bucket)
    llm = BaseLLMModel(model_name="gemini-2.0-flash-lite")
    agent = DocumentAnalyzerAgent(gcs_client=gcs, user_id="usuario1", llm=llm, llm_token_limit=2000000)
    
    print(f"🔧 Usando bucket: {gcs.get_bucket_name()}")
    print(f"📁 Analizando folder: {args.folder}")
    if args.subfolders:
        print(f"📂 Subfolders específicos: {args.subfolders}")
    else:
        print("📂 Analizando todo el folder")
    
    if args.analyze_by_subfolder:
        print(f"📊 Modo: Análisis por subfolder (máx {args.max_files:,} archivos por subfolder)")
    else:
        print(f"📊 Modo: Análisis general (máx {args.max_files:,} archivos total)")
    
    # Ejecutar análisis de longitudes de tokens
    results = agent.analyze_token_lengths(
        args.folder, 
        args.subfolders, 
        analyze_by_subfolder=args.analyze_by_subfolder,
        max_files=args.max_files
    )
    
    # Mostrar resultados
    print("\n" + "="*60)
    print("RESULTADOS DEL ANÁLISIS DE LONGITUDES DE TOKENS")
    print("="*60)
    
    if args.analyze_by_subfolder:
        # Mostrar resultados del análisis por subfolder
        for folder_name, folder_results in results.items():
            if isinstance(folder_results, dict) and "summary" in folder_results:
                print(f"\n📁 {folder_name}:")
                
                # Mostrar resumen general
                summary = folder_results["summary"]
                print(f"   📊 Archivos procesados: {summary['total_files_processed']:,} (de {summary['total_files_available']:,} disponibles)")
                print(f"   📂 Subfolders analizados: {summary['subfolders_analyzed']}")
                
                # Mostrar estadísticas por subfolder
                print(f"   📈 Estadísticas por subfolder:")
                for subfolder, stats in folder_results["by_subfolder"].items():
                    print(f"      📂 {subfolder}: {stats['files_processed']:,} archivos, {stats['mean']:,.0f} tokens promedio, {stats['total_tokens']:,.0f} tokens total")
                
                # Mostrar estadísticas generales sobre subfolders
                subfolder_stats = summary["subfolder_statistics"]
                print(f"   📏 Estadísticas sobre subfolders (suma de tokens por subfolder):")
                print(f"      Mínimo total por subfolder: {subfolder_stats['min']:,.0f} tokens")
                print(f"      Máximo total por subfolder: {subfolder_stats['max']:,.0f} tokens")
                print(f"      Media total por subfolder: {subfolder_stats['mean']:,.2f} tokens")
                print(f"      Mediana total por subfolder: {subfolder_stats['median']:,.2f} tokens")
            else:
                print(f"\n❌ {folder_name}: No se pudieron procesar los archivos")
    else:
        # Mostrar resultados del análisis general
        for folder_name, stats in results.items():
            if stats:  # Solo mostrar si hay estadísticas
                print(f"\n📁 {folder_name}:")
                print(f"   📊 Archivos analizados: {stats['total_files']:,}")
                print(f"   📏 Longitud mínima: {stats['min']:,} tokens")
                print(f"   📏 Longitud máxima: {stats['max']:,} tokens")
                print(f"   📏 Longitud media: {stats['mean']:,.2f} tokens")
                print(f"   📏 Mediana: {stats['median']:,.2f} tokens")
                print(f"   📏 Desviación estándar: {stats['std']:,.2f} tokens")
                
                print(f"   📈 Deciles:")
                for decile_name, value in stats['deciles'].items():
                    print(f"      {decile_name}: {value:,.0f} tokens")
            else:
                print(f"\n❌ {folder_name}: No se encontraron archivos o no se pudieron procesar")
    
    # Guardar resultados si se solicita
    if args.save_results:
        import json
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_suffix = "_by_subfolder" if args.analyze_by_subfolder else "_general"
        filename = f"token_lengths_analysis{mode_suffix}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Resultados guardados en: {filename}")
    
    # Guardar conversación del agente
    agent.save_conversation()
    
    print("\n✅ Análisis completado!") 