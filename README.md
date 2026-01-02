# 🔊 THING – AI Voice Assistant (Python)

THING is a smart AI-powered voice assistant built using Python.  
It can understand voice & text commands, control system functions, play music, fetch news, open apps/websites, and chat using Groq’s LLaMA model.

---

## 🚀 Features

- 🎙️ Voice & Text Command Support
- 🤖 AI Chat using Groq (LLaMA 3.1)
- 🎵 Music Playback via YouTube
- 🌐 Open Websites & Desktop Apps
- 🔊 System Volume Control
- 💡 Screen Brightness Control
- 🧠 Memory System (remembers facts)
- 📰 Live News Updates
- 🖥️ Camera Access
- 🛑 Interrupt / Stop Speaking Anytime

---

## 🧠 Technologies Used

- Python 3.10+
- SpeechRecognition
- Groq API (LLaMA 3.1)
- Windows SAPI (Text-to-Speech)
- PyAutoGUI
- Screen Brightness Control
- Requests, OS, Threading

---

## 📁 Project Structure

THING/
│
├── main.py # Core assistant logic
├── clint.py # Groq AI client
├── MymusicLibrary.py # Music & voice aliases
├── memory.json # Stored memory
├── requirements.txt # Dependencies
├── .gitignore # Ignored files
└── README.md

---
## ⚙️ Installation & Setup

### 1️⃣ Clone Repository
```bash
git clone https://github.com/your-username/THING.git
cd THING

###2️⃣ Create Virtual Environment
python -m venv venv
venv\Scripts\activate

###3️⃣ Install Dependencies
pip install -r requirements.txt

###4️⃣ Set Groq API Key (IMPORTANT)

Create an environment variable:

Windows (PowerShell)

setx GROQ_API_KEY "your_api_key_here"


Restart terminal after setting the key.

### ▶️ Run THING
python main.py


Say “Hey Thing” or type commands 🎧

### 🛡️ Security Note

API keys are NOT hardcoded

.env and virtual environments are ignored

Safe for public GitHub hosting

### 👨‍💻 Author

Prabhu Shankar Mund (Raj)
BCA Student | Python Developer | AI & Automation Enthusiast

## ⭐ Final Note

This project focuses on real-world automation, voice control, and AI integration.
Feel free to fork, improve, or suggest enhancements.