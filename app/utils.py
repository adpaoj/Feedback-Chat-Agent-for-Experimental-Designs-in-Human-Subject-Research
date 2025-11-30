from langdetect import detect

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


def ChooseModel (languag: int) -> str:

    # je nach Sprache bestes Model zurückgeben

    # noch die entsprechenden besten Modelle auswählen !!!!!!!!!

    if languag == 0:
        # bestes deutsches Modell
        return "llama-3.1-sauerkrautlm-70b-instruct"
    else:
        # bestes englisches Modell
        return "meta-llama-3.1-8b-instruct"


def CraftPrompt(user_text: str, language: int) -> str:
    
    # je nach Sprache besten Prompt zurückgeben

    if language == 0:
        # deutschen prompt bauen
        final_prompt = open("data/dePrompt.txt", encoding="utf-8").read() + user_text
    else:
        # englischen prompt bauen
        final_prompt = open("data/enPrompt.txt", encoding="utf-8").read() + user_text

    return final_prompt

def DetectDiffTopic (user_text: str) -> bool:
    
    # false wenn Thema passt, true wenn Theme falsch

    return False