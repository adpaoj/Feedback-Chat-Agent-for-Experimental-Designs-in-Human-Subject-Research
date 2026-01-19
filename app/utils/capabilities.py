import os
import requests
import json
import logging
from flask import current_app

logger = logging.getLogger(__name__)

def check_model_capabilities():
    """
    Check and print capabilities of available models from the API.
    """
    api_key = os.getenv('API_KEY')
    base_url = os.getenv('SAIA_BASE_URL', "https://chat-ai.academiccloud.de/v1")
    url = f"{base_url}/models"

    logger.info(f"Fetching from {url}")

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, dict) and 'data' in data:
            models = data['data']
            if models:
                logger.info("First model structure:")
                logger.info(json.dumps(models[0], indent=2))
                
                # Check for specific capabilities in all models
                logger.info("\nChecking capabilities...")
                for model in models:
                    inputs = model.get('input', [])
                    if 'image' in inputs:
                        logger.info(f"Vision model found: {model['id']} - Input: {inputs}")
                    
                    # Also check for 'vision' or 'vl' in ID just in case
                    if 'vision' in model.get('id', '').lower() or 'vl' in model.get('id', '').lower():
                         logger.info(f"Potential vision model by ID: {model['id']} - Input: {inputs}")
            else:
                logger.warning("No models found in data")
        else:
            logger.error("Unexpected response format")
            logger.error(data)

    except Exception as e:
        logger.error(f"Error checking capabilities: {e}")
