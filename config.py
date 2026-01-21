"""
ChatAI Integration Configuration

Configuration settings for the Flask application.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Configuration class for the Flask application.
    Reads settings from environment variables.
    """
    # Secret key for session management and other security purposes
    SECRET_KEY = os.getenv('SECRET_KEY', 'dwae212w12ewqdsawads&)!"&§')

    # Session management settings
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    # SQLAlchemy database configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    # if not SQLALCHEMY_DATABASE_URI:
    #     raise ValueError("No DATABASE_URL set for Flask application")

    # SAIA API Configuration
    API_KEY = os.getenv('API_KEY')
    SAIA_BASE_URL = "https://chat-ai.academiccloud.de/v1"
    
    # RAG/Arcana Configuration for enhanced accuracy
    # Primary Arcana Configuration (German)
    ARCANA_ID = os.getenv('ARCANA_ID', 'adrian.patinoojeda/docs_de')  # Replace with your Arcana ID
    ARCANA_BASE_URL = os.getenv('ARCANA_BASE_URL', "https://chat-ai.academiccloud.de/v1")
    
    # Secondary Arcana Configuration (English)
    ARCANA_2_ID = os.getenv('ARCANA_2_ID', 'adrian.patinoojeda/docs_en')  # Replace with your second Arcana ID
    ARCANA_2_BASE_URL = os.getenv('ARCANA_2_BASE_URL', "https://chat-ai.academiccloud.de/v1")
    
    # Enable RAG/Arcana for enhanced responses
    ENABLE_ARCANA = os.getenv('ENABLE_ARCANA', 'true').lower() == 'true'
    
    # Arcana configuration dictionary for easy access
    ARCANAS = {
        'primary': {
            'id': ARCANA_ID,
            'base_url': ARCANA_BASE_URL
        },
        'secondary': {
            'id': ARCANA_2_ID,
            'base_url': ARCANA_2_BASE_URL
        }
    }
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable track modifications to save resources

    # App specific configuration
    REGISTRATION_TOKEN = os.getenv('REGISTRATION_TOKEN')

