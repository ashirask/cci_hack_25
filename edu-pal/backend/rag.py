# Reads PDFs and extracts text
# Combines teacher's prompt + PDF content + student question
# Calls Groq API
# Returns educated, rule-following answers

import os
import json
from groq import Groq
import PyPDF2
import re
from typing import List, Dict, Optional
import tiktoken
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SimpleRAG:
    def __init__(self):
        # Initialize Groq client instead of OpenAI
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.max_context_tokens = 4000  # Reserve context window for conversation
        
        # Ensure documents directory exists
        self.documents_dir = "backend/data/documents"
        os.makedirs(self.documents_dir, exist_ok=True)
        
        print("🤖 RAG System Initialized with Groq")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text for context management"""
        return len(self.encoding.encode(text))

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file with error handling"""
        try:
            full_path = os.path.join(self.documents_dir, pdf_path)
            if not os.path.exists(full_path):
                print(f"⚠️ PDF not found: {pdf_path}")
                return f"Document {pdf_path} not available."
            
            with open(full_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                
                for page_num, page in enumerate(reader.pages):
                    page_text = page.extract_text()
                    if page_text.strip():
                        text += f"--- Page {page_num + 1} ---\n{page_text}\n\n"
                
                if not text.strip():
                    return f"PDF {pdf_path} appears to be empty or contains no extractable text."
                
                print(f"📄 Extracted {len(text)} characters from {pdf_path}")
                return text
                
        except Exception as e:
            print(f"❌ Error extracting text from {pdf_path}: {e}")
            return f"Error reading {pdf_path}: {str(e)}"

    def extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            full_path = os.path.join(self.documents_dir, file_path)
            with open(full_path, 'r', encoding='utf-8') as file:
                content = file.read()
                print(f"📄 Read {len(content)} characters from {file_path}")
                return content
        except Exception as e:
            print(f"❌ Error reading text file {file_path}: {e}")
            return f"Error reading {file_path}: {str(e)}"

    def smart_context_selection(self, documents: List[str], question: str, max_tokens: int = 3000) -> str:
        """
        Smartly select relevant context from documents based on question
        to stay within token limits
        """
        all_content = ""
        
        for doc_path in documents:
            if doc_path.endswith('.pdf'):
                content = self.extract_text_from_pdf(doc_path)
            elif doc_path.endswith('.txt'):
                content = self.extract_text_from_txt(doc_path)
            else:
                content = f"Unsupported file type: {doc_path}"
            
            all_content += f"\n\n--- Document: {os.path.basename(doc_path)} ---\n{content}"
        
        # If content is too long, use a simple relevance-based selection
        if self.count_tokens(all_content) > max_tokens:
            print(f"📚 Content too large ({self.count_tokens(all_content)} tokens), selecting relevant portions...")
            
            # Simple relevance: look for sections containing question keywords
            question_keywords = set(question.lower().split())
            lines = all_content.split('\n')
            relevant_lines = []
            
            for line in lines:
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in question_keywords if len(keyword) > 3):
                    relevant_lines.append(line)
            
            selected_content = '\n'.join(relevant_lines[:100])  # Limit lines
            if self.count_tokens(selected_content) < 500:  # If not enough relevant content
                # Fallback: take beginning of each document
                selected_content = ""
                for doc_path in documents:
                    if doc_path.endswith('.pdf'):
                        content = self.extract_text_from_pdf(doc_path)
                    else:
                        content = self.extract_text_from_txt(doc_path)
                    selected_content += content[:2000] + "\n\n"  # First 2000 chars per doc
        else:
            selected_content = all_content
        
        final_tokens = self.count_tokens(selected_content)
        print(f"🎯 Selected context: {final_tokens} tokens")
        return selected_content

    def build_system_prompt(self, course: Dict, context: str) -> str:
        """Build the system prompt with teacher's instructions and context"""
        
        base_instructions = f"""
You are an AI teaching assistant for the course: "{course['courseName']}"

TEACHER'S SPECIFIC INSTRUCTIONS (MUST FOLLOW):
{course['teacherPrompt']}

COURSE MATERIALS CONTEXT:
{context if context else "No specific course materials provided. Use general knowledge about the subject."}

CORE RULES (STRICTLY ENFORCED):
1. NEVER provide direct answers to specific quiz, test, or assignment questions
2. ALWAYS guide students to understand concepts and solve problems themselves
3. Use the course materials as your primary knowledge source when available
4. If materials don't cover the topic, acknowledge this and provide general guidance
5. Be patient, encouraging, and educational in your tone
6. If a student asks for direct answers, explain why understanding the concept is more valuable

RESPONSE GUIDELINES:
- Break down complex concepts into understandable parts
- Ask guiding questions to help students think critically
- Provide examples and analogies when helpful
- Encourage learning and curiosity
- If you're unsure, admit it and suggest where they might find the information
"""

        return base_instructions.strip()

    def process_question(self, course: Dict, question: str) -> str:
        """
        Main method to process a student's question using RAG
        """
        try:
            print(f"🧠 Processing question for course: {course['courseName']}")
            print(f"   Question: {question}")
            print(f"   Teacher Instructions: {course['teacherPrompt'][:100]}...")
            print(f"   Available documents: {len(course.get('documents', []))}")

            # Extract context from course documents
            context = ""
            if course.get('documents'):
                context = self.smart_context_selection(course['documents'], question)
            else:
                print("ℹ️ No documents available for this course, using general knowledge")

            # Build the system prompt with teacher's rules
            system_prompt = self.build_system_prompt(course, context)
            
            # Call Groq API instead of OpenAI
            response = self.client.chat.completions.create(
                model="llama3-8b-8192",  # Using Llama 3 8B - fast and free
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user", 
                        "content": question
                    }
                ],
                max_tokens=500,
                temperature=0.7,
                top_p=0.9
            )
            
            answer = response.choices[0].message.content
            print(f"✅ Generated answer: {answer[:100]}...")
            
            return answer

        except Exception as e:
            error_msg = f"I apologize, but I'm having trouble processing your question right now. Please try again in a moment. Error: {str(e)}"
            print(f"❌ RAG Error: {e}")
            return error_msg

    def test_rag_system(self, course_data: Dict = None):
        """Test method to verify RAG system is working"""
        if not course_data:
            course_data = {
                "id": "test-course",
                "courseName": "Biology 101 - Test",
                "teacherPrompt": "Explain concepts clearly but never give direct answers to test questions. Always guide students to discover answers themselves.",
                "documents": []
            }
        
        test_questions = [
            "What is photosynthesis?",
            "Can you give me the answer to question 3 on the quiz?",
            "How do cells produce energy?"
        ]
        
        print("🧪 Testing RAG System...")
        for question in test_questions:
            print(f"\n--- Testing: '{question}' ---")
            answer = self.process_question(course_data, question)
            print(f"Answer: {answer}\n")
        
        return "RAG system test completed"

