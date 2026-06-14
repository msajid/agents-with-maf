import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(override=False) 

class LLMProviderConfig(BaseSettings):
    foundry_project_endpoint: str =  os.environ.get("FOUNDRY_PROJECT_ENDPOINT")   
    foundry_model: str = os.environ.get("FOUNDRY_MODEL", "gpt-5.1")
    default_temperature: Optional[float] = 0.0
    default_max_tokens: Optional[int] = 2048
    application_insights_connection_string: str = os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING")  
    