# TEAM **Git-iT** 
CCI Start-up Hackathon 2025

# EduPal - AI-Powered Learning Assistant

> Teacher-controlled AI tutoring that prevents cheating while providing personalized learning

## Quick Set-up

### 1. Get Your Free API Key
- Visit [Groq Console](https://console.groq.com/)
- Sign up (free, no credit card)
- Create an API key and copy it

### 2. Setup & Run
```bash
# Setup backend
cd backend
echo "GROQ_API_KEY=your_groq_key_here" > .env
pip install -r requirements.txt
python main.py

# In new terminal - setup frontend
cd streamlit_app
pip install -r requirements.txt
streamlit run app.py
