"""
Main Routes Module
Handles HTTP endpoints for the chat interface
"""

from flask import render_template, jsonify, request, Response, stream_with_context, current_app, session
from flask_login import login_required, current_user
from app.main import bp
from app.services.conversation_service import ConversationService
from app.services.chat_service import ChatService, ModelAPIError
import logging
from app.utils import logic_methods as utils


logger = logging.getLogger(__name__)


@bp.route('/')
@login_required
def index():
    """
    Render the main chat interface
    
    Returns:
        HTML template with conversation list
    """
    try:
        conversations = ConversationService.get_user_conversations(current_user.id)
        return render_template('index.html', conversations=conversations)
    except Exception as e:
        logger.error(f"Error rendering index page: {e}")
        return render_template('index.html', conversations=[])


@bp.route('/get_conversations')
@login_required
def get_conversations():
    """
    API endpoint to retrieve conversations for the current user
    
    Returns:
        JSON: List of conversations with metadata
    """
    try:
        conversations = ConversationService.get_user_conversations(current_user.id)
        convo_list = [
            {
                'id': convo.id,
                'title': convo.title,
                'created_at': convo.created_at.strftime('%Y-%m-%d %H:%M'),
            }
            for convo in conversations
        ]
        return jsonify({'conversations': convo_list})
    except Exception as e:
        logger.error(f"Error fetching conversations: {e}")
        return jsonify({'error': 'Failed to load conversations'}), 500


@bp.route('/new_conversation', methods=['POST'])
@login_required
def new_conversation():
    """
    Create a new conversation
    
    Request JSON:
        - message (optional): Initial message to start the conversation
        
    Returns:
        JSON: New conversation metadata
    """
    try:
        data = request.get_json() or {}
        user_message = data.get('message', '').strip()

        conversation = ConversationService.create_conversation(current_user.id)

        if user_message:
            ConversationService.add_message(conversation.id, 'user', user_message)

        return jsonify({
            "conversation_id": conversation.id,
            "title": conversation.title,
            "created_at": conversation.created_at.strftime('%Y-%m-%d %H:%M'),
        })
    except Exception as e:
        logger.error(f"Error creating conversation: {e}")
        return jsonify({'error': 'Failed to create conversation'}), 500


