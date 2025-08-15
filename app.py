import os
import requests
import pandas as pd
from flask import Flask, request
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

# ----------------- LOAD ENV -----------------
load_dotenv()

META_TOKEN = os.getenv("META_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
HF_API_KEY = os.getenv("HF_API_KEY")
GOOGLE_SHEET_CSV = os.getenv("GOOGLE_SHEET_CSV")

# ----------------- INIT APP -----------------
app = Flask(__name__)

# ----------------- INIT MODEL -----------------
print("[MODEL] Connecting to Hugging Face API...")
client = InferenceClient(
    "mistralai/Mistral-7B-Instruct-v0.2",
    token=HF_API_KEY
)
print("[MODEL] Connected successfully!")

# ----------------- LOAD CONTACTS -----------------
def load_contacts():
    try:
        df = pd.read_csv(GOOGLE_SHEET_CSV)
        if "phone" not in df.columns:
            raise ValueError("CSV must have 'phone' column")
        return df["phone"].astype(str).tolist()
    except Exception as e:
        print(f"[ERROR] Could not load contacts: {e}")
        return []

contacts = load_contacts()

# ----------------- SEND WHATSAPP MESSAGE -----------------
def send_whatsapp_message(phone_number, message):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "text": {"body": message}
    }
    response = requests.post(url, headers=headers, json=data)
    print(f"[SEND] To {phone_number}: {message} | Status: {response.status_code}")

# ----------------- MODEL REPLY -----------------
def get_model_reply(user_message):
    try:
        messages = [
            {"role": "user", "content": user_message}
        ]
        response = client.chat_completion(messages=messages, max_tokens=500)
        return response.choices[0].message["content"].strip()
    except Exception as e:
        print(f"[ERROR] Model call failed: {e}")
        return "Sorry, I couldn't process your request."

# ----------------- SEND TO ALL CONTACTS -----------------
def send_to_all_contacts():
    for contact in contacts:
        send_whatsapp_message(contact, "Hello! This is an automated test message.")

# ----------------- WEBHOOK VERIFY -----------------
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == VERIFY_TOKEN:
            return request.args.get("hub.challenge")
        return "Invalid verification token", 403

    data = request.get_json()
    if data and "entry" in data:
        try:
            phone_number = data["entry"][0]["changes"][0]["value"]["messages"][0]["from"]
            user_message = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
            print(f"[customer {phone_number}]: {user_message}")

            bot_reply = get_model_reply(user_message)
            send_whatsapp_message(phone_number, bot_reply)
        except Exception as e:
            print(f"[ERROR] Processing webhook: {e}")
    return "ok", 200

# ----------------- START -----------------
if __name__ == "__main__":
    print("[CONTACTS] Messages sent to all contacts!")
    send_to_all_contacts()
    print("[SERVER] Starting webhook on port 5000...")
    app.run(host="0.0.0.0", port=5000)
