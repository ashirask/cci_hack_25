import streamlit as st
import requests

# Your backend URL
BACKEND_URL = "http://localhost:8000"

def main():
    st.title("🎓 EduPal - AI Study Partner")
    
    # Role selection
    role = st.radio("Select your role:", ["Teacher", "Student"])
    
    if role == "Teacher":
        teacher_view()
    else:
        student_view()

def teacher_view():
    st.header("Teacher Dashboard")
    
    # Create course form - moved to top so it works better
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
                        st.balloons()
                    else:
                        st.error(f"Failed to create course: {response.text}")
                except ConnectionError:
                    st.error("Cannot connect to backend server!")
    
    # Get existing courses for file upload (show after creation form)
    try:
        courses = requests.get(f"{BACKEND_URL}/courses").json()
        
        if courses:
            st.subheader("Upload Course Materials")
            course_options = {c['courseName']: c['id'] for c in courses}
            selected_course = st.selectbox("Select course to upload materials:", list(course_options.keys()))
            course_id = course_options[selected_course]
            
            uploaded_file = st.file_uploader("Upload PDF or text file", type=['pdf', 'txt'])
            if uploaded_file and st.button("Upload File"):
                files = {'file': (uploaded_file.name, uploaded_file.getvalue())}
                response = requests.post(f"{BACKEND_URL}/upload/{course_id}", files=files)
                if response.status_code == 200:
                    st.success("File uploaded successfully!")
                else:
                    st.error("Upload failed")
        
        # Show existing courses
        st.subheader("Existing Courses")
        for course in courses:
            st.write(f"**{course['courseName']}** (ID: {course['id'][:8]}...)")
            
    except ConnectionError:
        st.error("Cannot connect to backend. Make sure it's running on localhost:8000")

def student_view():
    st.header("Student Dashboard")
    
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
            
            # Initialize chat history for this course
            if course_id not in st.session_state.chat_history:
                st.session_state.chat_history[course_id] = []
            
            st.subheader("Chat with AI Tutor")
            
            # Display chat history
            chat_container = st.container()
            with chat_container:
                for message in st.session_state.chat_history[course_id]:
                    if message["role"] == "user":
                        st.write(f"**You:** {message['content']}")
                    else:
                        st.write(f"**AI Tutor:** {message['content']}")
                    st.divider()
            
            # Chat input at the bottom
            st.subheader("Ask a question")
            user_message = st.text_input("Type your question here:", key="user_input")
            
            if user_message and st.button("Send"):
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
            st.info("No courses available yet. Ask a teacher to create one!")
            
    except ConnectionError:
        st.error("Cannot connect to backend. Make sure it's running on localhost:8000")

if __name__ == "__main__":
    main()