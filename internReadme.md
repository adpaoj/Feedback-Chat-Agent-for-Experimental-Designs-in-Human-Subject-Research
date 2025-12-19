jo, hier paar kurze Infos zum Starten...

falls nicht alle Erweiterungen runtergeladen sind
alles auf einaml mit pip install requirements.txt oder so

du musst auf jeden Fall noch bei dir lokal die .env datei mit dem API Key (per mail bekommen) ausfülle
wahrscheinlich auch noch einen Registration-Token setzen, z.B. "1234", mit dem du dich auf der Seite erstmal registrieren musst

evtl was mit table database erzeugen... (falls da Fehler in die Richtung kommen... einfach chatgpt fragen wie - lösen wir dann später richtig für den Server)


so in kurz zum Code zur Übersicht
hauptsächlich interessant main/routes.py - hier "@bp.route('/chat_stream', methods=['POST'])" - da ist auch unser Backend drin
sonst noch static/js/main.js - hier "function handleChatSubmit(event) {"
unter utils/logic_methods.py liegen die Funktionen für unsere Backend Logik
unter data liegen unsere Prompts