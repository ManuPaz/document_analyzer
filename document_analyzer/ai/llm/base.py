import os
from typing import Optional, Dict, Any, List
import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from dotenv import load_dotenv

class BaseLLMModel:
    def __init__(self, model_name: str = "gemini-2.0-flash-lite"):
        load_dotenv()
        
        # Configure Google API
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.llm = GoogleGenerativeAI(model=model_name, temperature=0.7)
        
    def create_chain(self, prompt_template: str, output_key: str = "result") -> LLMChain:
        """Create a LangChain chain with the given prompt template"""
        prompt = PromptTemplate(
            input_variables=["input"],
            template=prompt_template
        )
        return LLMChain(
            llm=self.llm,
            prompt=prompt,
            output_key=output_key,
            verbose=True
        )
    
    def generate_text(self, prompt: str) -> str:
        """Generate text using the model directly"""
        chain = self.create_chain(prompt)
        response = chain.run(input=prompt)
        return response
    
    def batch_generate(self, prompts: List[str]) -> List[str]:
        """Generate text for multiple prompts"""
        return [self.generate_text(prompt) for prompt in prompts]
    
    def set_temperature(self, temperature: float) -> None:
        """Set the temperature for text generation"""
        if not 0 <= temperature <= 1:
            raise ValueError("Temperature must be between 0 and 1")
        self.llm.temperature = temperature 

    def __getattr__(self, name):
        """
        Delegate attribute access to the underlying LLM instance.
        This allows calling any method of self.llm directly from BaseLLMModel.
        """
        return getattr(self.llm, name) 