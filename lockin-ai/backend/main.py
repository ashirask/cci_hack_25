# Receives requests from frontend

# Stores teacher's prompt and PDF locations

# Routes questions to the RAG system

# Returns AI responses back to frontend
from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import json
import os
import uuid
from datetime import datetime
import shutil

# Import RAG system (to be implemented in rag.py)
try:
    from rag import SimpleRAG
    rag_system = SimpleRAG()
except ImportError:
    # Fallback for development
    rag_system = None

app = FastAPI(
    title="LOCKIN API",
    description="AI-powered educational assistant with teacher-controlled RAG",
    version="1.0.0"
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data Models
class CourseCreate(BaseModel):
    courseName: str
    teacherPrompt: str

class ChatRequest(BaseModel):
    courseId: str
    message: str

class CourseResponse(BaseModel):
    id: str
    courseName: str
    teacherPrompt: str
    documents: List[str]
    createdAt: str

class ChatResponse(BaseModel):
    answer: str
    courseId: str

class UploadResponse(BaseModel):
    message: str
    filename: str
    courseId: str

# File paths
DATA_DIR = "backend/data"
DOCUMENTS_DIR = os.path.join(DATA_DIR, "documents")
COURSES_FILE = os.path.join(DATA_DIR, "courses.json")

# Ensure directories exist
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(COURSES_FILE), exist_ok=True)

def load_courses() -> List[dict]:
    """Load courses from JSON file"""
    try:
        if os.path.exists(COURSES_FILE):
            with open(COURSES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"Error loading courses: {e}")
        return []

def save_courses(courses: List[dict]):
    """Save courses to JSON file"""
    try:
        with open(COURSES_FILE, 'w', encoding='utf-8') as f:
            json.dump(courses, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving courses: {e}")
        raise HTTPException(status_code=500, detail="Failed to save course data")

def find_course_by_id(course_id: str) -> Optional[dict]:
    """Find a course by ID"""
    courses = load_courses()
    return next((course for course in courses if course["id"] == course_id), None)

def create_demo_course():
    """Create a demo course for testing if no courses exist"""
    courses = load_courses()
    if not courses:
        demo_course = {
            "id": str(uuid.uuid4()),
            "courseName": "Biology 101 - Demo",
            "teacherPrompt": "You are a helpful biology tutor. Explain concepts clearly but never give direct answers to specific test questions. Guide students to understand the underlying principles.",
            "documents": [],
            "createdAt": datetime.now().isoformat()
        }
        courses.append(demo_course)
        save_courses(courses)
        print("📚 Demo course created for testing")

# Create demo course on startup
create_demo_course()

# API Routes
@app.get("/")
async def root():
    return {
        "message": "EduPal API Server",
        "version": "1.0.0",
        "endpoints": {
            "courses": {
                "GET": "/courses",
                "POST": "/courses"
            },
            "chat": {
                "POST": "/chat"
            },
            "upload": {
                "POST": "/upload/{course_id}"
            }
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(course_data: CourseCreate):
    """
    Create a new course with teacher's custom prompt
    """
    try:
        if not course_data.courseName.strip():
            raise HTTPException(status_code=400, detail="Course name is required")
        
        if not course_data.teacherPrompt.strip():
            raise HTTPException(status_code=400, detail="Teacher prompt is required")

        courses = load_courses()
        
        new_course = {
            "id": str(uuid.uuid4()),
            "courseName": course_data.courseName.strip(),
            "teacherPrompt": course_data.teacherPrompt.strip(),
            "documents": [],
            "createdAt": datetime.now().isoformat()
        }
        
        courses.append(new_course)
        save_courses(courses)
        
        print(f"✅ New course created: {new_course['courseName']} (ID: {new_course['id']})")
        return new_course
        
    except Exception as e:
        print(f"❌ Error creating course: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create course: {str(e)}")

@app.get("/courses", response_model=List[CourseResponse])
async def get_courses():
    """
    Get all available courses
    """
    try:
        courses = load_courses()
        return courses
    except Exception as e:
        print(f"❌ Error loading courses: {e}")
        raise HTTPException(status_code=500, detail="Failed to load courses")

@app.get("/courses/{course_id}", response_model=CourseResponse)
async def get_course(course_id: str):
    """
    Get a specific course by ID
    """
    course = find_course_by_id(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@app.post("/upload/{course_id}", response_model=UploadResponse)
async def upload_document(course_id: str, file: UploadFile = File(...)):
    """
    Upload a document (PDF, TXT) to a specific course
    """
    try:
        # Validate course exists
        course = find_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Validate file type
        allowed_extensions = {'.pdf', '.txt', '.docx', '.md'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Generate unique filename
        unique_filename = f"{course_id}_{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(DOCUMENTS_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Update course documents
        courses = load_courses()
        for c in courses:
            if c["id"] == course_id:
                c["documents"].append(unique_filename)
                break
        
        save_courses(courses)
        
        print(f"✅ Document uploaded: {file.filename} -> {unique_filename} for course {course['courseName']}")
        
        return UploadResponse(
            message="File uploaded successfully",
            filename=unique_filename,
            courseId=course_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@app.post("/chat", response_model=ChatResponse)
async def chat_with_ai(chat_request: ChatRequest):
    """
    Chat with AI using course-specific RAG system
    """
    try:
        if not rag_system:
            raise HTTPException(status_code=503, detail="RAG system not available")
        
        # Validate course exists
        course = find_course_by_id(chat_request.courseId)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")
        
        if not chat_request.message.strip():
            raise HTTPException(status_code=400, detail="Message cannot be empty")
        
        print(f"💬 Chat request for course: {course['courseName']}")
        print(f"   Question: {chat_request.message}")
        
        # Use RAG system to process the question
        response = rag_system.process_question(course, chat_request.message)
        
        print(f"   AI Response: {response[:100]}...")
        
        return ChatResponse(
            answer=response,
            courseId=chat_request.courseId
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in chat: {e}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

@app.delete("/courses/{course_id}")
async def delete_course(course_id: str):
    """Delete a course and its associated files"""
    try:
        courses = load_courses()
        course_to_delete = next((c for c in courses if c["id"] == course_id), None)
        
        if not course_to_delete:
            raise HTTPException(status_code=404, detail="Course not found")
        
        # Remove associated files
        for doc_path in course_to_delete.get("documents", []):
            full_path = os.path.join(DOCUMENTS_DIR, doc_path)
            if os.path.exists(full_path):
                os.remove(full_path)
        
        # Remove course from list
        courses = [c for c in courses if c["id"] != course_id]
        save_courses(courses)
        
        print(f"🗑️ Course deleted: {course_to_delete['courseName']}")
        return {"message": "Course deleted successfully"}
        
    except Exception as e:
        print(f"❌ Error deleting course: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete course: {str(e)}")

# Error handlers
@app.exception_handler(500)
async def internal_server_error_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"}
    )

if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting EduPal API Server...")
    print("📚 Available at: http://localhost:8000")
    print("📖 API Docs: http://localhost:8000/docs")
    
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000,
        reload=True  # Auto-reload during development
    )