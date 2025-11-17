def DetectLanguage(user_text: str) -> int:
    
    # 0 für Deutsch, 1 für Englisch, sonst Fehler

    # iwie testen, am besten ohne AI Modell aufzurufen...

    return 0 


def ChooseModel (languag: int) -> str:

    # je nach Sprache bestes Model zurückgeben

    return "meta-llama-3.1-8b-instruct"


def CraftPrompt(user_text: str, language: int) -> str:
    
    # je nach Sprache besten Prompt zurückgeben

    # dafür besten prompt for user_text packen

    return user_text

def DetectDiffTopic (user_text: str) -> bool:
    
    # false wenn Thema passt, true wenn Theme falsch

    return False