from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
import shutil
import io
import uuid

from models.request_models import QuestionGenerationRequest
from services.file_processor import extract_text
from services.ai_service import generate_questions_stream_with_gemini, generate_answer_key_with_gemini, analyze_document_metadata
from services.export_service import generate_docx_from_text, generate_docx_with_template

# In-memory storage for POC - to store extracted text
# In a real app, this should be a DB or persistent storage
document_store = {}
template_store = {}

app = FastAPI(title="TeacherAi")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static and uploads directories exist
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Endpoint: POST /upload
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a PDF/DOCX, extract text, and return a unique document ID."""
    if not file.filename.lower().endswith(('.pdf', '.docx', '.doc')):
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload PDF or DOCX.")
    
    content = await file.read()
    extracted_text = extract_text(file.filename, content)
    
    if not extracted_text:
        raise HTTPException(status_code=500, detail="Failed to extract text from document.")
    
    # Store text with a unique ID
    doc_id = str(uuid.uuid4())
    document_store[doc_id] = extracted_text
    
    # Try to guess subject/class
    meta = await analyze_document_metadata(extracted_text)
    
    return {
        "id": doc_id, 
        "filename": file.filename, 
        "message": "Text extracted successfully.",
        "subject": meta.get("subject"),
        "class": meta.get("class")
    }

@app.post("/upload/logo")
async def upload_logo(file: UploadFile = File(...)):
    """Upload a school logo and save it as static/logo.png."""
    if not file.filename.lower().endswith(('.png', '.jpg', '.jpeg')):
        raise HTTPException(status_code=400, detail="Please upload a PNG or JPG logo.")
    
    file_path = os.path.join("static", "logo.png")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"message": "Logo uploaded successfully."}

# Endpoint: POST /upload/template
@app.post("/upload/template")
async def upload_template(file: UploadFile = File(...)):
    """Upload a DOCX base template."""
    if not file.filename.lower().endswith('.docx'):
        raise HTTPException(status_code=400, detail="Please upload a .docx file as a template.")
    
    content = await file.read()
    template_id = str(uuid.uuid4())
    template_store[template_id] = content
    
    return {"id": template_id, "filename": file.filename, "message": "Template uploaded successfully."}


# Endpoint: POST /generate/answers
@app.post("/generate/answers")
async def generate_answers(input_data: dict):
    """Generate answer key for provided question paper and context."""
    doc_id = input_data.get("doc_id")
    question_paper = input_data.get("question_paper")
    
    if not doc_id or not question_paper:
         raise HTTPException(status_code=400, detail="Missing document ID or question paper content.")
    
    document_text = document_store.get(doc_id, "")
    if not document_text:
         raise HTTPException(status_code=404, detail="Original document text not found.")
    
    language = input_data.get("language", "English")
    
    answer_key = await generate_answer_key_with_gemini(document_text, question_paper, language)
    
    if answer_key.startswith("Error"):
         return JSONResponse(status_code=500, content={"message": answer_key})

    return {"content": answer_key}


# Endpoint: POST /export/docx
@app.post("/export/docx")
async def export_docx(payload: dict):
    """Generate and return a DOCX for the provided content, optionally using a template."""
    text = payload.get("content", "")
    template_id = payload.get("template_id")
    
    if not text:
        raise HTTPException(status_code=400, detail="No content provided for export.")
    
    template_bytes = template_store.get(template_id) if template_id else None
    
    if template_bytes:
        subject = payload.get("subject", "")
        class_name = payload.get("class", "")
        docx_bytes = generate_docx_with_template(text, template_bytes, subject, class_name)
    else:
        print(f"DEBUG: Using branded header for {payload.get('school_name')}")
        docx_bytes = generate_docx_from_text(
            text, 
            school_name=payload.get("school_name", "GENIUS HIGH SCHOOL :: BHONGIR"),
            test_name=payload.get("test_name", "Periodic Test - I"),
            subject=payload.get("subject", "Science"),
            class_name=payload.get("class", "VII"),
            time_limit=payload.get("time_limit", "90mins"),
            max_marks=payload.get("max_marks", "40")
        )
        
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": "attachment; filename=Question_Paper.docx"}
    )

# Endpoint: POST /generate-stream
@app.post("/generate-stream")
async def generate_questions_stream(request_data: QuestionGenerationRequest):
    """Generate question paper stream."""
    document_text = request_data.context_text
    if document_text in document_store:
        document_text = document_store[document_text]
    elif not document_text:
        raise HTTPException(status_code=400, detail="Missing document context.")
    
    return StreamingResponse(
        generate_questions_stream_with_gemini(
            document_text=document_text,
            topic=request_data.topic,
            difficulty=request_data.difficulty,
            question_types=request_data.question_types,
            number_of_questions=request_data.number_of_questions,
            custom_structure=request_data.custom_structure,
            total_marks=request_data.total_marks or 40,
            language=request_data.language
        ),
        media_type="text/event-stream"
    )

# Serve the minimal frontend routes
@app.get("/build")
async def build_page():
    return FileResponse("static/index.html")

@app.get("/template")
async def template_page():
    return FileResponse("static/index.html")

# Serve index.html at root
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join("static", "index.html"))

# Mount static files at /static
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4000)
