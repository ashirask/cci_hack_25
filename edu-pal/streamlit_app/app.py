import streamlit as st
import requests
from requests.exceptions import ConnectionError

# Your backend URL
BACKEND_URL = "http://localhost:8000"

def main():
    # Initialize session state for role
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    
    # Welcome page - if no role selected yet
    if st.session_state.user_role is None:
        welcome_page()
    else:
        # Show the appropriate dashboard based on selected role
        if st.session_state.user_role == "student":
            student_view()
        else:
            teacher_view()

def welcome_page():
    st.title("🎓 Welcome to EduPal!")
    st.markdown("### Your AI-Powered Learning Companion")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎒 Student")
        st.markdown("""
        - Access AI tutors for your courses
        - Get personalized learning help
        - Understand concepts, not just answers
        """)
        if st.button("I'm a Student →", use_container_width=True, key="student_btn"):
            st.session_state.user_role = "student"
            st.rerun()
    
    with col2:
        st.subheader("👨‍🏫 Teacher")
        st.markdown("""
        - Create custom AI tutors for your courses
        - Upload course materials
        - Set learning guidelines
        """)
        if st.button("I'm a Teacher →", use_container_width=True, key="teacher_btn"):
            st.session_state.user_role = "teacher"
            st.rerun()
    
    st.markdown("---")
    st.info("💡 **Demo Tip**: Open two browser tabs - one as Teacher, one as Student to see the full experience!")

def teacher_view():
    st.header("👨‍🏫 Teacher Dashboard")
    
    # Back to role selection
    if st.button("← Back to Role Selection"):
        st.session_state.user_role = None
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
                        else:
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
            st.subheader("Your Courses")
            for course in courses:
                with st.expander(f"📚 {course['courseName']}"):
                    st.write(f"**AI Instructions:** {course['teacherPrompt']}")
                    if course.get('documents'):
                        st.write("**Uploaded Files:**")
                        for doc in course['documents']:
                            # Show clean filename
                            original_filename = '_'.join(doc.split('_')[2:])
                            st.write(f"• {original_filename}")
                    else:
                        st.write("No files uploaded yet")
                    
                    # 🆕 SIMPLE DELETE BUTTON INSIDE EXPANDER
                    if st.button("🗑️ Delete Course", key=f"delete_{course['id']}"):
                        try:
                            response = requests.delete(f"{BACKEND_URL}/courses/{course['id']}")
                            if response.status_code == 200:
                                st.success(f"Deleted '{course['courseName']}'!")
                                st.rerun()
                        except:
                            st.error("Delete failed")

        else:
            st.info("No courses created yet. Use the form above to create your first course!")
            
    except ConnectionError:
        st.error("Cannot connect to backend. Make sure it's running on localhost:8000")

def student_view():
    st.header("🎒 Student Dashboard")
    
    # Back to role selection
    if st.button("← Back to Role Selection"):
        st.session_state.user_role = None
        st.rerun()
    
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
            
            # Show course info (but NOT the prompt given by the teacher)
            selected_course = next((c for c in courses if c['id'] == course_id), None)
            if selected_course:
                with st.expander("📖 About This Course"):
                    if selected_course.get('documents'):
                        st.write("**Available Study Materials:**")
                        for doc in selected_course['documents']:
                            # Show just the UUID part (last part after underscore)
                            if '_' in doc:
                                clean_name = doc.split('_')[-1]
                                st.write(f"• {clean_name}")
                            else:
                                st.write(f"• {doc}")
                    else:
                        st.write("No study materials uploaded yet")

            
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