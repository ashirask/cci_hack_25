import streamlit as st
import requests
from requests.exceptions import ConnectionError

# Your backend URL
BACKEND_URL = "http://localhost:8000"

# Teacher password (for demo - in real app, use proper auth)
TEACHER_PASSWORD = "teacher123"

def main():
    st.title("🎓 EduPal - AI Study Partner")
    
    # Check if backend is running
    if not check_backend_connection():
        st.error("🚨 Backend server is not running! Please start the backend first.")
        st.info("**To fix this:** Open a terminal and run: `cd backend && python main.py`")
        return
    
    # Role selection with tabs
    tab1, tab2 = st.tabs(["🎒 Student Portal", "👨‍🏫 Teacher Portal"])
    
    with tab1:
        student_view()
    
    with tab2:
        teacher_view()

def teacher_view():
    st.header("Teacher Portal")
    
    # Teacher authentication
    if "teacher_authenticated" not in st.session_state:
        st.session_state.teacher_authenticated = False
    
    if not st.session_state.teacher_authenticated:
        st.subheader("Teacher Login")
        password = st.text_input("Enter teacher password:", type="password")
        if st.button("Login"):
            if password == TEACHER_PASSWORD:
                st.session_state.teacher_authenticated = True
                st.rerun()
            else:
                st.error("Incorrect password!")
        return
    
    # Logout button
    if st.button("Logout"):
        st.session_state.teacher_authenticated = False
        st.rerun()
    
    try:
        # Create course form
        st.subheader("Create New Course")
        with st.form("create_course", clear_on_submit=True):
            course_name = st.text_input("Course Name *", placeholder="e.g., Algebra 101")
            teacher_prompt = st.text_area("AI Instructions *", 
                                        value="You are a helpful tutor. Explain concepts clearly but never give direct answers to test questions. Guide students to understand the underlying principles.",
                                        placeholder="How should the AI tutor behave?")
            submitted = st.form_submit_button("Create Course")
            
            if submitted:
                if not course_name.strip():
                    st.error("Course name is required!")
                else:
                    try:
                        # Call your existing backend
                        response = requests.post(
                            f"{BACKEND_URL}/courses",
                            json={
                                "courseName": course_name.strip(),
                                "teacherPrompt": teacher_prompt.strip()
                            }
                        )
                        if response.status_code == 200:
                            st.success("✅ Course created successfully!")
                            # Don't show error even if it appears - the course actually gets created
                        else:
                            # Course might still be created despite error message
                            st.info("Course may have been created. Check the list below.")
                    except ConnectionError:
                        st.error("Cannot connect to backend server!")
        
        # Get existing courses
        courses = requests.get(f"{BACKEND_URL}/courses").json()
        
        if courses:
            st.subheader("Upload Course Materials")
            course_options = {c['courseName']: c['id'] for c in courses}
            selected_course = st.selectbox("Select course to upload materials:", list(course_options.keys()))
            course_id = course_options[selected_course]
            
            # Multiple file upload
            uploaded_files = st.file_uploader(
                "Upload PDF files (you can select multiple)", 
                type=['pdf', 'txt'], 
                accept_multiple_files=True
            )
            
            if uploaded_files and st.button("Upload Files"):
                success_count = 0
                for uploaded_file in uploaded_files:
                    try:
                        files = {'file': (uploaded_file.name, uploaded_file.getvalue())}
                        response = requests.post(f"{BACKEND_URL}/upload/{course_id}", files=files)
                        if response.status_code == 200:
                            success_count += 1
                    except:
                        continue
                
                if success_count > 0:
                    st.success(f"✅ {success_count} file(s) uploaded successfully!")
                else:
                    st.error("Upload failed for all files")
            
            # Show existing courses and their documents
            st.subheader("Existing Courses & Materials")
            for course in courses:
                with st.expander(f"📚 {course['courseName']}"):
                    st.write(f"**AI Instructions:** {course['teacherPrompt']}")
                    if course.get('documents'):
                        st.write("**Uploaded Files:**")
                        for doc in course['documents']:
                            st.write(f"• {doc.split('_')[-1]}")  # Show just filename
                    else:
                        st.write("No files uploaded yet")
        else:
            st.info("No courses created yet. Use the form above to create your first course!")
            
    except ConnectionError:
        st.error("Cannot connect to backend. Make sure it's running on localhost:8000")

def student_view():
    st.header("Student Portal")
    
    # Initialize chat history in session state
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = {}
    
    try:
        # Get available courses from backend
        courses = requests.get(f"{BACKEND_URL}/courses").json()
        
        if courses:
            course_options = {f"{c['courseName']}": c['id'] for c in courses}
            selected_course_name = st.selectbox("Select a course:", list(course_options.keys()))
            course_id = course_options[selected_course_name]
            
            # Show course info
            selected_course = next((c for c in courses if c['id'] == course_id), None)
            if selected_course:
                with st.expander("📖 Course Information"):
                    st.write(f"**AI Tutor Instructions:** {selected_course['teacherPrompt']}")
                    if selected_course.get('documents'):
                        st.write("**Available Materials:**")
                        for doc in selected_course['documents']:
                            st.write(f"• {doc.split('_')[-1]}")
            
            # Initialize chat history for this course
            if course_id not in st.session_state.chat_history:
                st.session_state.chat_history[course_id] = []
            
            st.subheader("💬 Chat with AI Tutor")
            
            # Display chat history
            chat_container = st.container()
            with chat_container:
                for message in st.session_state.chat_history[course_id]:
                    if message["role"] == "user":
                        st.markdown(f"**You:** {message['content']}")
                    else:
                        st.markdown(f"**AI Tutor:** {message['content']}")
                    st.divider()
            
            # Chat input
            col1, col2 = st.columns([4, 1])
            with col1:
                user_message = st.text_input("Type your question:", placeholder="Ask about course content...", label_visibility="collapsed")
            with col2:
                send_button = st.button("Send", use_container_width=True)
            
            if user_message and send_button:
                # Add user message to history
                st.session_state.chat_history[course_id].append({
                    "role": "user", 
                    "content": user_message
                })
                
                with st.spinner("🤔 AI is thinking..."):
                    try:
                        response = requests.post(
                            f"{BACKEND_URL}/chat",
                            json={
                                "courseId": course_id,
                                "message": user_message
                            }
                        )
                        if response.status_code == 200:
                            answer = response.json()["answer"]
                            # Add AI response to history
                            st.session_state.chat_history[course_id].append({
                                "role": "assistant",
                                "content": answer
                            })
                            # Rerun to update the display
                            st.rerun()
                        else:
                            st.error("Failed to get response from AI")
                    except ConnectionError:
                        st.error("Cannot connect to backend server!")
            
            # Clear chat button
            if st.session_state.chat_history[course_id]:
                if st.button("Clear Chat History"):
                    st.session_state.chat_history[course_id] = []
                    st.rerun()
                    
        else:
            st.info("📚 No courses available yet. Teachers can create courses in the Teacher Portal.")
            
    except ConnectionError:
        st.error("Cannot connect to backend. Make sure it's running on localhost:8000")

def check_backend_connection():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/")
        return True
    except ConnectionError:
        return False

if __name__ == "__main__":
    main()