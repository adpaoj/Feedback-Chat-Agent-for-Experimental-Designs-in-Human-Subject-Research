"""
Conversation Service Module
Handles database operations for conversations and messages
"""

from app.models import Conversation, Message
from app.extensions import db
from datetime import datetime, timezone, timedelta
import logging


logger = logging.getLogger(__name__)


# Get the current UTC time with timezone offset
utc_now = datetime.now(timezone.utc)
berlin_time = utc_now + timedelta(hours=1)


class ConversationService:
    """Service for managing conversations and messages in the database"""
    
    @staticmethod
    def get_user_conversations(user_id):
        """
        Retrieve all conversations for a user that have at least one message
        
        Args:
            user_id (int): User ID
            
        Returns:
            list: List of Conversation objects ordered by creation date (newest first)
        """
        try:
            conversations = (
                Conversation.query
                .filter(Conversation.user_id == user_id, Conversation.messages.any())
                .order_by(Conversation.created_at.desc())
                .all()
            )
            logger.info(f"Retrieved {len(conversations)} conversations for user {user_id}")
            return conversations
        except Exception as e:
            logger.error(f"Error retrieving conversations for user {user_id}: {e}")
            return []

    @staticmethod
    def create_conversation(user_id, title=None):
        """
        Create a new conversation for a user
        
        Args:
            user_id (int): User ID
            title (str, optional): Conversation title
            
        Returns:
            Conversation: Newly created conversation object
            
        Raises:
            Exception: If database operation fails
        """
        try:
            conversation = Conversation(user_id=user_id)
            if title:
                conversation.title = title
            db.session.add(conversation)
            db.session.commit()
            logger.info(f"Created new conversation {conversation.id} for user {user_id}")
            return conversation
        except Exception as e:
            logger.error(f"Error creating conversation for user {user_id}: {e}")
            db.session.rollback()
            raise

    @staticmethod
    def get_conversation(conversation_id, user_id):
        """
        Get a specific conversation by ID, ensuring it belongs to the user
        
        Args:
            conversation_id (int): Conversation ID
            user_id (int): User ID
            
        Returns:
            Conversation: Conversation object or None if not found
        """
        try:
            conversation = Conversation.query.filter_by(
                id=conversation_id, 
                user_id=user_id
            ).first()
            
            if conversation:
                logger.debug(f"Retrieved conversation {conversation_id} for user {user_id}")
            else:
                logger.warning(f"Conversation {conversation_id} not found for user {user_id}")
                
            return conversation
        except Exception as e:
            logger.error(f"Error retrieving conversation {conversation_id}: {e}")
            return None

    @staticmethod
    def delete_conversation(conversation_id, user_id):
        """
        Delete a conversation and all its messages
        
        Args:
            conversation_id (int): Conversation ID to delete
            user_id (int): User ID (for authorization)
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            conversation = Conversation.query.filter_by(
                id=conversation_id, 
                user_id=user_id
            ).first()
            
            if conversation:
                db.session.delete(conversation)
                db.session.commit()
                logger.info(f"Deleted conversation {conversation_id} for user {user_id}")
                return True
            else:
                logger.warning(f"Attempted to delete non-existent conversation {conversation_id}")
                return False
        except Exception as e:
            logger.error(f"Error deleting conversation {conversation_id}: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def add_message(conversation_id, role, content):
        """
        Add a message to a conversation
        
        Args:
            conversation_id (int): Conversation ID
            role (str): Message role ('user' or 'assistant')
            content (str): Message content
            
        Returns:
            Message: Created message object
            
        Raises:
            Exception: If database operation fails
        """
        try:
            message = Message(
                role=role, 
                content=content, 
                conversation_id=conversation_id
            )
            db.session.add(message)
            db.session.commit()
            
            # Update conversation title if it's the first user message
            conversation = Conversation.query.get(conversation_id)
            if conversation and len(conversation.messages) == 1 and role == 'user':
                conversation.set_title()
                db.session.commit()
                logger.info(f"Set title for conversation {conversation_id}: {conversation.title}")
            
            logger.debug(f"Added {role} message to conversation {conversation_id}")
            return message
        except Exception as e:
            logger.error(f"Error adding message to conversation {conversation_id}: {e}")
            db.session.rollback()
            raise

    @staticmethod
    def get_messages(conversation_id, user_id):
        """
        Get all messages for a conversation
        
        Args:
            conversation_id (int): Conversation ID
            user_id (int): User ID (for authorization)
            
        Returns:
            list: List of Message objects or None if conversation not found
        """
        try:
            conversation = ConversationService.get_conversation(conversation_id, user_id)
            if not conversation:
                return None
            
            messages = conversation.messages
            logger.debug(f"Retrieved {len(messages)} messages for conversation {conversation_id}")
            return messages
        except Exception as e:
            logger.error(f"Error retrieving messages for conversation {conversation_id}: {e}")
            return None

    @staticmethod
    def reset_conversation(conversation_id, user_id):
        """
        Delete all messages in a conversation without deleting the conversation itself
        
        Args:
            conversation_id (int): Conversation ID
            user_id (int): User ID (for authorization)
            
        Returns:
            bool: True if reset successfully, False otherwise
        """
        try:
            conversation = ConversationService.get_conversation(conversation_id, user_id)
            if conversation:
                Message.query.filter_by(conversation_id=conversation.id).delete()
                db.session.commit()
                logger.info(f"Reset conversation {conversation_id} (deleted all messages)")
                return True
            else:
                logger.warning(f"Attempted to reset non-existent conversation {conversation_id}")
                return False
        except Exception as e:
            logger.error(f"Error resetting conversation {conversation_id}: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def update_message(message_id, new_content):
        """
        Update the content of an existing message
        
        Args:
            message_id (int): Message ID
            new_content (str): New message content
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            message = Message.query.get(message_id)
            if message:
                message.content = new_content
                db.session.commit()
                logger.info(f"Updated message {message_id}")
                return True
            else:
                logger.warning(f"Message {message_id} not found for update")
                return False
        except Exception as e:
            logger.error(f"Error updating message {message_id}: {e}")
            db.session.rollback()
            return False

    @staticmethod
    def delete_messages_after(conversation_id, message_id, user_id):
        """
        Delete all messages after a specific message (useful for regeneration)
        
        Args:
            conversation_id (int): Conversation ID
            message_id (int): Message ID to delete from
            user_id (int): User ID (for authorization)
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            conversation = ConversationService.get_conversation(conversation_id, user_id)
            if not conversation:
                return False
            
            # Get the timestamp of the target message
            target_message = Message.query.get(message_id)
            if not target_message or target_message.conversation_id != conversation_id:
                logger.warning(f"Message {message_id} not found in conversation {conversation_id}")
                return False
            
            # Delete all messages after this timestamp
            Message.query.filter(
                Message.conversation_id == conversation_id,
                Message.timestamp > target_message.timestamp
            ).delete()
            
            db.session.commit()
            logger.info(f"Deleted messages after {message_id} in conversation {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting messages after {message_id}: {e}")
            db.session.rollback()
            return False
