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
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False  # Disable track modifications to save resources

    # App specific configuration
    REGISTRATION_TOKEN = os.getenv('REGISTRATION_TOKEN')
    API_KEY = os.getenv('API_KEY')

