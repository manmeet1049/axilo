from pydantic import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # DynamoDB Settings
    dynamodb_table_name: str = "axilo-metadata"
    dynamodb_region: str = "us-east-1"
    dynamodb_endpoint_url: str = ""  # For local development (empty string for None)
    
    # Repository Processing
    clone_base_dir: str = "/tmp"
    metadata_base_dir: str = "/tmp/metadata"
    
    # Parser Settings
    compression_level: int = 1  # 0=full, 1=standard
    output_format: str = "md"  # 'md' or 'json'
    
    # AWS Settings
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
