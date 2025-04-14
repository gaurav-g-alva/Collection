# app.py
import streamlit as st
import pandas as pd
from datetime import datetime
import auth
import models
import generator
import utils

# Page configuration
st.set_page_config(page_title="TimeTable Generator", layout="wide")

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'role' not in st.session_state:
    st.session_state.role = None

def login_page():
    st.title("TimeTable Generator - Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = auth.authenticate_user(email, password)
        if user:
            st.session_state.user = user
            st.session_state.role = user.role
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

def admin_dashboard():
    st.title("Admin Dashboard")
    tab1, tab2, tab3 = st.tabs(["Users", "Courses", "Timetable Generation"])
    
    with tab1:
        st.subheader("User Management")
        users_df = pd.DataFrame(models.get_all_users())
        st.dataframe(users_df)
        
    with tab2:
        st.subheader("Course Management")
        courses_df = pd.DataFrame(models.get_all_courses())
        st.dataframe(courses_df)
        
    with tab3:
        st.subheader("Generate Timetable")
        semester = st.selectbox("Select Semester", range(1, 9))
        if st.button("Generate Timetable"):
            with st.spinner("Generating timetable..."):
                timetable = generator.generate_timetable(semester)
                if timetable:
                    st.success("Timetable generated successfully!")
                    st.download_button(
                        "Download PDF",
                        utils.generate_pdf(timetable),
                        file_name=f"timetable_sem{semester}.pdf",
                        mime="application/pdf"
                    )

def faculty_dashboard():
    st.title("Faculty Dashboard")
    faculty_id = st.session_state.user.id
    tab1, tab2 = st.tabs(["My Schedule", "Availability"])
    
    with tab1:
        schedule = models.get_faculty_schedule(faculty_id)
        st.dataframe(pd.DataFrame(schedule))
        
    with tab2:
        st.subheader("Update Availability")
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        availability = {}
        for day in days:
            st.write(f"### {day}")
            availability[day] = {
                "start": st.time_input(f"Start time - {day}", key=f"start_{day}"),
                "end": st.time_input(f"End time - {day}", key=f"end_{day}")
            }
        if st.button("Update"):
            models.update_faculty_availability(faculty_id, availability)
            st.success("Availability updated successfully!")

def student_dashboard():
    st.title("Student Dashboard")
    student_id = st.session_state.user.id
    semester = models.get_student_semester(student_id)
    
    timetable = models.get_student_timetable(semester)
    if timetable:
        st.dataframe(pd.DataFrame(timetable))
        st.download_button(
            "Download PDF",
            utils.generate_pdf(timetable),
            file_name=f"timetable_sem{semester}.pdf",
            mime="application/pdf"
        )
    else:
        st.info("No timetable available for your semester yet.")

def main():
    if not st.session_state.user:
        login_page()
    else:
        st.sidebar.button("Logout", on_click=lambda: st.session_state.clear())
        
        if st.session_state.role == "admin":
            admin_dashboard()
        elif st.session_state.role == "faculty":
            faculty_dashboard()
        else:
            student_dashboard()

if __name__ == "__main__":
    main()