# Demo data creation functions
def create_sample_biology_syllabus():
    """Create a sample biology syllabus for demo purposes"""
    syllabus_content = """
BIOLOGY 101 - INTRODUCTION TO BIOLOGY
Instructor: Dr. Jane Smith
Semester: Fall 2024

COURSE DESCRIPTION:
This course introduces fundamental concepts in biology, including cell structure, genetics, evolution, and ecology. Students will develop scientific reasoning skills and understand the principles governing living organisms.

LEARNING OBJECTIVES:
1. Understand cell structure and function
2. Explain genetic inheritance and DNA replication
3. Describe evolutionary processes and natural selection
4. Analyze ecosystem dynamics and energy flow

TOPICS COVERED:
- Cell Biology: Prokaryotic vs eukaryotic cells, organelles, cellular respiration
- Genetics: Mendelian inheritance, DNA structure, protein synthesis
- Evolution: Natural selection, adaptation, speciation
- Ecology: Food webs, nutrient cycles, biodiversity

ASSESSMENTS:
- Weekly Quizzes: 20%
- Lab Reports: 30%
- Midterm Exam: 25%
- Final Exam: 25%

GRADING POLICY:
Grades are based on demonstrated understanding of concepts rather than memorization. Critical thinking and application of knowledge are emphasized.

ACADEMIC INTEGRITY:
All work must be original. Collaboration is encouraged but students must submit their own work.
"""
    
    os.makedirs("backend/data/documents", exist_ok=True)
    syllabus_path = "backend/data/documents/sample_biology_syllabus.txt"
    
    with open(syllabus_path, 'w', encoding='utf-8') as f:
        f.write(syllabus_content)
    
    print(f"✅ Created sample syllabus: {syllabus_path}")
    return "sample_biology_syllabus.txt"

def create_sample_lecture_notes():
    """Create sample lecture notes for demo"""
    lecture_content = """
LECTURE 3: PHOTOSYNTHESIS

Key Concepts:
- Photosynthesis converts light energy to chemical energy
- Occurs in chloroplasts of plant cells
- Overall equation: 6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂

Two Main Stages:
1. Light-Dependent Reactions:
   - Location: Thylakoid membranes
   - Input: Light, water
   - Output: ATP, NADPH, oxygen
   - Photosystems II and I capture light energy

2. Light-Independent Reactions (Calvin Cycle):
   - Location: Stroma
   - Input: CO₂, ATP, NADPH
   - Output: Glucose
   - Carbon fixation using RuBisCO enzyme

Factors Affecting Photosynthesis:
- Light intensity
- CO₂ concentration
- Temperature
- Water availability

Importance:
- Primary energy source for most ecosystems
- Oxygen production for aerobic organisms
- Carbon dioxide consumption
"""
    
    lecture_path = "backend/data/documents/sample_lecture_notes.txt"
    with open(lecture_path, 'w', encoding='utf-8') as f:
        f.write(lecture_content)
    
    print(f"✅ Created sample lecture notes: {lecture_path}")
    return "sample_lecture_notes.txt"

# Initialize RAG system
rag_system = SimpleRAG()

if __name__ == "__main__":
    # Test the RAG system
    print("🚀 Testing EduPal RAG System with Groq...")
    
    # Create demo documents
    syllabus_file = create_sample_biology_syllabus()
    lecture_file = create_sample_lecture_notes()
    
    # Test with a sample course
    test_course = {
        "id": "demo-course-001",
        "courseName": "Biology 101 - Demo",
        "teacherPrompt": "You are a helpful biology tutor. Explain concepts clearly but never give direct answers to specific test questions. Guide students to understand the underlying principles and think critically. If asked for quiz answers, explain the relevant concepts instead.",
        "documents": [syllabus_file, lecture_file]
    }
    
    # Run tests
    rag_system.test_rag_system(test_course)