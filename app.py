import os
import pandas as pd
import requests
from dotenv import load_dotenv
from flask import Flask, request, jsonify
import threading

# ========== LOAD ENV ==========
load_dotenv()
META_TOKEN = os.getenv("META_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "testtoken")
TEMPLATE_NAME = os.getenv("TEMPLATE_NAME", "hello_world")
TEMPLATE_LANG = os.getenv("TEMPLATE_LANG", "en_US")
HF_API_KEY = os.getenv("HF_API_KEY")
GOOGLE_SHEET_URL = os.getenv("GOOGLE_SHEET_URL")

# Flask App
app = Flask(__name__)

# ========== LOAD CONTACTS FROM GOOGLE SHEETS ==========
def load_contacts():
    try:
        df = pd.read_csv(GOOGLE_SHEET_URL)
        if "phone" not in df.columns:
            raise ValueError("Google Sheet must have a 'phone' column.")
        return df
    except Exception as e:
        print("[ERROR] Could not load contacts:", e)
        return pd.DataFrame(columns=["phone"])

# ========== WHATSAPP SEND FUNCTIONS ==========
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
    r = requests.post(url, headers=headers, json=payload)
    print(f"[TEMPLATE SENT] {to} -> {r.status_code} {r.text}")

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
    r = requests.post(url, headers=headers, json=payload)
    print(f"[MSG SENT] {to} -> {r.status_code} {r.text}")

# ========== HUGGING FACE MISTRAL API ==========
def mistral_reply(user_text):
    url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": f"You are a friendly assistant.\nUser: {user_text}\nAssistant:"}
    response = requests.post(url, headers=headers, json=payload)
    try:
        data = response.json()
        if isinstance(data, list) and "generated_text" in data[0]:
            return data[0]["generated_text"].split("Assistant:")[-1].strip()
        elif isinstance(data, dict) and "error" in data:
            return f"[HF API ERROR] {data['error']}"
        else:
            return "[ERROR] Unexpected HF API response."
    except Exception as e:
        return f"[ERROR] Failed to parse HF API response: {e}"

# ========== BULK SEND ==========
def send_bulk():
    contacts = load_contacts()
    for _, row in contacts.iterrows():
        phone = row["phone"]
        send_template_message(phone)

# ========== WEBHOOK VERIFICATION ==========
@app.route("/webhook", methods=["GET"])
def verify():
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if token == VERIFY_TOKEN:
        print("[WEBHOOK] Verified successfully")
        return challenge
    return "Invalid token", 403

# ========== WEBHOOK RECEIVER ==========
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    threading.Thread(target=process_incoming, args=(data,)).start()
    return jsonify(status="ok"), 200

# ========== PROCESS INCOMING ==========
def process_incoming(data):
    try:
        value = data["entry"][0]["changes"][0]["value"]
        if "statuses" in value:
            return  # Ignore delivery receipts
        if "messages" in value:
            msg = value["messages"][0]
            sender = msg["from"]
            if msg["type"] == "text":
                user_text = msg["text"]["body"]
                print(f"[INCOMING] {sender}: {user_text}")
                reply_text = mistral_reply(user_text)
                send_message(sender, reply_text)
    except Exception as e:
        print("[ERROR]", e)

# ========== MAIN ==========
if __name__ == "__main__":
    # Send initial messages
    send_bulk()
    # Start webhook
    app.run(host="0.0.0.0", port=5000, debug=True)
