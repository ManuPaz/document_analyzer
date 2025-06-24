LLM_TOKEN_LIMITS = {
    "gemini-2.0-flash-lite": 1000000,
    # Puedes añadir más modelos aquí
    # "openai-gpt-3.5": 4096,
    # "openai-gpt-4": 8192,
}

def get_llm_token_limit(model_name: str) -> int:
    """
    Returns the token limit for the given LLM model name.
    """
    return LLM_TOKEN_LIMITS.get(model_name, 1000000)  # Valor por defecto: 1,000,000 