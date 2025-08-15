# app.py — WhatsApp bulk send + webhook + Hugging Face Mistral

import os
import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from huggingface_hub import InferenceClient
import threading

# ================== LOAD ENV VARIABLES ==================
load_dotenv()

META_TOKEN = os.getenv("META_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "testtoken")
TEMPLATE_NAME = os.getenv("TEMPLATE_NAME", "hello_world")
TEMPLATE_LANG = os.getenv("TEMPLATE_LANG", "en_US")
HF_API_KEY = os.getenv("HF_API_KEY")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL")  # public CSV link

# ================== INIT FLASK APP ==================
app = Flask(__name__)

# ================== INIT HUGGING FACE CLIENT ==================
print("[MODEL] Connecting to Hugging Face API...")
hf_client = InferenceClient(
    model="mistralai/Mistral-7B-Instruct-v0.2",
    token=HF_API_KEY
)
print("[MODEL] Connected successfully!")

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

# ================== BULK SEND FROM GOOGLE SHEET ==================
def send_bulk_from_google_sheet():
    try:
        print("[CONTACTS] Fetching contacts from Google Sheet...")
        df = pd.read_csv(GOOGLE_SHEET_URL)
        if "phone" not in df.columns:
            raise ValueError("Google Sheet must have a 'phone' column.")
        for _, row in df.iterrows():
            send_template_message(row["phone"])
        print("[CONTACTS] Messages sent to all contacts!")
    except Exception as e:
        print(f"[ERROR] Could not load contacts: {e}")

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

        if "statuses" in value:
            print("[WEBHOOK] Ignored status update")
            return

        if "messages" in value:
            msg = value["messages"][0]
            sender = msg["from"]

            if msg["type"] == "text":
                user_text = msg["text"]["body"]
                print(f"[customer {sender}]: {user_text}")

                # Generate reply using Hugging Face API
                prompt = f"You are a friendly assistant.\nUser: {user_text}\nAssistant:"
                response = hf_client.text_generation(
                    prompt,
                    max_new_tokens=256,
                    temperature=0.7,
                    stop=["User:", "Assistant:"]
                )
                mistral_reply = response.strip()

                send_message(sender, mistral_reply)
    except Exception as e:
        print("[ERROR]", e)

# ================== MAIN EXECUTION ==================
if __name__ == "__main__":
    send_bulk_from_google_sheet()
    print("[SERVER] Starting webhook on port 5000...")
    app.run(host="0.0.0.0", port=5000, debug=True)
