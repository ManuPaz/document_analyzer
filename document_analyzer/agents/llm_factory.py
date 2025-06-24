from langchain.llms import OpenAI
# Puedes importar otros LLMs de LangChain aquí, por ejemplo:
# from langchain_google_genai import ChatGoogleGenerativeAI

class LLMFactory:
    """
    Factory for creating LLM instances for LangChain, supporting multiple providers.
    """
    @staticmethod
    def create(llm_type: str = "openai", **kwargs):
        """
        Create and return an LLM instance based on the llm_type.
        Args:
            llm_type (str): The type of LLM to use (e.g., 'openai', 'gemini').
            kwargs: Additional parameters for the LLM constructor.
        Returns:
            An instance of a LangChain LLM.
        """
        if llm_type == "openai":
            return OpenAI(**kwargs)
        # elif llm_type == "gemini":
        #     return ChatGoogleGenerativeAI(**kwargs)
        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}") 