@bp.route('/delete_conversation/<int:conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """
    Delete a specific conversation
    
    Args:
        conversation_id: ID of conversation to delete
        
    Returns:
        JSON: Success status
    """
    try:
        success = ConversationService.delete_conversation(conversation_id, current_user.id)
        if success:
            return jsonify({'success': True})
        return jsonify({'error': 'Conversation not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting conversation {conversation_id}: {e}")
        return jsonify({'error': 'Failed to delete conversation'}), 500


@bp.route('/conversation/<int:conversation_id>')
@login_required
def load_conversation(conversation_id):
    """
    Load messages for a specific conversation
    
    Args:
        conversation_id: ID of conversation to load
        
    Returns:
        JSON: Conversation metadata and messages
    """
    try:
        messages = ConversationService.get_messages(conversation_id, current_user.id)
        if messages is None:
            return jsonify({'error': 'Conversation not found'}), 404
            
        formatted_messages = [{
            'id': msg.id,
            'role': msg.role, 
            'content': msg.content,
            'timestamp': msg.timestamp.isoformat() if msg.timestamp else None
        } for msg in messages]
        
        return jsonify({
            'conversation_id': conversation_id, 
            'messages': formatted_messages
        })
    except Exception as e:
        logger.error(f"Error loading conversation {conversation_id}: {e}")
        return jsonify({'error': 'Failed to load conversation'}), 500


@bp.route('/reset', methods=['POST'])
@login_required
def reset():
    """
    Reset a conversation by deleting all its messages
    
    Request JSON:
        - conversation_id: ID of conversation to reset
        
    Returns:
        JSON: Success status
    """
    try:
        conversation_id = request.json.get('conversation_id')
        if not conversation_id:
            return jsonify({'error': 'Conversation ID required'}), 400
            
        success = ConversationService.reset_conversation(conversation_id, current_user.id)
        if success:
            return jsonify({'message': 'Conversation reset successfully'})
        return jsonify({'error': 'Conversation not found'}), 404
    except Exception as e:
        logger.error(f"Error resetting conversation: {e}")
        return jsonify({'error': 'Failed to reset conversation'}), 500


@bp.route('/chat_stream', methods=['POST'])
@login_required
def chat_stream():
    """
    Handle chat messages with streaming response
    
    Request JSON:
        - message: User message text
        - conversation_id (optional): Existing conversation ID
        - model: Model name to use
        - temperature: Sampling temperature (0.0-2.0)
        - max_tokens: Maximum tokens for response
        - system_prompt (optional): System instructions
        - base64_image (optional): Base64 encoded image
        
    Returns:
        Streaming response with generated text
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request data required'}), 400
        
        user_message = data.get('message', '').strip()
        model = data.get('model', 'meta-llama-3.1-8b-instruct')
        base64_image = data.get('base64_image', None)
        
        # Validate required fields
        if not user_message and not base64_image:
            return jsonify({'error': 'Message or image is required'}), 400


        # || Eigene Backend Logik ;) ||

        # 1) Art der Anfrage bestimmen
        req = utils.DetectDiffTopic(user_message)
        if req == 0:
            #return jsonify({'error': 'Bitte nur zum richtigen Thema fragen.'}), 400
            return jsonify({'error': True, 'message': 'Bitte nur zum richtigen Thema fragen.'}), 400

        # 2) Sprache erkennen
        lang = utils.DetectLanguage(user_message)
        if lang == -1:
            # return jsonify({'error': 'Bitte in Deutsch oder Englisch schreiben.'}), 400
            return jsonify({'error': True, 'message': 'Bitte in Deutsch oder Englisch schreiben.'}), 400

        # 3) Modell nach Sprache wählen
        model = utils.ChooseModel(lang)

        # 4) Prompt anpassen
        user_message = utils.CraftPrompt(user_message, lang, req)


        # Get or create conversation
        conversation_id = data.get('conversation_id')
        conversation = (ConversationService.get_conversation(conversation_id, current_user.id) 
                       if conversation_id else None)
        
        if not conversation:
            conversation = ConversationService.create_conversation(current_user.id)

        # Save user message
        if user_message:
            ConversationService.add_message(conversation.id, 'user', user_message)

        # Get parameters with validation
        try:
            temperature = float(data.get('temperature', 0.5))
            max_tokens = int(data.get('max_tokens', 1500))
            
            # Validate parameters
            ChatService.validate_parameters(temperature, max_tokens, model)
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid parameters: {e}")
            return jsonify({'error': f'Invalid parameters: {str(e)}'}), 400

        # Get system prompt from request or user settings
        system_prompt = data.get('system_prompt', '').strip()
        if not system_prompt:
            user_settings = current_user.settings or {}
            system_prompt = user_settings.get('system_prompt', '')

        # Fetch message history
        history_messages = conversation.messages

        # Prepare messages with context window management
        messages = ChatService.prepare_messages(
            history_messages=history_messages,
            current_message=user_message,
            base64_image=base64_image,
            system_prompt=system_prompt,
            model_name=model,
            max_tokens=max_tokens
        )

        # Get API client
        try:
            client = ChatService.get_openai_client()
        except ModelAPIError as e:
            logger.error(f"Failed to get API client: {e}")
            return jsonify({'error': str(e)}), 503

        def generate():
            """Generator function for streaming response"""
            assistant_reply = ""
            try:
                # Stream chat completion
                for content in ChatService.stream_chat_completion(
                    client=client,
                    messages=messages,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens
                ):
                    assistant_reply += content
                    yield content

            except ModelAPIError as e:
                # Handle API errors gracefully
                error_msg = f"\n\n[Error: {str(e)}]"
                logger.error(f"Model API error during streaming: {e}")
                yield error_msg
                
            except Exception as e:
                # Handle unexpected errors
                error_msg = f"\n\n[Unexpected error occurred]"
                logger.exception(f"Unexpected error during streaming: {e}")
                yield error_msg
                
            finally:
                # Save the assistant's reply to the database
                if assistant_reply:
                    try:
                        with current_app.app_context():
                            ConversationService.add_message(
                                conversation.id, 
                                'assistant', 
                                assistant_reply
                            )
                    except Exception as e:
                        logger.error(f"Failed to save assistant message: {e}")
                
                if base64_image:
                    logger.info("Image data processed")
        
        # Create streaming response
        response = Response(
            stream_with_context(generate()), 
            mimetype='text/event-stream'
        )
        response.headers['X-New-Conversation-Id'] = conversation.id
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['X-Accel-Buffering'] = 'no'
        
        return response
        
    except Exception as e:
        logger.exception(f"Unexpected error in chat_stream: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500


@bp.route('/get_models', methods=['GET'])
@login_required
def get_models():
    """
    Get available models from the API
    
    Uses session caching to avoid repeated API calls
    
    Returns:
        JSON: List of available models
    """

    # eigenes Modell zurückgeben
    return jsonify([
        {
            "id": "Experiment Feedback",
            "object": "model",
            "name": "Experiment Feedback Agent",
            "type": "chat",
            "input": ["text"]
        }
    ])



    # Check if models are cached in session
    if 'models' in session:
        return jsonify(session['models'])

    try:
        models = ChatService.get_models()
        session['models'] = models
        return jsonify(models)
    except ModelAPIError as e:
        logger.error(f"Error fetching models: {e}")
        return jsonify({
            "error": str(e),
            "message": "Failed to load models"
        }), 503
    except Exception as e:
        logger.exception(f"Unexpected error fetching models: {e}")
        return jsonify({
            "error": "Unexpected error occurred",
            "message": "Failed to load models"
        }), 500


@bp.route('/update_settings', methods=['POST'])
@login_required
def update_settings():
    """
    Update user settings
    
    Request JSON:
        - default_temperature: Default temperature value
        - default_max_tokens: Default max tokens value
        - system_prompt: Default system instructions
        
    Returns:
        JSON: Success status
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Settings data required'}), 400
        
        # Validate settings if present
        if 'default_temperature' in data:
            temp = float(data['default_temperature'])
            if not (0.0 <= temp <= 2.0):
                return jsonify({'error': 'Temperature must be between 0.0 and 2.0'}), 400
        
        if 'default_max_tokens' in data:
            tokens = int(data['default_max_tokens'])
            if tokens < 1:
                return jsonify({'error': 'Max tokens must be at least 1'}), 400
        
        # Update user settings
        current_user.settings = data
        from app.extensions import db
        db.session.commit()
        
        logger.info(f"Updated settings for user {current_user.id}")
        return jsonify({'success': True})
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid settings data: {e}")
        return jsonify({'error': 'Invalid settings data'}), 400
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return jsonify({'error': 'Failed to update settings'}), 500


@bp.route('/get_settings', methods=['GET'])
@login_required
def get_settings():
    """
    Get current user settings
    
    Returns:
        JSON: User settings dictionary
    """
    try:
        return jsonify(current_user.settings or {})
    except Exception as e:
        logger.error(f"Error fetching settings: {e}")
        return jsonify({}), 500
