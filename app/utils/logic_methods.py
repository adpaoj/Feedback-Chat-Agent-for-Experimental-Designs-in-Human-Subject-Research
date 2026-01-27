import json
from pathlib import Path
from langdetect import detect
from flask import current_app

def DetectLanguage(user_text: str) -> int:
    
    # 0 für Deutsch, 1 für Englisch, sonst Fehler

    try:
        lang = detect(user_text)
        if lang == "de":
            return 0
        elif lang == "en":
            return 1
        else:
            return -1
    except:
        return -1


def GetArcanaForLanguage(language: int) -> tuple:
    """
    Get the appropriate Arcana ID based on detected language.
    
    Args:
        language (int): Language code (0 for German, 1 for English, -1 for unknown)
    
    Returns:
        tuple: (arcana_id, base_url) for the selected language
    """
    arcanas = current_app.config.get('ARCANAS', {})
    
    if language == 0:
        # German Arcana
        arcana_config = arcanas.get('primary', {})
    elif language == 1:
        # English Arcana
        arcana_config = arcanas.get('secondary', {})
    else:
        # Fallback to primary
        arcana_config = arcanas.get('primary', {})
    
    return (
        arcana_config.get('id'),
        arcana_config.get('base_url')
    )


def ChooseModel (languag: int) -> str:

    # je nach Sprache bestes Model zurückgeben

    # noch die entsprechenden besten Modelle auswählen !!!!!!!!!

    if languag == 0:
        # bestes deutsches Modell
        return "llama-3.1-sauerkrautlm-70b-instruct"
    else:
        # bestes englisches Modell
        return "meta-llama-3.1-8b-instruct"


def CraftPrompt(user_text: str, language: int, req: int) -> str:
    
    # je nach Sprache besten Prompt zurückgeben
    # für req = 1 Bewertungsprompts, sonst nix
    # evtl für 2/else noch anderen Prompt für bessere Antwort?

    if language == 0:
        # deutschen prompt bauen
        if req == 1:
            final_prompt = open("data/dePrompt-Evaluate.txt", encoding="utf-8").read() + user_text
        else:
            final_prompt = open("data/dePrompt.txt", encoding="utf-8").read() + user_text
    else:
        # englischen prompt bauen
        if req == 1:
            final_prompt = open("data/enPrompt-Evaluate.txt", encoding="utf-8").read() + user_text
        else:
            final_prompt = open("data/enPrompt.txt", encoding="utf-8").read() + user_text

    return final_prompt

def DetectDiffTopic(user_text: str, language: int = 0, conversation_id: int = None) -> int:
    """
    Detect topic type with conversation context awareness.
    Uses existing conversation history from database to understand follow-up questions.
    
    Args:
        user_text (str): The user input text
        language (int): 0 for German, 1 for English
        conversation_id (int): Optional conversation ID to get context from history
    
    Returns:
        int: 0 = wrong topic, 1 = evaluation request, 2 = specific request
    """
    if not user_text or not user_text.strip():
        return 0
    
    text = user_text.lower()
    lang_key = "en" if language == 1 else "de"
    
    # Load keywords from config file
    config_path = Path("data/keywords.json")
    try:
        with open(config_path, encoding="utf-8") as f:
            keywords_config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
    
    lang_keywords = keywords_config.get(lang_key, {})
    rate_keywords = lang_keywords.get("rate", [])
    specific_keywords = lang_keywords.get("specific", [])
    follow_up_keywords = lang_keywords.get("follow-up", [])
    
    # Check for follow-up questions first - use conversation context
    if any(k in text for k in follow_up_keywords) and conversation_id:
        try:
            from app.services.conversation_service import ConversationService
            from flask_login import current_user
            
            # Get messages from conversation history
            messages = ConversationService.get_messages(conversation_id, current_user.id)
            
            if messages and len(messages) > 1:
                # Find the last user message (excluding current one)
                for msg in reversed(messages[:-1]):
                    if msg.role == 'user':
                        # Detect the topic of the last user message
                        last_user_text = msg.content.lower()
                        
                        if any(k in last_user_text for k in rate_keywords):
                            return 1
                        elif any(k in last_user_text for k in specific_keywords):
                            return 2
                        break
        except Exception as e:
            # Log but don't fail - fall back to regular detection
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Could not get conversation context: {e}")
    
    # Regular topic detection
    if any(k in text for k in rate_keywords):
        return 1
    elif any(k in text for k in specific_keywords):
        return 2
    else:
        return 0