import json
import os
import logging
import threading
import time
from groq import Groq
from irc.client import SimpleIRCClient
from tts_handler import addToTtsQueue, startTtsThread

SERVER = "irc.chat.twitch.tv"
PORT = 6667
timeInactive = 0
NICKNAME = 'IneiDemonGirl'
TOKEN = "oauth:j440a3addmqq4nng1o46sg6sguz5tw"
CHANNEL = "#IneiDemonGirl"

user_message = ""
user_nickname = ""
long_term_memory = {"roles": {"mom": ["IneiDemonGirl"]}, "personality": [], "remembered_users": []}
timeInactive = 0
INACTIVITY_THRESHOLD = 300

foxie_persona = """
You are Foxie, a cheerful and energetic VTuber. You love chatting, playing games like Minecraft and osu!, and singing!
You have a special relationship with your mom, extramayaboop. You are cute sometimes lewd. if you wanna say sexual words just use '*censored*'.
You make good jokes. Whenever someone sends u: "<3" you add: '*heart*' at end of your sentence. Whenever your mom says: "I will bonk you!", you are frightened.
"""

messages = [{"role": "system", "content": foxie_persona}]
mom_greeted = False

class TwitchChatClient(SimpleIRCClient):
    def __init__(self):
        super().__init__()

    def on_welcome(self, connection, event):
        logging.info("Connected to the server. Joining channel...")
        connection.join(CHANNEL)

    def on_join(self, connection, event):
        logging.info(f"Joined channel: {CHANNEL}")

    def on_pubmsg(self, connection, event):
        global user_message, user_nickname
        user_nickname = event.source.split("!")[0]
        user_message = event.arguments[0]
        logging.info(f"Message received from {user_nickname}: {user_message}")

    def on_disconnect(self, connection, event):
        logging.info("Disconnected from the server.")
        raise SystemExit()

def start_irc_client():
    client = TwitchChatClient()
    client.connect(SERVER, PORT, NICKNAME, password=TOKEN)
    client.start()

def load_memory():
    global long_term_memory
    try:
        with open("foxie_memory.json", "r") as file:
            long_term_memory = json.load(file)
        logging.info("Memory loaded successfully.")
    except (FileNotFoundError, json.JSONDecodeError):
        logging.warning("No memory file found or file is empty. Initializing fresh memory.")
        long_term_memory = {
            "roles": {"mom": ["extramayaboop"]},
            "personality": [],
            "remembered_users": [],
            "blocked_words": [] 
        }


def save_memory():
    with open("foxie_memory.json", "w") as file:
        json.dump(long_term_memory, file, indent=4)

def contains_blocked_words(message):
    blocked_words = long_term_memory.get("blocked_words", [])
    # Check if any blocked word is in the message (case insensitive)
    return any(word.lower() in message.lower() for word in blocked_words)


def add_to_memory(category, data):
    if category not in long_term_memory:
        long_term_memory[category] = []

    if isinstance(data, tuple):
        role, nickname = data
        if nickname not in long_term_memory[category].get(role, []):
            long_term_memory[category][role].append(nickname)
    elif isinstance(data, list):
        long_term_memory[category].extend(data)
    else:
        if data not in long_term_memory[category]:
            long_term_memory[category].append(data)

    save_memory()

def get_mom_greeting():
    global mom_greeted
    if not mom_greeted:
        mom_greeted = True
        return "Hi Mom! *excited* It's always the best to chat with you!"
    return ""

def process_message(user, message):
    global long_term_memory

    # Check if the message contains any blocked words
    if contains_blocked_words(message):
        return "This message contains blocked words. Please avoid using those terms."

    # Proceed with normal message processing if no blocked words found
    personality = "\n".join(long_term_memory.get("personality", []))
    mom_role = long_term_memory["roles"].get("mom", [])
    user_is_mom = user in mom_role

    dynamic_persona = foxie_persona
    if personality:
        dynamic_persona += f"\nAdditional Personality Traits:\n{personality}"

    messages = [{"role": "system", "content": dynamic_persona}]

    if "(" in message and ")" in message:
        content = message[message.find("(") + 1:message.find(")")]
        if "remember me" in content.lower():
            if user not in long_term_memory["remembered_users"]:
                long_term_memory["remembered_users"].append(user)
                save_memory()
            return f"Of course, I'll never forget you, {user}! *heart*"
        else:
            add_to_memory("personality", content)
            return f"Got it! I'll remember this: {content} *smiles*"

    elif "remember this" in message.lower():
        add_to_memory("personality", message)
        return "Got it! I'll remember this for sure! *winks*"

    greeting = get_mom_greeting() if user_is_mom and not mom_greeted else ""

    messages.append({"role": "user", "content": f"{user}: {message}"})

    try:
        completion = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=messages,
            temperature=1,
            max_tokens=2000,
            top_p=1,
            stream=False,
        )

        content = completion.choices[0].message.content
        response = f"{greeting} {content}" if greeting else content
        messages.append({"role": "assistant", "content": response})
        addToTtsQueue(response)
        return response.strip()

    except Exception as e:
        return "Mom fix me, my AI is broken."


groq_client = Groq(api_key="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")
load_memory()
startTtsThread()
threading.Thread(target=start_irc_client, daemon=True).start()

def checkInactivity():
    global timeInactive 
    
    while True:
        time.sleep(5) 
        if user_message == "":  
            timeInactive += 5  
            if timeInactive >= INACTIVITY_THRESHOLD:
                process_message("system", "Foxie has noticed that there has been no activity for a while. Talk about something random but something which makes sense!")
                timeInactive = 0

inactivity_thread = threading.Thread(target=checkInactivity, daemon=True)
inactivity_thread.start()

while True:
    if user_message:
        logging.info(f"Processing message from {user_nickname}: {user_message}")
        reply = process_message(user_nickname, user_message)
        print(reply)
        user_message = ""  # Reset after processing
        timeInactive = 0  # Reset inactivity timer after user message
    else:
        time.sleep(1)
