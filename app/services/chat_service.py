"""
Chat Service Module
Handles AI model interactions, message preparation, and API communication
"""

import requests
import json
import logging
import os
from flask import current_app
from openai import OpenAI
from openai import APIError, APIConnectionError, RateLimitError, APITimeoutError


logger = logging.getLogger(__name__)


class ModelAPIError(Exception):
    """Custom exception for model API errors"""
    pass


class ChatService:
    """Service for handling chat-related operations with AI models"""
    
    # Token limits for context window management (approximate)
    DEFAULT_TOKEN_LIMIT = 4096
    MODEL_TOKEN_LIMITS = {
        'gpt-4': 8192,
        'gpt-4-32k': 32768,
        'gpt-3.5-turbo': 4096,
        'gpt-3.5-turbo-16k': 16384,
        'meta-llama-3.1-8b-instruct': 8192,
        'meta-llama-3.1-70b-instruct': 8192,
    }
    
    @staticmethod
    def get_openai_client():
        """
        Create and return an OpenAI client instance
        
        Returns:
            OpenAI: Configured OpenAI client
            
        Raises:
            ModelAPIError: If API configuration is invalid
        """
        try:
            api_key = current_app.config.get('API_KEY')
            if not api_key:
                raise ModelAPIError("API key not configured")
                
            api_base = current_app.config.get('SAIA_BASE_URL', "https://chat-ai.academiccloud.de/v1")
            
            return OpenAI(
                api_key=api_key,
                base_url=api_base,
                timeout=600
            )
        except Exception as e:
            logger.error(f"Failed to create OpenAI client: {e}")
            raise ModelAPIError(f"Failed to initialize API client: {str(e)}")

    @staticmethod
    def get_models():
        """
        Fetch available models from the API or fallback to local file
        
        Returns:
            list: List of available models with their properties
            
        Raises:
            ModelAPIError: If model fetching fails completely
        """
        models_list = []
        
        # Try fetching from API first
        try:
            api_key = current_app.config.get('API_KEY')
            if api_key:
                base_url = current_app.config.get('SAIA_BASE_URL', "https://chat-ai.academiccloud.de/v1")
                url = f"{base_url}/models"
                
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json"
                }
                
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models_list = data.get('data', [])
                    logger.info(f"Fetched {len(models_list)} models from API")
                else:
                    logger.warning(f"API returned status {response.status_code} when fetching models")
        except Exception as e:
            logger.warning(f"Failed to fetch models from API: {e}")

        # Fallback to local file if API failed or returned no models
        if not models_list:
            try:
                models_file = os.path.join(current_app.root_path, 'static', 'assets', 'models.json')
                if os.path.exists(models_file):
                    with open(models_file, 'r') as f:
                        local_models = json.load(f)
                        # Adapt local models to API format
                        for model in local_models:
                            models_list.append({
                                'id': model.get('name'),
                                'name': model.get('display_name', model.get('name')),
                                'input': ['text', 'image'] if model.get('image_capable') else ['text'],
                                'context_length': ChatService.DEFAULT_TOKEN_LIMIT
                            })
                    logger.info(f"Loaded {len(models_list)} models from local file")
            except Exception as e:
                logger.error(f"Failed to load local models: {e}")

        if not models_list:
            raise ModelAPIError("No models available (API failed and local file not found)")
            
        formatted_models = []
        for model in models_list:
            # Ensure input is a list
            input_types = model.get('input')
            if input_types is None:
                input_types = ['text']
            elif not isinstance(input_types, list):
                input_types = [str(input_types)]
            
            formatted_models.append({
                "id": model['id'],
                "name": model.get('name', model['id']),
                "input": input_types,
                "context_length": model.get('context_length', ChatService.DEFAULT_TOKEN_LIMIT)
            })
        
        return formatted_models

    @staticmethod
    def estimate_tokens(text):
        """
        Rough estimation of token count
        Uses approximation: 1 token ≈ 4 characters for English text
        
        Args:
            text (str): Text to estimate tokens for
            
        Returns:
            int: Estimated token count
        """
        if not text:
            return 0
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4

    @staticmethod
    def get_model_token_limit(model_name):
        """
        Get the token limit for a specific model
        
        Args:
            model_name (str): Name of the model
            
        Returns:
            int: Token limit for the model
        """
        return ChatService.MODEL_TOKEN_LIMITS.get(
            model_name, 
            ChatService.DEFAULT_TOKEN_LIMIT
        )

    @staticmethod
    def prepare_messages(history_messages, current_message=None, base64_image=None, 
                        system_prompt=None, model_name=None, max_tokens=1500):
        """
        Prepare messages for the API with context window management
        
        Implements a sliding window approach to stay within token limits:
        - Always includes system prompt if provided
        - Keeps most recent messages that fit within context window
        - Reserves space for the response (max_tokens)
        
        Args:
            history_messages: List of Message objects from database
            current_message (str, optional): Current user message
            base64_image (str, optional): Base64 encoded image
            system_prompt (str, optional): System instructions
            model_name (str, optional): Model name for token limit lookup
            max_tokens (int): Maximum tokens for response
            
        Returns:
            list: Formatted messages for API
        """
        messages = []
        
        # Get model's token limit
        model_limit = ChatService.get_model_token_limit(model_name)
        
        # Reserve tokens for response
        available_tokens = model_limit - max_tokens
        
        # Add system prompt if provided
        system_tokens = 0
        if system_prompt:
            system_tokens = ChatService.estimate_tokens(system_prompt)
            available_tokens -= system_tokens
            messages.append({"role": "system", "content": system_prompt})
        
        # Estimate tokens for current message (if it's an image message)
        current_message_tokens = 0
        if base64_image:
            # Images take up significant tokens (estimate ~1000 tokens for an image)
            current_message_tokens = 1000
            if current_message:
                current_message_tokens += ChatService.estimate_tokens(current_message)
            available_tokens -= current_message_tokens
        
        # Build message history with sliding window
        # Start from most recent and work backwards
        history_tokens = 0
        messages_to_include = []
        
        for msg in reversed(history_messages):
            msg_tokens = ChatService.estimate_tokens(msg.content)
            
            if history_tokens + msg_tokens <= available_tokens:
                messages_to_include.insert(0, {
                    'role': msg.role, 
                    'content': msg.content
                })
                history_tokens += msg_tokens
            else:
                # We've hit the token limit, stop adding older messages
                logger.info(f"Context window limit reached. Included {len(messages_to_include)} messages.")
                break
        
        # Add the history messages
        messages.extend(messages_to_include)
        
        # Add current message with image if present
        if base64_image:
            if messages and messages[-1]['role'] == 'user':
                # The last message in history is the current user message
                # Replace it with multimodal version
                last_msg = messages.pop()
                image_payload = [
                    {"type": "text", "text": last_msg['content']},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
                ]
                messages.append({"role": "user", "content": image_payload})
        
        logger.info(f"Prepared {len(messages)} messages. Estimated tokens: system={system_tokens}, "
                   f"history={history_tokens}, current={current_message_tokens}, "
                   f"total={system_tokens + history_tokens + current_message_tokens}/{model_limit}")
        
        return messages

    @staticmethod
    def stream_chat_completion(client, messages, model, temperature=0.5, max_tokens=1500, **kwargs):
        """
        Stream chat completion from the API with error handling
        
        Args:
            client: OpenAI client instance
            messages: Formatted messages list
            model (str): Model name
            temperature (float): Sampling temperature
            max_tokens (int): Maximum tokens for response
            **kwargs: Additional parameters for the API
            
        Yields:
            str: Content chunks from the API
            
        Raises:
            ModelAPIError: If API call fails
        """
        try:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream": True,
            }
            
            # Add any additional parameters
            payload.update(kwargs)
            
            response = client.chat.completions.create(**payload)
            
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    content = getattr(delta, 'content', '')
                    if content:
                        yield content
                        
        except APITimeoutError as e:
            logger.error(f"API timeout: {e}")
            raise ModelAPIError("Request timeout: The model is taking too long to respond")
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            raise ModelAPIError("Rate limit exceeded: Please try again in a moment")
        except APIConnectionError as e:
            logger.error(f"API connection error: {e}")
            raise ModelAPIError("Connection error: Cannot reach the API server")
        except APIError as e:
            logger.error(f"API error: {e}")
            raise ModelAPIError(f"API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during streaming: {e}")
            raise ModelAPIError(f"Unexpected error: {str(e)}")

    @staticmethod
    def validate_file(file_data):
        """
        Validate uploaded file
        
        Args:
            file_data (dict): File information including 'name', 'type', 'content', 'size'
            
        Returns:
            bool: True if valid
            
        Raises:
            ValueError: If file is invalid
        """
        MAX_TEXT_SIZE = 1024 * 1024  # 1MB for text
        MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB for images (base64 is larger)
        
        content_length = len(file_data.get('content', ''))
        
        if content_length > MAX_IMAGE_SIZE:
            raise ValueError("File content too large. Maximum size is 10MB.")
        
        file_type = file_data.get('type', '')
        if not file_type.startswith('image/') and content_length > MAX_TEXT_SIZE:
            raise ValueError("Text file too large. Maximum size is 1MB.")
        
        return True

    @staticmethod
    def validate_parameters(temperature, max_tokens, model=None):
        """
        Validate chat parameters
        
        Args:
            temperature (float): Temperature parameter
            max_tokens (int): Max tokens parameter
            model (str, optional): Model name
            
        Raises:
            ValueError: If parameters are invalid
        """
        if not (0.0 <= temperature <= 2.0):
            raise ValueError("Temperature must be between 0.0 and 2.0")
        
        if max_tokens < 1:
            raise ValueError("Max tokens must be at least 1")
        
        if model:
            model_limit = ChatService.get_model_token_limit(model)
            if max_tokens > model_limit:
                raise ValueError(f"Max tokens ({max_tokens}) exceeds model limit ({model_limit})")
