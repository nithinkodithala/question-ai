# Question AI - POC

A simple backend-focused web application built with FastAPI and Gemini AI that allows teachers to generate question papers from uploaded PDF/DOCX documents.

## 🚀 Getting Started

### 1. Installation
Install the required Python packages:
```bash
pip install -r requirements.txt
```

### 2. Configuration
Create or edit the `.env` file and add your Google Gemini API key:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

### 3. Run the Application
Start the FastAPI server:
```bash
python main.py
```
Alternatively, use uvicorn:
```bash
uvicorn main:app --reload
```

### 4. Access the POC
Open your browser and navigate to:
[http://localhost:8000](http://localhost:8000)

---

## 🛠️ Features
- **File Upload:** Extract text from PDF/DOCX files.
- **AI Question Generation:** Customizable parameters (Topic, Difficulty, Bloom's Level, Question Types).
- **Export Options:** Download generated question papers as PDF or DOCX.
- **Minimalistic UI:** Clean dashboard for teacher interaction.

## 📁 Project Structure
- `main.py`: Entry point and API routes.
- `services/`: Core logic for file processing, AI, and exports.
- `models/`: Data models for requests.
- `utils/`: Text cleaning and utilities.
- `static/`: Minimal frontend assets.
- `uploads/`: Temporary storage for uploaded files (if needed).
