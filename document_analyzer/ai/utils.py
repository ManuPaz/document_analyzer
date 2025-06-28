import json
import csv
import pandas as pd
from typing import Union, List, Dict, Any

def format_text_braces(text: str) -> str:
    """
    Reemplaza todas las llaves '{' por '{{' y '}' por '}}' en el texto dado.
    Útil para evitar conflictos con formatos de string.
    """
    return text.replace("{", "{{").replace("}", "}}")

def load_file_content(file_path: str) -> Union[List[str], Dict[str, Any], str]:
    """
    Carga el contenido de un archivo independientemente de su formato.
    Soporta JSON, TXT, CSV y otros formatos de texto.
    
    Args:
        file_path: Ruta del archivo a cargar
        
    Returns:
        Contenido del archivo en formato unificado:
        - Lista de strings para archivos con múltiples líneas/batches
        - Diccionario para archivos JSON con estructura
        - String para archivos de texto simple
        
    Raises:
        Exception: Si no se puede cargar el archivo
    """
    file_extension = file_path.lower().split('.')[-1]
    
    try:
        if file_extension == 'json':
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        elif file_extension == 'csv':
            # Intentar cargar como CSV y convertir a texto
            try:
                df = pd.read_csv(file_path)
                # Convertir DataFrame a texto
                return df.to_string(index=False)
            except Exception:
                # Si falla pandas, intentar con csv estándar
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    lines = []
                    for row in reader:
                        lines.append(' '.join(row))
                    return '\n'.join(lines)
        
        elif file_extension in ['txt', 'text', 'md', 'markdown']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        else:
            # Para otros formatos, intentar leer como texto
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                # Si falla UTF-8, intentar con otras codificaciones
                for encoding in ['latin-1', 'cp1252', 'iso-8859-1']:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            return f.read()
                    except UnicodeDecodeError:
                        continue
                raise Exception(f"No se pudo decodificar el archivo {file_path} con ninguna codificación conocida")
    
    except Exception as e:
        raise Exception(f"Error al cargar el archivo {file_path}: {str(e)}")

def extract_text_from_content(content: Union[List[str], Dict[str, Any], str]) -> str:
    """
    Extrae texto unificado de diferentes tipos de contenido.
    
    Args:
        content: Contenido del archivo (lista, diccionario, string)
        
    Returns:
        String con todo el texto extraído
    """
    if isinstance(content, list):
        # Si es una lista de batches o líneas
        return " ".join(str(item) for item in content)
    
    elif isinstance(content, dict):
        # Si es un diccionario, convertir a texto
        text_parts = []
        for key, value in content.items():
            if isinstance(value, (list, dict)):
                text_parts.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
            else:
                text_parts.append(f"{key}: {value}")
        return " ".join(text_parts)
    
    elif isinstance(content, str):
        # Si ya es un string
        return content
    
    else:
        # Para otros tipos, convertir a string
        return str(content) 