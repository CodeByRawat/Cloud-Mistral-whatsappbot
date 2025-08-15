# bulk_send.py — sends hello_world to all contacts, webhook handles replies via local Mistral-7B

import os
import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from llama_cpp import Llama
import threading

# ================== LOAD ENV VARIABLES ==================
load_dotenv()

META_TOKEN = os.getenv("META_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "testtoken")
TEMPLATE_NAME = os.getenv("TEMPLATE_NAME", "hello_world")
TEMPLATE_LANG = os.getenv("TEMPLATE_LANG", "en_US")

# ================== INIT FLASK APP ==================
app = Flask(__name__)

# ================== LOAD MISTRAL MODEL ==================
print("[MODEL] Loading Mistral-7B model locally... This may take a minute.")
llm = Llama(
    model_path="mistral-7b-instruct-v0.2.Q4_K_M.gguf",  # path to your model file
    n_ctx=4096,
    n_threads=8,      # adjust based on CPU cores
    n_gpu_layers=0    # set >0 if GPU is available
)
print("[MODEL] Mistral loaded successfully!")

# ================== WHATSAPP SEND FUNCTIONS ==================
def send_template_message(to):
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": str(to),
        "type": "template",
        "template": {"name": TEMPLATE_NAME, "language": {"code": TEMPLATE_LANG}}
    }
    print(f"[client {to}]: Sending {TEMPLATE_NAME}")
    r = requests.post(url, headers=headers, json=payload)
    print(f"[TEMPLATE RESPONSE] {r.status_code}: {r.text}")

def send_message(to, text):
    url = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": str(to),
        "type": "text",
        "text": {"body": text}
    }
    print(f"[client {to}]: {text}")
    r = requests.post(url, headers=headers, json=payload)
    print(f"[MESSAGE RESPONSE] {r.status_code}: {r.text}")

# ================== BULK SEND FROM EXCEL ==================
def send_bulk_from_excel(file_path):
    df = pd.read_excel(file_path)
    for _, row in df.iterrows():
        phone = row["phone"]
        send_template_message(phone)

# ================== WEBHOOK VERIFICATION ==================
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if token == VERIFY_TOKEN:
        print("[WEBHOOK] Verified")
        return challenge
    return "Invalid token", 403

# ================== WEBHOOK RECEIVER ==================
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    threading.Thread(target=process_incoming, args=(data,)).start()
    return jsonify(status="ok"), 200

# ================== PROCESS INCOMING MESSAGES ==================
def process_incoming(data):
    try:
        value = data["entry"][0]["changes"][0]["value"]

        # Ignore delivery/read receipts
        if "statuses" in value:
            print("[WEBHOOK] Ignored status update")
            return

        # Handle actual messages
        if "messages" in value:
            msg = value["messages"][0]
            sender = msg["from"]

            if msg["type"] == "text":
                user_text = msg["text"]["body"]
                print(f"[customer {sender}]: {user_text}")

                # Generate reply from Mistral
                prompt = f"You are a friendly assistant.\nUser: {user_text}\nAssistant:"
                output = llm(prompt, max_tokens=256, stop=["User:", "Assistant:"])
                mistral_reply = output["choices"][0]["text"].strip()

                send_message(sender, mistral_reply)
    except Exception as e:
        print("[ERROR]", e)

# ================== MAIN EXECUTION ==================
if __name__ == "__main__":
    # Step 1: Send initial messages from Excel
    send_bulk_from_excel("contacts.xlsx")

    # Step 2: Start webhook for replies
    print("[SERVER] Starting webhook on port 5000...")
    app.run(port=5000, debug=True)
