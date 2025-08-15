# WhatsApp Chatbot with Local Mistral-7B

This project integrates the **WhatsApp Cloud API** with a locally running **Mistral-7B** model (via `llama-cpp-python`) to send bulk messages and hold conversations with WhatsApp contacts.

## 📌 Features
- Bulk send approved WhatsApp template messages from an Excel contact list
- Automatic replies to incoming messages using **Mistral-7B**
- Webhook for real-time communication
- Customizable template name & language via `.env` file

---

## 📂 Project Structure
```
meta-mistral/
│── app.py                   # Main chatbot application
│── contacts.xlsx            # Excel file containing phone numbers
│── mistral-7b-instruct-v0.2.Q4_K_M.gguf  # Local Mistral-7B model
│── llama_cpp_python-*.whl   # Prebuilt wheel for llama-cpp-python
│── requirements.txt         # Python dependencies
│── .env                     # Environment variables
│── .gitignore               # Ignored files for Git
```

---

## ⚙️ Setup Instructions

### 1️⃣ Install Python
Ensure you have **Python 3.10+** installed.

### 2️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/meta-mistral-whatsapp.git
cd meta-mistral-whatsapp
```

### 3️⃣ Create & Activate Virtual Environment
```bash
python -m venv venv
source venv/bin/activate    # Mac/Linux
venv\Scripts\activate     # Windows
```

### 4️⃣ Install Dependencies
```bash
pip install -r requirements.txt
```

If you have the `.whl` file for `llama-cpp-python`, install it manually:
```bash
pip install llama_cpp_python-0.3.2-cp310-cp310-win_amd64.whl
```

---

## 🛠 Environment Variables
Create a `.env` file in the project root with the following:
```
META_TOKEN=your_whatsapp_cloud_api_token
PHONE_NUMBER_ID=your_phone_number_id
VERIFY_TOKEN=testtoken
TEMPLATE_NAME=hello_world
TEMPLATE_LANG=en_US
```

- `META_TOKEN`: Your **WhatsApp Cloud API** permanent access token
- `PHONE_NUMBER_ID`: Found in your **Meta for Developers** dashboard
- `VERIFY_TOKEN`: Any random string to verify your webhook
- `TEMPLATE_NAME`: Approved WhatsApp message template name
- `TEMPLATE_LANG`: Language code of the template

---

## 📊 contacts.xlsx Format
The Excel file should have:
| name     | phone         |
|----------|--------------|
| John Doe | 919876543210 |
| Alice    | 918765432109 |

**Note:** Phone numbers **must be in the test list** inside Meta for Developers unless you have production approval.

---

## 🚀 Running the Bot

### Step 1: Send Bulk Messages
When you run the script, it first sends the approved template to all contacts in `contacts.xlsx`.

### Step 2: Start Webhook for Replies
The Flask server starts on port **5000** to receive messages.
```bash
python app.py
```

Use **ngrok** to make it public:
```bash
ngrok http 5000
```

Add the ngrok URL to your **WhatsApp Webhook** settings in Meta Developer Console.

---

## 💬 How It Works
1. User receives the **template message**
2. When they reply, the webhook captures it
3. The message is passed to the **Mistral-7B** model
4. Mistral generates a response and sends it back via WhatsApp Cloud API

---

## 🧠 Using Local Mistral-7B
We use the `llama-cpp-python` library to run Mistral on CPU/GPU.

Example:
```python
from llama_cpp import Llama

llm = Llama(model_path="mistral-7b-instruct-v0.2.Q4_K_M.gguf")
response = llm("Hello, how are you?", max_tokens=50)
print(response["choices"][0]["text"])
```

---

## ⚠️ Notes
- Make sure your **Meta App** is in **Development Mode** unless approved for production
- All recipients must be in the **Test Numbers** list for development mode
- Large models require **enough RAM** to run locally

---

## 📜 License
This project is open-source under the MIT License.
