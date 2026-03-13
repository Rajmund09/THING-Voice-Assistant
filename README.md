# 🔊 THING – AI Voice Assistant (Python)

**THING** is an AI-powered voice assistant built with **Python** that can understand both **voice and text commands**.
It performs system automation, plays music, fetches news, opens apps/websites, and can even **chat intelligently using Groq's LLaMA model**.

This project demonstrates **AI integration, automation, voice recognition, and real-world assistant capabilities**.

---

# 🚀 Features

* 🎙️ **Voice & Text Commands** – Control the assistant using voice or keyboard input
* 🤖 **AI Chat (Groq LLaMA 3.1)** – Smart conversation and question answering
* 🎵 **Music Playback** – Plays songs directly from YouTube
* 🌐 **Open Websites & Applications** – Launch common tools instantly
* 🔊 **System Volume Control** – Increase, decrease, or mute volume
* 💡 **Screen Brightness Control** – Adjust brightness dynamically
* 🧠 **Memory System** – Stores and recalls important information
* 📰 **Live News Updates** – Fetches latest news using APIs
* 📷 **Camera Access** – Open and control webcam
* 🛑 **Interrupt System** – Stop the assistant while it is speaking

---

# 🧠 Technologies Used

| Technology                | Purpose                       |
| ------------------------- | ----------------------------- |
| Python 3.10+              | Core Programming Language     |
| SpeechRecognition         | Voice input processing        |
| Groq API (LLaMA 3.1)      | AI conversation engine        |
| Windows SAPI              | Text-to-Speech engine         |
| PyAutoGUI                 | System automation             |
| Screen Brightness Control | Brightness management         |
| Requests                  | API communication             |
| OS & Threading            | System control & multitasking |

---

# 📁 Project Structure

```
THING/
│
├── main.py              # Core assistant logic
├── clint.py             # Groq AI client integration
├── MymusicLibrary.py    # Music commands & aliases
├── memory.json          # Stored memory data
├── requirements.txt     # Python dependencies
├── .gitignore           # Ignored files
└── README.md            # Project documentation
```

---

# ⚙️ Installation & Setup

## 1️⃣ Clone the Repository

```bash
git clone https://github.com/your-username/THING.git
cd THING
```

---

## 2️⃣ Create Virtual Environment

```bash
python -m venv venv
```

Activate the environment:

### Windows

```bash
venv\Scripts\activate
```

### Mac / Linux

```bash
source venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 4️⃣ Set Groq API Key (IMPORTANT)

Create an environment variable:

### Windows (PowerShell)

```bash
setx GROQ_API_KEY "your_api_key_here"
```

After setting the key, **restart the terminal**.

---

# ▶️ Run the Assistant

```bash
python main.py
```

Then say:

> **"Hey Thing"**

or type commands directly in the terminal 🎧

---

# 🛡️ Security Note

* API keys are **never hardcoded**
* `.env` and virtual environments are **ignored using `.gitignore`**
* Safe to upload and share on **public GitHub repositories**

---

# 👨‍💻 Author

**Prabhu Shankar Mund (Raj)**
🎓 BCA Student
🐍 Python Developer
🤖 AI & Automation Enthusiast

---

# ⭐ Final Note

This project focuses on **real-world AI automation and voice control systems**.

If you like this project:

⭐ Star the repository
🍴 Fork the project
💡 Suggest improvements

---

**THING – Your Personal AI Assistant Powered by Python 🚀**
