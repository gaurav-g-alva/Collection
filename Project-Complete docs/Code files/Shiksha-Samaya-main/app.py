# app.py
import streamlit as st
import pandas as pd
from collections import defaultdict
import time
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

from database import (
    init_db, add_user, get_user, check_password,
    add_department, get_departments, update_department, delete_department,
    add_semester, get_semesters, delete_semester,
    add_faculty, get_faculty, update_faculty, delete_faculty,
    add_course, get_courses, get_theory_courses, get_lab_courses, update_course, delete_course,
    add_theory_mapping, get_theory_mappings, delete_theory_mapping,
    add_lab_mapping, get_lab_mappings, delete_lab_mapping,
    add_faculty_preference, get_faculty_preferences, get_faculty_preferences_by_faculty_id, delete_faculty_preference,
    load_all_data, get_classes_to_schedule,
    add_saved_timetable, get_saved_timetables, load_saved_timetable_data, delete_saved_timetable,
    delete_all_user_data, create_timetables_table,create_saved_timetables_table,
)
from genetic_algorithm import GeneticAlgorithm, TimetableChromosome, PERIODS_PER_DAY

# Initialize DB (create tables if needed)
init_db()
create_timetables_table()
create_saved_timetables_table()

# -----------------------------
# Utilities and PDF helpers
# -----------------------------
def confirm_action(message, key_prefix):
    st.markdown(f"**Confirmation needed:** {message}", unsafe_allow_html=True)
    col_yes, col_no = st.columns([1, 4])
    with col_yes:
        if st.button("Yes, proceed", key=f"{key_prefix}_yes", type="primary"):
            return True
    with col_no:
        if st.button("No, cancel", key=f"{key_prefix}_no"):
            st.info("Action cancelled.")
            return False
    return None

# ---------- PDF helpers ----------
def build_pdf_from_timetable(grids_by_section: dict, title: str = "Automatic Timetable") -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24
    )
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(title, styles["Title"]))
    story.append(Spacer(1, 12))

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    for section_name, day_map in grids_by_section.items():
        max_slots = max((len(v) for v in day_map.values()), default=0)
        header = ["Day"] + [f"Slot {i+1}" for i in range(max_slots)]
        data = [header]
        for day in day_order:
            if day not in day_map:
                continue
            row = [day] + day_map[day] + [""] * (max_slots - len(day_map[day]))
            data.append(row)

        story.append(Paragraph(section_name, styles["Heading2"]))
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (1,1), (-1,-1), "CENTER"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.lightyellow]),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))
        story.append(PageBreak())

    doc.build(story)
    return buf.getvalue()

# ---------- grids for whole + per-faculty ----------
def to_shareable_grids(chromosome: TimetableChromosome, all_data) -> dict:
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    slots_per_day = PERIODS_PER_DAY
    by_sem = defaultdict(list)
    for sc in chromosome.scheduled_classes:
        by_sem[sc.semester_id].append(sc)
    grids = {}
    for sem_id, entries in by_sem.items():
        sem_obj = all_data['semesters_by_id'].get(sem_id)
        sem_name = f"Semester {getattr(sem_obj, 'semester_number', sem_id)}"
        grids[sem_name] = {d: [""] * slots_per_day for d in day_order}
        for sc in entries:
            course_code = sc.course_obj.code if sc.course_obj else ""
            fac_names = ", ".join([f.name for f in sc.faculty_objs]) if sc.faculty_objs else ""
            cell = f"{course_code}\n({fac_names})" if fac_names else course_code
            for p in range(sc.start_period, sc.end_period + 1):
                if 1 <= p <= slots_per_day and sc.day in grids[sem_name]:
                    idx = p - 1
                    grids[sem_name][sc.day][idx] = (grids[sem_name][sc.day][idx] + ("\n—\n" if grids[sem_name][sc.day][idx] else "") + cell)
    return grids

def build_faculty_grids(chromosome: TimetableChromosome, all_data):
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    slots_per_day = PERIODS_PER_DAY
    out = {}
    def ensure(fid):
        if fid not in out:
            name = all_data['faculty_by_id'][fid].name if fid in all_data['faculty_by_id'] else f"Faculty {fid}"
            out[fid] = (name, {d: [""] * slots_per_day for d in day_order})
    for sc in chromosome.scheduled_classes:
        sem_obj = sc.semester_obj or all_data['semesters_by_id'].get(sc.semester_id)
        sem_num = getattr(sem_obj, 'semester_number', sc.semester_id)
        course_code = sc.course_obj.code if sc.course_obj else ""
        cell = f"{course_code} (Sem {sem_num})"
        fac_ids = [f.id for f in sc.faculty_objs] if getattr(sc, "faculty_objs", None) else (sc.faculty_ids or [])
        for fid in fac_ids:
            ensure(fid)
            _, grid = out[fid]
            for p in range(sc.start_period, sc.end_period + 1):
                if 1 <= p <= slots_per_day and sc.day in grid:
                    idx = p - 1
                    grid[sc.day][idx] = (grid[sc.day][idx] + ("\n—\n" if grid[sc.day][idx] else "") + cell)
    return out

# -----------------------------
# Page Navigation + Pages
# -----------------------------
def set_page(page_name):
    st.session_state['current_page'] = page_name

def show_login_register_page():
    st.image("assets/home.png", use_container_width=False)
    st.title("Welcome to Timetable Generator")

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        st.subheader("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            user = get_user(username)
            if user and check_password(password, user['password_hash']):
                st.session_state['logged_in'] = True
                st.session_state['username'] = username
                st.session_state['user_id'] = user['id']
                st.success("Logged in successfully!")
                set_page("welcome")
                st.rerun()
            else:
                st.error("Invalid username or password")

    with tab_register:
        st.subheader("Register")
        new_username = st.text_input("New Username", key="register_username")
        new_password = st.text_input("New Password", type="password", key="register_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm_password")
        if st.button("Register"):
            if new_password and new_username:
                if new_password == confirm_password:
                    if add_user(new_username, new_password):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Username already exists or registration failed.")
                else:
                    st.error("Passwords do not match.")
            else:
                st.warning("Please enter a username and password.")

def show_welcome_page():
    st.image("assets/home.png", use_container_width=True)
    st.title(f"Welcome, {st.session_state.get('username', 'User')}!")
    st.markdown(
        """
        ### About This Application
        This **Web-Based Automatic Timetable Scheduler** helps colleges efficiently generate clash-free timetables.  
        
        🔹 Manage Departments, Faculty, Courses, and Semesters  
        🔹 Map Courses with Faculty & Preferences  
        🔹 Generate Optimized Timetables using a **Genetic Algorithm**  
        🔹 Analyze Faculty Workload & Class Distribution  
        🔹 Save and Reuse Timetables Anytime  
        """
    )
    st.success("**>>** Use the sidebar to navigate through different sections.")
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; font-size: 30px;'>
            Developed by <b>Gaurav G Alva</b>, <b>Prapthi J P</b>, <b>Supreetha N S</b>, <b>Harshit M Naik</b>
        </div>
        """,
        unsafe_allow_html=True
    )

def manage_departments_page():
    st.image("assets/deptandsem.png", use_container_width=True)
    st.header("Department Management")
    user_id = st.session_state['user_id']

    with st.expander("Add New Department"):
        new_dept_name = st.text_input("Department Name")
        if st.button("Add Department"):
            if new_dept_name:
                if add_department(user_id, new_dept_name):
                    st.success(f"Department '{new_dept_name}' added successfully!")
                    st.rerun()
                else:
                    st.error(f"Department '{new_dept_name}' already exists or failed to add.")
            else:
                st.warning("Please enter a department name.")

    st.subheader("Current Departments")
    departments = get_departments(user_id)
    if departments:
        dept_data = [dict(row) for row in departments]
        df = pd.DataFrame(dept_data)
        st.dataframe(df.set_index('id'))

        st.subheader("Edit / Delete Department")
        dept_names = {dept['id']: dept['name'] for dept in departments}
        selected_dept_id = st.selectbox(
            "Select Department to Edit/Delete",
            options=list(dept_names.keys()),
            format_func=lambda x: dept_names[x],
            key="edit_delete_dept_select"
        )

        if selected_dept_id:
            current_dept_name = dept_names[selected_dept_id]
            col1, col2 = st.columns(2)
            with col1:
                new_name_edit = st.text_input("New Name", value=current_dept_name, key="edit_dept_name")
                if st.button("Update Department"):
                    if new_name_edit and update_department(user_id, selected_dept_id, new_name_edit):
                        st.success(f"Department updated to '{new_name_edit}'")
                        st.rerun()
                    else:
                        st.error("Failed to update department. Name might already exist.")
            with col2:
                if st.button("Delete Department", type="secondary", key="init_delete_dept_button"):
                    st.session_state[f"confirm_delete_dept_{selected_dept_id}"] = True

            if st.session_state.get(f"confirm_delete_dept_{selected_dept_id}", False):
                confirmed = confirm_action(
                    f"Are you sure you want to delete '{current_dept_name}'? This cannot be undone and may affect associated data.",
                    f"confirm_del_dept_{selected_dept_id}"
                )
                if confirmed is not None:
                    if confirmed:
                        if delete_department(user_id, selected_dept_id):
                            st.success(f"Department '{current_dept_name}' deleted.")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete department '{current_dept_name}'. It might have associated records or delete failed.")
                    st.session_state[f"confirm_delete_dept_{selected_dept_id}"] = False
    else:
        st.info("No departments added yet.")

    st.subheader("Current Semesters")
    semesters = get_semesters(user_id)
    with st.expander("Add New Semester"):
        st.write("Add current as well as upcoming semesters (e.g., 3, 4, 5, 6, etc.).")
        new_sem_num = st.number_input("Semester Number", min_value=1, step=1, key="new_sem_num")
        if st.button("Add Semester"):
            if new_sem_num:
                if add_semester(user_id, new_sem_num):
                    st.success(f"Semester {new_sem_num} added!")
                    st.rerun()
                else:
                    st.error(f"Semester {new_sem_num} already exists or failed to add.")
            else:
                st.warning("Please enter a semester number.")

    if semesters:
        sem_data = [dict(row) for row in semesters]
        df_sem = pd.DataFrame(sem_data)
        st.dataframe(df_sem.set_index('id'))

        st.subheader("Delete Semester")
        sem_options = {sem['id']: sem['semester_number'] for sem in semesters}
        selected_sem_id = st.selectbox(
            "Select Semester to Delete",
            options=list(sem_options.keys()),
            format_func=lambda x: f"Semester {sem_options[x]}",
            key="delete_sem_select"
        )
        if selected_sem_id:
            current_sem_num = sem_options[selected_sem_id]
            if st.button("Delete Selected Semester", type="secondary", key="init_delete_sem_button"):
                st.session_state[f"confirm_delete_sem_{selected_sem_id}"] = True

            if st.session_state.get(f"confirm_delete_sem_{selected_sem_id}", False):
                confirmed = confirm_action(
                    f"Are you sure you want to delete Semester {current_sem_num}? This cannot be undone.",
                    f"confirm_del_sem_{selected_sem_id}"
                )
                if confirmed is not None:
                    if confirmed:
                        if delete_semester(user_id, selected_sem_id):
                            st.success(f"Semester {current_sem_num} deleted.")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete Semester {current_sem_num}. It might have associated mappings.")
                    st.session_state[f"confirm_delete_sem_{selected_sem_id}"] = False
    else:
        st.info("No semesters added yet.")

def manage_faculty_page():
    st.image("assets/facmanagement.png", use_container_width=True)
    st.header("Faculty Management")
    user_id = st.session_state['user_id']

    departments = get_departments(user_id)
    dept_options = {dept['id']: dept['name'] for dept in departments}

    if not departments:
        st.warning("Please add some departments first in 'Department Management' to add faculty.")
        return

    with st.expander("Add New Faculty"):
        faculty_name = st.text_input("Faculty Name")
        faculty_emp_id = st.text_input("Employee ID")
        selected_dept_id = st.selectbox(
            "Department",
            options=list(dept_options.keys()),
            format_func=lambda x: dept_options[x],
            key="add_faculty_dept_select"
        )

        if st.button("Add Faculty"):
            if faculty_name and faculty_emp_id and selected_dept_id:
                if add_faculty(user_id, faculty_name, faculty_emp_id, selected_dept_id):
                    st.success(f"Faculty '{faculty_name}' added successfully!")
                    st.rerun()
                else:
                    st.error(f"Faculty with Employee ID '{faculty_emp_id}' already exists or failed to add.")
            else:
                st.warning("Please fill all fields.")

    st.subheader("Current Faculty")
    faculty = get_faculty(user_id)
    if faculty:
        faculty_data = [dict(row) for row in faculty]
        df = pd.DataFrame(faculty_data)
        st.dataframe(df.set_index('id'))

        st.subheader("Edit / Delete Faculty")
        faculty_options = {f['id']: f['name'] for f in faculty}
        selected_faculty_id = st.selectbox(
            "Select Faculty to Edit/Delete",
            options=list(faculty_options.keys()),
            format_func=lambda x: faculty_options[x],
            key="edit_delete_faculty_select"
        )

        if selected_faculty_id:
            current_faculty = next((f for f in faculty if f['id'] == selected_faculty_id), None)
            if current_faculty:
                col1, col2 = st.columns(2)
                with col1:
                    new_name = st.text_input("New Name", value=current_faculty['name'], key="edit_faculty_name")
                    new_emp_id = st.text_input("New Employee ID", value=current_faculty['emp_id'], key="edit_faculty_emp_id")
                    current_dept_id = current_faculty['department_id']
                    new_dept_id = st.selectbox(
                        "New Department",
                        options=list(dept_options.keys()),
                        index=list(dept_options.keys()).index(current_dept_id) if current_dept_id in dept_options else 0,
                        format_func=lambda x: dept_options[x],
                        key="edit_faculty_dept_select"
                    )

                    if st.button("Update Faculty"):
                        if new_name and new_emp_id and new_dept_id:
                            if update_faculty(user_id, selected_faculty_id, new_name, new_emp_id, new_dept_id):
                                st.success(f"Faculty '{current_faculty['name']}' updated.")
                                st.rerun()
                            else:
                                st.error("Failed to update faculty. Employee ID might already exist.")
                        else:
                            st.warning("Please fill all fields for update.")
                with col2:
                    if st.button("Delete Faculty", type="secondary", key="init_delete_faculty_button"):
                        st.session_state[f"confirm_delete_faculty_{selected_faculty_id}"] = True

                    if st.session_state.get(f"confirm_delete_faculty_{selected_faculty_id}", False):
                        confirmed = confirm_action(
                            f"Are you sure you want to delete '{current_faculty['name']}'? This cannot be undone and may affect associated mappings.",
                            f"confirm_del_faculty_{selected_faculty_id}"
                        )
                        if confirmed is not None:
                            if confirmed:
                                if delete_faculty(user_id, selected_faculty_id):
                                    st.success(f"Faculty '{current_faculty['name']}' deleted.")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to delete faculty '{current_faculty['name']}'. It might be assigned to a course.")
                            st.session_state[f"confirm_delete_faculty_{selected_faculty_id}"] = False
    else:
        st.info("No faculty added yet.")

def manage_courses_page():
    st.image("assets/coursemanagement.png", use_container_width=True)
    st.header("Course Management")
    user_id = st.session_state['user_id']

    with st.expander("Add New Course"):
        course_code = st.text_input("Course Code (e.g., CS101)")
        course_name  = st.text_input("Course Name (e.g., Data Structures)")
        course_type = st.radio("Course Type", ('theory', 'lab'))

        hours_per_week = st.number_input("Hours per week (Theory)", min_value=1, step=1) if course_type == 'theory' else 2
        if course_type == 'lab':
            st.write("Lab courses are fixed at 2 hours continuously.")
        
        if st.button("Add Course"):
            if course_code and course_name and hours_per_week:
                if add_course(user_id, course_code.upper(), course_name, int(hours_per_week), course_type):
                    st.success(f"Course '{course_name}' ({course_code.upper()}) added successfully!")
                    st.rerun()
                else:
                    st.error(f"Course with code '{course_code.upper()}' already exists or failed to add.")
            else:
                st.warning("Please fill all fields.")

    st.subheader("Current Courses")
    courses = get_courses(user_id)
    if courses:
        course_data = [dict(row) for row in courses]
        df = pd.DataFrame(course_data)
        st.dataframe(df.set_index('id'))

        st.subheader("Edit / Delete Course")
        course_options = {c['id']: f"{c['code']} - {c['name']} ({c['type'].capitalize()})" for c in courses}
        selected_course_id = st.selectbox(
            "Select Course to Edit/Delete",
            options=list(course_options.keys()),
            format_func=lambda x: course_options[x],
            key="edit_delete_course_select"
        )

        if selected_course_id:
            current_course = next((c for c in courses if c['id'] == selected_course_id), None)
            if current_course:
                col1, col2 = st.columns(2)
                with col1:
                    new_code = st.text_input("New Code", value=current_course['code'], key="edit_course_code")
                    new_name = st.text_input("New Name", value=current_course['name'], key="edit_course_name")
                    new_type = st.radio("New Type", ('theory', 'lab'), index=0 if current_course['type'] == 'theory' else 1, key="edit_course_type")
                    new_hours = st.number_input("New Hours per week", min_value=1, step=1, value=current_course['hours_per_week'], key="edit_course_hours")

                    if st.button("Update Course"):
                        if new_code and new_name and new_hours and new_type:
                            if new_type == 'lab' and new_hours != 2:
                                st.warning("Lab courses must have 2 hours per week.")
                            else:
                                if update_course(user_id, selected_course_id, new_code.upper(), new_name, int(new_hours), new_type):
                                    st.success(f"Course '{current_course['name']}' updated.")
                                    st.rerun()
                                else:
                                    st.error("Failed to update course. Code might already exist.")
                        else:
                            st.warning("Please fill all fields for update.")
                with col2:
                    if st.button("Delete Course", type="secondary", key="init_delete_course_button"):
                        st.session_state[f"confirm_delete_course_{selected_course_id}"] = True
                    
                    if st.session_state.get(f"confirm_delete_course_{selected_course_id}", False):
                        confirmed = confirm_action(
                            f"Are you sure you want to delete '{current_course['name']}' ({current_course['code']})? This cannot be undone and may affect associated mappings.",
                            f"confirm_del_course_{selected_course_id}"
                        )
                        if confirmed is not None:
                            if confirmed:
                                if delete_course(user_id, selected_course_id):
                                    st.success(f"Course '{current_course['name']}' deleted.")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to delete course '{current_course['name']}'. It might be part of a mapping.")
                            st.session_state[f"confirm_delete_course_{selected_course_id}"] = False
    else:
        st.info("No courses added yet.")

def manage_mapping_page():
    st.image("assets/c-f-smapping.png", use_container_width=True)
    st.header("Course-Faculty-Semester Mapping")
    user_id = st.session_state['user_id']

    semesters = get_semesters(user_id)
    faculty_list = get_faculty(user_id)
    theory_courses = get_theory_courses(user_id)
    lab_courses = get_lab_courses(user_id)

    sem_options = {s['id']: s['semester_number'] for s in semesters}
    faculty_options = {f['id']: f['name'] for f in faculty_list}
    theory_course_options = {c['id']: f"{c['code']} - {c['name']}" for c in theory_courses}
    lab_course_options = {c['id']: f"{c['code']} - {c['name']}" for c in lab_courses}

    if not (semesters and faculty_list):
        st.warning("Please ensure you have added Semesters and Faculty.")
        return
    if not (theory_courses or lab_courses):
        st.warning("Please add some Courses (Theory/Lab) before creating mappings.")
        return

    st.subheader("Theory Course Mapping")
    with st.expander("Add New Theory Mapping"):
        if not theory_courses:
            st.info("No theory courses available to map.")
        else:
            col1, col2, col3 = st.columns(3)
            with col1:
                selected_sem_id_theory = st.selectbox("Semester", options=list(sem_options.keys()), format_func=lambda x: f"Semester {sem_options[x]}", key="map_theory_sem")
            with col2:
                selected_course_id_theory = st.selectbox("Theory Course", options=list(theory_course_options.keys()), format_func=lambda x: theory_course_options[x], key="map_theory_course")
            with col3:
                selected_faculty_id_theory = st.selectbox("Faculty", options=list(faculty_options.keys()), format_func=lambda x: faculty_options[x], key="map_theory_faculty")

            if st.button("Add Theory Mapping"):
                if all([selected_sem_id_theory, selected_course_id_theory, selected_faculty_id_theory]):
                    if add_theory_mapping(user_id, selected_sem_id_theory, selected_course_id_theory, selected_faculty_id_theory):
                        st.success("Theory course mapping added!")
                        st.rerun()
                    else:
                        st.error("Failed to add theory mapping. This course might already be mapped for this semester.")
                else:
                    st.warning("Please select all options for theory mapping.")

    st.markdown("---")
    st.subheader("Lab Course Mapping")
    with st.expander("Add New Lab Mapping"):
        if not lab_courses:
            st.info("No lab courses available to map.")
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                selected_sem_id_lab = st.selectbox("Semester", options=list(sem_options.keys()), format_func=lambda x: f"Semester {sem_options[x]}", key="map_lab_sem")
            with col2:
                selected_course_id_lab = st.selectbox("Lab Course", options=list(lab_course_options.keys()), format_func=lambda x: lab_course_options[x], key="map_lab_course")
            with col3:
                selected_faculty_id_lab1 = st.selectbox("Faculty 1", options=list(faculty_options.keys()), format_func=lambda x: faculty_options[x], key="map_lab_faculty1")
            with col4:
                selected_faculty_id_lab2 = st.selectbox("Faculty 2", options=list(faculty_options.keys()), format_func=lambda x: faculty_options[x], key="map_lab_faculty2")

            if st.button("Add Lab Mapping"):
                if all([selected_sem_id_lab, selected_course_id_lab, selected_faculty_id_lab1, selected_faculty_id_lab2]):
                    if selected_faculty_id_lab1 == selected_faculty_id_lab2:
                        st.error("Faculty 1 and Faculty 2 cannot be the same for a lab course.")
                    else:
                        if add_lab_mapping(user_id, selected_sem_id_lab, selected_course_id_lab, selected_faculty_id_lab1, selected_faculty_id_lab2):
                            st.success("Lab course mapping added!")
                            st.rerun()
                        else:
                            st.error("Failed to add lab mapping. This lab course might already be mapped for this semester.")
                else:
                    st.warning("Please select all options for lab mapping.")

    st.subheader("Current Mappings")
    st.write("### Theory Course Mappings")
    theory_mappings = get_theory_mappings(user_id)
    if theory_mappings:
        df_theory_map = pd.DataFrame([dict(row) for row in theory_mappings])
        st.dataframe(df_theory_map.set_index('id'))
        
        st.subheader("Delete Theory Mapping")
        theory_map_options = {tm['id']: f"Sem {tm['semester_number']}: {tm['course_name']} by {tm['faculty_name']}" for tm in theory_mappings}
        selected_theory_map_id = st.selectbox(
            "Select Theory Mapping to Delete",
            options=list(theory_map_options.keys()),
            format_func=lambda x: theory_map_options[x],
            key="delete_theory_map_select"
        )
        if selected_theory_map_id:
            if st.button("Delete Selected Theory Mapping", type="secondary"):
                if delete_theory_mapping(user_id, selected_theory_map_id):
                    st.success("Theory mapping deleted.")
                    st.rerun()
                else:
                    st.error("Failed to delete theory mapping.")
    else:
        st.info("No theory course mappings added yet.")

    st.write("### Lab Course Mappings")
    lab_mappings = get_lab_mappings(user_id)
    if lab_mappings:
        lab_map_data = [dict(row) for row in lab_mappings]
        df_lab_map = pd.DataFrame(lab_map_data)
        st.dataframe(df_lab_map.set_index('id'))

        st.subheader("Delete Lab Mapping")
        lab_map_options = {lm['id']: f"Sem {lm['semester_number']}: {lm['lab_course_name']} by {lm['faculty_1_name']} & {lm['faculty_2_name']}" for lm in lab_mappings}
        selected_lab_map_id = st.selectbox(
            "Select Lab Mapping to Delete",
            options=list(lab_map_options.keys()),
            format_func=lambda x: lab_map_options[x],
            key="delete_lab_map_select"
        )
        if selected_lab_map_id:
            if st.button("Delete Selected Lab Mapping", type="secondary"):
                if delete_lab_mapping(user_id, selected_lab_map_id):
                    st.success("Lab mapping deleted.")
                    st.rerun()
                else:
                    st.error("Failed to delete lab mapping.")
    else:
        st.info("No lab course mappings added yet.")

def manage_faculty_preferences_page():
    st.image("assets/facultypref.png", use_container_width=True)
    st.header("Faculty Preferences")
    user_id = st.session_state['user_id']

    faculty_list = get_faculty(user_id)
    if not faculty_list:
        st.warning("Please add faculty members first to set their preferences.")
        return

    faculty_options = {f['id']: f['name'] for f in faculty_list}

    with st.expander("Add New Faculty Preference"):
        selected_faculty_id = st.selectbox("Select Faculty", options=list(faculty_options.keys()), format_func=lambda x: faculty_options[x], key="pref_faculty_select")

        days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_day = st.selectbox("Day", days_of_week, key="pref_day_select")
        with col2:
            period_start = st.number_input("Period Start (1-6)", min_value=1, max_value=6, step=1, key="pref_period_start")
        with col3:
            period_end = st.number_input("Period End (1-6)", min_value=1, max_value=6, step=1, key="pref_period_end")

        if_start_greater_than_end = period_start > period_end
        if if_start_greater_than_end:
            st.error("Period Start cannot be greater than Period End.")

        preference_type = st.radio(
            "Preference Type",
            ('blocked', 'preferred'),
            help="Blocked: Faculty cannot be assigned any class. Preferred: Faculty prefers to teach at this time (soft constraint, can be overridden if necessary)."
        )

        if st.button("Add Preference"):
            if selected_faculty_id and selected_day and period_start and period_end and not if_start_greater_than_end:
                if add_faculty_preference(user_id, selected_faculty_id, selected_day, period_start, period_end, preference_type):
                    st.success("Preference added successfully!")
                    st.rerun()
                else:
                    st.error("Failed to add preference. This preference for this faculty might already exist.")
            else:
                st.warning("Please fill all fields correctly.")

    st.subheader("Current Faculty Preferences")
    preferences = get_faculty_preferences(user_id)
    if preferences:
        df_prefs = pd.DataFrame([dict(row) for row in preferences])
        st.dataframe(df_prefs.set_index('id'))

        st.subheader("Delete Faculty Preference")
        pref_options = {p['id']: f"{p['faculty_name']}: {p['day']} {p['period_start']}-{p['period_end']} ({p['preference_type']})" for p in preferences}
        selected_pref_id = st.selectbox(
            "Select Preference to Delete",
            options=list(pref_options.keys()),
            format_func=lambda x: pref_options[x],
            key="delete_pref_select"
        )
        if selected_pref_id:
            if st.button("Delete Selected Preference", type="secondary"):
                if delete_faculty_preference(user_id, selected_pref_id):
                    st.success("Preference deleted.")
                    st.rerun()
                else:
                    st.error("Failed to delete preference.")
    else:
        st.info("No faculty preferences added yet.")

# Build a map: {faculty_id: {"Monday": {"blocked":[(s,e)...], "preferred":[(s,e)...]}, ...}}
def build_faculty_prefs_map(pref_rows, all_data):
    """
    Build a tolerant preferences map:
      { fac_id: { "Monday": {"blocked":[(s,e),...], "preferred":[(s,e),...]}, ... } }
    Accepts rows where faculty can be under: faculty_id | facultyId | fid | faculty | faculty_id_fk | faculty_name
    Day can be: day | Day
    Start/end can be: period_start|start|from_period, period_end|end|to_period
    Type can be: preference_type|type|pref_type
    If only faculty_name is present, resolves to ID via all_data['faculty_by_id'] names.
    """
    from collections import defaultdict

    def pick(d, *keys):
        for k in keys:
            if k in d and d[k] is not None:
                return d[k]
        return None

    # Build name->id map for fallback
    name_to_id = {}
    for fid, fobj in all_data.get('faculty_by_id', {}).items():
        name_to_id[str(getattr(fobj, 'name', '')).strip().lower()] = fid

    prefs = defaultdict(lambda: defaultdict(lambda: {"blocked": [], "preferred": []}))

    for r in pref_rows:
        # faculty id or name
        fid = pick(r, "faculty_id", "facultyId", "fid", "faculty", "faculty_id_fk")
        if fid is None:
            fname = pick(r, "faculty_name", "name", "facultyName")
            if fname:
                fid = name_to_id.get(str(fname).strip().lower())
        # if still missing, skip this row safely
        if fid is None:
            continue

        day = pick(r, "day", "Day")
        if not day:
            continue
        # normalize day text to title-case (e.g., monday->Monday)
        day = str(day).strip().capitalize()

        ps = pick(r, "period_start", "start", "from_period", "fromPeriod")
        pe = pick(r, "period_end", "end", "to_period", "toPeriod")
        if ps is None or pe is None:
            continue
        try:
            ps = int(ps); pe = int(pe)
        except Exception:
            continue

        kind = pick(r, "preference_type", "type", "pref_type")
        kind = str(kind).strip().lower() if kind else ""
        if kind not in ("blocked", "preferred"):
            # default unrecognized types to 'preferred' (soft), or just skip
            continue

        prefs[fid][day][kind].append((ps, pe))

    return prefs


# def generate_timetable_page():
#     st.header("Timetable Generation")
#     user_id = st.session_state['user_id']
#     st.write("Configure Genetic Algorithm parameters and click 'Generate'.")

#     col1, col2, col3, col4 = st.columns(4)
#     with col1:
#         population_size = st.number_input("Population Size", min_value=50, max_value=1000, value=200, step=50, help="Number of candidate timetables in each generation.")
#     with col2:
#         generations = st.number_input("Generations", min_value=100, max_value=5000, value=1000, step=100, help="Number of iterations the algorithm will run.")
#     with col3:
#         mutation_rate = st.slider("Mutation Rate (per gene)", min_value=0.01, max_value=0.5, value=0.05, step=0.01, help="Probability of a single class assignment changing.")
#     with col4:
#         mutation_chance_smart = st.slider("Smart Mutation Chance", min_value=0.0, max_value=1.0, value=0.8, step=0.05, help="Probability that mutation tries to find an empty slot (0=purely random, 1=always try smart).")
#     crossover_rate = st.slider("Crossover Rate", min_value=0.5, max_value=1.0, value=0.8, step=0.05, help="Probability of two parent timetables exchanging genetic material.")

#     st.markdown("---")

#     if st.button("Generate Timetable", type="primary"):
#         st.info("Step 1: Loading required data from the database...")
#         try:
#             all_raw_data = load_all_data(user_id)
#             classes_to_schedule = get_classes_to_schedule(all_raw_data)

#             if not classes_to_schedule:
#                 st.error("No classes defined or mapped. Please add courses and mappings first.")
#                 return
#             if not all_raw_data['semesters_by_id']:
#                 st.error("No semesters defined. Please add semesters.")
#                 return
#             if not all_raw_data['faculty_by_id']:
#                 st.error("No faculty defined. Please add faculty.")
#                 return

#             st.success(f"Loaded data: {len(classes_to_schedule)} scheduled class items to place.")
#             st.info("Step 2: Initializing and running Genetic Algorithm...")

#             ga = GeneticAlgorithm(
#                 classes_to_schedule,
#                 all_raw_data,
#                 population_size=population_size,
#                 generations=generations,
#                 mutation_rate=mutation_rate,
#                 mutation_chance_smart=mutation_chance_smart,
#                 crossover_rate=crossover_rate
#             )

#             st.subheader("Genetic Algorithm Progress")
#             progress_bar = st.progress(0)
#             status_text = st.empty()
#             fitness_text = st.empty()

#             def ga_progress_callback(current_gen, total_gen, current_fitness):
#                 progress_percent = int((current_gen / total_gen) * 100)
#                 progress_bar.progress(progress_percent)
#                 status_text.text(f"Generation {current_gen}/{total_gen}")
#                 fitness_text.text(f"Current Best Fitness: {current_fitness:.2f}")
#                 time.sleep(0.001)

#             with st.spinner("Running Genetic Algorithm... This might take a while for large data sets."):
#                 best_timetable_chromosome = ga.run(progress_callback=ga_progress_callback)

#             progress_bar.progress(100)
#             status_text.text("Generation Complete!")
#             time.sleep(0.5)

#             st.session_state['generated_timetable_chromosome'] = best_timetable_chromosome
#             st.session_state['data_for_analysis'] = all_raw_data 

#             st.subheader("Results")
#             st.write(f"Final Best Fitness: **{best_timetable_chromosome.fitness:.2f}**")

#             if best_timetable_chromosome.fitness >= 0:
#                 st.balloons()
#                 st.success("Timetable generated successfully with all hard constraints satisfied! 🎉")
#             else:
#                 st.warning("Timetable generated, but some hard constraints might still be violated. Consider increasing generations or population size, or adjust penalty values.")
            
#             st.markdown("---")
#             display_generated_timetable(best_timetable_chromosome, all_raw_data)

#             # --- Save timetable snapshot (existing flow) ---
#             st.markdown("---")
#             st.subheader("Save This Timetable")
#             save_name = st.text_input("Enter a name for this timetable:", value=f"Timetable_{datetime.now().strftime('%Y%m%d_%H%M')}")
#             if st.button("Save Timetable", type="secondary"):
#                 if save_name:
#                     if add_saved_timetable(user_id, save_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), best_timetable_chromosome, all_raw_data):
#                         st.success(f"Timetable '{save_name}' saved successfully!")
#                     else:
#                         st.error(f"Failed to save timetable. A timetable with the name '{save_name}' might already exist.")
#                 else:
#                     st.warning("Please enter a name for the timetable.")

#             # --- Export whole timetable PDF ---
#             st.markdown("---")
#             st.subheader("Export (Whole Timetable)")
#             try:
#                 grids = to_shareable_grids(best_timetable_chromosome, all_raw_data)
#                 pdf_title = save_name or f"Timetable_{datetime.now().strftime('%Y%m%d_%H%M')}"
#                 pdf_bytes = build_pdf_from_timetable(grids, title=pdf_title)
#                 st.download_button(
#                     label="Download Entire Timetable as PDF",
#                     data=pdf_bytes,
#                     file_name=f"{pdf_title.replace(' ', '_')}.pdf",
#                     mime="application/pdf"
#                 )
#             except Exception as e:
#                 st.warning(f"Could not build PDF: {e}")

#             # --- Faculty Timetables (display + per-faculty PDF download) ---
#             st.markdown("---")
#             st.subheader("Faculty Timetables")

#             fac_grids = build_faculty_grids(best_timetable_chromosome, all_raw_data)
#             if not fac_grids:
#                 st.info("No faculty assignments found in the generated timetable.")
#             else:
#                 # Build selection of only those faculty who were assigned some class
#                 choices = []
#                 for fid, (fname, grid) in fac_grids.items():
#                     total_cells = sum(1 for d in grid for v in grid[d] if v)
#                     if total_cells > 0:
#                         choices.append((fid, fname))
#                 if not choices:
#                     st.info("No faculty have scheduled classes.")
#                 else:
#                     # Select a faculty to preview & download
#                     display_names = {fid: fname for fid, fname in choices}
#                     chosen_fid = st.selectbox(
#                         "Select Faculty",
#                         options=[fid for fid, _ in choices],
#                         format_func=lambda fid: display_names[fid]
#                     )

#                     if chosen_fid is not None:
#                         fname, grid = fac_grids[chosen_fid]

#                         # Show HTML table preview
#                         day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
#                         periods_cols = [f"Period {i}" for i in range(1, PERIODS_PER_DAY + 1)]
#                         df = pd.DataFrame('', index=day_order, columns=periods_cols)
#                         for day in day_order:
#                             for i in range(PERIODS_PER_DAY):
#                                 if i < len(grid[day]):
#                                     df.iloc[day_order.index(day), i] = grid[day][i].replace("\n", "<br>")
#                         st.markdown(f"**{fname}**")
#                         st.write(df.to_html(escape=False), unsafe_allow_html=True)

#                         # Download this faculty's PDF
#                         single = {f"Faculty: {fname}": grid}
#                         fac_pdf_title = f"Faculty Timetable - {fname}"
#                         fac_pdf = build_pdf_from_timetable(single, title=fac_pdf_title)
#                         st.download_button(
#                             label=f"Download PDF for {fname}",
#                             data=fac_pdf,
#                             file_name=f"{fac_pdf_title.replace(' ', '_')}.pdf",
#                             mime="application/pdf"
#                         )

#         except ValueError as e:
#             st.error(f"Configuration Error: {e}")
#         except Exception as e:
#             st.error(f"An unexpected error occurred during timetable generation: {e}")
#             st.exception(e)
def generate_timetable_page():
    st.image("assets/generatetimetable.png", use_container_width=True)
    st.header("Timetable Generation")
    user_id = st.session_state['user_id']
    st.write("Configure Genetic Algorithm parameters and click 'Generate'.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        population_size = st.number_input("Population Size", 50, 1000, 200, 50)
    with c2:
        generations = st.number_input("Generations", 100, 5000, 1000, 100)
    with c3:
        mutation_rate = st.slider("Mutation Rate", 0.01, 0.5, 0.05, 0.01)
    with c4:
        mutation_chance_smart = st.slider("Smart Mutation", 0.0, 1.0, 0.8, 0.05)
    crossover_rate = st.slider("Crossover Rate", 0.5, 1.0, 0.8, 0.05)

    st.markdown("---")
    if st.button("Generate Timetable", type="primary", key="btn_gen"):
        st.info("Loading data …")
        try:
            all_raw = load_all_data(user_id)
            classes_to_schedule = get_classes_to_schedule(all_raw)
            if not classes_to_schedule:
                st.error("No classes defined or mapped. Please add courses and mappings first.")
                return
            if not all_raw['semesters_by_id'] or not all_raw['faculty_by_id']:
                st.error("Please add semesters and faculty.")
                return

            # build preference map from DB rows and pass to GA
            # pref_rows = get_faculty_preferences(user_id)  # iterable of rows
            # prefs_map = build_faculty_prefs_map([dict(r) for r in pref_rows])
            pref_rows = [dict(r) for r in get_faculty_preferences(user_id)]
            prefs_map = build_faculty_prefs_map(pref_rows, all_raw)  # pass all_raw so we can resolve names->ids


            st.info("Running Genetic Algorithm …")
            ga = GeneticAlgorithm(
                classes_to_schedule, all_raw,
                population_size=population_size,
                generations=generations,
                mutation_rate=mutation_rate,
                mutation_chance_smart=mutation_chance_smart,
                crossover_rate=crossover_rate,
                faculty_prefs_map=prefs_map           # <<< important
            )

            prog = st.progress(0)
            status = st.empty()
            fitbox = st.empty()
            def cb(g, total, fit):
                prog.progress(int(g/total*100))
                status.text(f"Generation {g}/{total}")
                fitbox.text(f"Current Best Fitness: {fit:.2f}")
                time.sleep(0.001)

            with st.spinner("Optimising …"):
                best = ga.run(progress_callback=cb)

            prog.progress(100)
            status.text("Done")

            st.session_state['generated_timetable_chromosome'] = best
            st.session_state['data_for_analysis'] = all_raw
            if 'save_name' not in st.session_state:
                st.session_state['save_name'] = f"Timetable_{datetime.now().strftime('%Y%m%d_%H%M')}"
            st.success("Timetable generated!")

        except Exception as e:
            st.error(f"Error during generation: {e}")
            st.exception(e)

    # show if present in state (so reruns keep UI)
    if 'generated_timetable_chromosome' in st.session_state and 'data_for_analysis' in st.session_state:
        best = st.session_state['generated_timetable_chromosome']
        all_raw = st.session_state['data_for_analysis']

        st.subheader("Results")
        st.write(f"Final Best Fitness: **{best.fitness:.2f}**")
        st.markdown("---")
        display_generated_timetable(best, all_raw)

        st.markdown("---")
        st.subheader("Export (Whole Timetable)")
        try:
            grids = to_shareable_grids(best, all_raw)
            title = st.session_state.get('save_name') or "Timetable"
            pdf = build_pdf_from_timetable(grids, title=title)
            st.download_button("Download Entire Timetable as PDF", pdf, f"{title.replace(' ','_')}.pdf", "application/pdf", key="dl_all")
        except Exception as e:
            st.warning(f"PDF build failed: {e}")

        st.markdown("---")
        st.subheader("Faculty Timetables")
        fac_grids = build_faculty_grids(best, all_raw)
        choices = [(fid, tup[0]) for fid, tup in fac_grids.items() if any(cell for day in tup[1].values() for cell in day)]
        if choices:
            name_map = {fid: nm for fid, nm in choices}
            fid = st.selectbox("Select Faculty", options=[fid for fid, _ in choices], format_func=lambda x: name_map[x], key="fac_sel")
            if fid is not None:
                fname, grid = fac_grids[fid]
                day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                cols = [f"Period {i}" for i in range(1, PERIODS_PER_DAY + 1)]
                df = pd.DataFrame('', index=day_order, columns=cols)
                for day in day_order:
                    for i in range(PERIODS_PER_DAY):
                        df.loc[day, cols[i]] = grid[day][i].replace("\n","<br>")
                st.markdown(f"**{fname}**")
                st.write(df.to_html(escape=False), unsafe_allow_html=True)
                single = {f"Faculty: {fname}": grid}
                fac_title = f"{st.session_state.get('save_name','Timetable')}-Faculty-{fname}"
                fac_pdf = build_pdf_from_timetable(single, title=fac_title)
                st.download_button(f"Download PDF for {fname}", fac_pdf, f"{fac_title.replace(' ','_')}.pdf", "application/pdf", key=f"dl_fac_{fid}")
        else:
            st.info("No faculty have scheduled classes in this timetable.")

        st.markdown("---")
        if st.button("Clear Generated Timetable", key="btn_clear"):
            for k in ("generated_timetable_chromosome", "data_for_analysis", "save_name"):
                st.session_state.pop(k, None)
            st.success("Cleared.")


def display_generated_timetable(chromosome: TimetableChromosome, all_data):
    st.markdown("##### Timetable by Semester")
    timetables_by_semester = defaultdict(list)
    for sc in chromosome.scheduled_classes:
        timetables_by_semester[sc.semester_id].append(sc)
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    periods_cols = [f"Period {i}" for i in range(1, PERIODS_PER_DAY + 1)]
    for sem_id in sorted(timetables_by_semester.keys()):
        classes_for_sem = timetables_by_semester[sem_id]
        sem_obj = all_data['semesters_by_id'].get(sem_id)
        sem_name = sem_obj.semester_number if sem_obj else sem_id
        st.markdown(f"**Semester {sem_name} Timetable**")
        df = pd.DataFrame('', index=days, columns=periods_cols)
        for sc in classes_for_sem:
            for p in range(sc.start_period, sc.end_period + 1):
                if 1 <= p <= PERIODS_PER_DAY:
                    col = f"Period {p}"
                    course = sc.course_obj.code if sc.course_obj else ""
                    facs = ", ".join([f.name for f in sc.faculty_objs]) if sc.faculty_objs else ""
                    cell = f"{course}<br>({facs})" if facs else course
                    df.loc[sc.day, col] = (df.loc[sc.day, col] + ("<br><span style='color:red; font-weight:bold;'>Collision with</span><br>" if df.loc[sc.day, col] else "") + cell)
        st.write(df.to_html(escape=False), unsafe_allow_html=True)
        st.markdown("---")
    # raw list
    rows = []
    for sc in chromosome.scheduled_classes:
        rows.append({
            "Semester": sc.semester_obj.semester_number if sc.semester_obj else sc.semester_id,
            "Course Code": sc.course_obj.code if sc.course_obj else sc.course_id,
            "Faculty": ", ".join([f.name for f in sc.faculty_objs]) if sc.faculty_objs else ", ".join(map(str, sc.faculty_ids)),
            "Is Lab": "Yes" if sc.is_lab else "No",
            "Day": sc.day,
            "Start": sc.start_period,
            "End": sc.end_period
        })
    st.dataframe(pd.DataFrame(rows))

def analyze_timetable_page():
    st.image("assets/timetableanalysis.png", use_container_width=True)
    st.header("Timetable Distribution Analysis")

    if 'generated_timetable_chromosome' not in st.session_state or 'data_for_analysis' not in st.session_state:
        st.warning("Please generate a timetable first from the 'Generate Timetable' page, or load a saved timetable.")
        return

    chromosome = st.session_state['generated_timetable_chromosome']
    all_data = st.session_state['data_for_analysis']

    def create_empty_grid():
        grid = pd.DataFrame(0, index=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], columns=[f"P{i}" for i in range(1, PERIODS_PER_DAY + 1)])
        return grid

    def plot_heatmap(df, title):
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(df, annot=True, cmap="YlGnBu", fmt="g", linewidths=.5, ax=ax)
        ax.set_title(title)
        ax.set_xlabel("Periods")
        ax.set_ylabel("Days")
        st.pyplot(fig)
        plt.clf()

    st.subheader("1. Overall Class Distribution")
    overall_grid = create_empty_grid()
    for sc in chromosome.scheduled_classes:
        for p in range(sc.start_period, sc.end_period + 1):
            period_col_name = f"P{p}"
            overall_grid.loc[sc.day, period_col_name] += 1
    plot_heatmap(overall_grid, "Overall Class Count Distribution (All Semesters)")

    st.markdown("---")
    st.subheader("2. Class Distribution Per Semester")

    semesters = sorted(all_data['semesters_by_id'].values(), key=lambda s: s.semester_number)
    for sem in semesters:
        st.markdown(f"**Semester {sem.semester_number}**")
        semester_grid = create_empty_grid()
        for sc in chromosome.scheduled_classes:
            if sc.semester_id == sem.id:
                for p in range(sc.start_period, sc.end_period + 1):
                    period_col_name = f"P{p}"
                    semester_grid.loc[sc.day, period_col_name] += 1
        plot_heatmap(semester_grid, f"Class Count Distribution - Semester {sem.semester_number}")

    st.markdown("---")
    st.subheader("3. Faculty Workload Distribution")

    faculty_hours = defaultdict(int)
    for sc in chromosome.scheduled_classes:
        for fac_id in sc.faculty_ids:
            faculty_hours[fac_id] += sc.periods_count
    
    faculty_data_for_df = []
    for fac_id, hours in faculty_hours.items():
        faculty_name = all_data['faculty_by_id'][fac_id].name
        faculty_data_for_df.append({"Faculty": faculty_name, "Total Hours": hours})

    if faculty_data_for_df:
        faculty_hours_df = pd.DataFrame(faculty_data_for_df).sort_values(by="Total Hours", ascending=False)
        fig_bar, ax_bar = plt.subplots(figsize=(10, len(faculty_hours_df) * 0.5 + 1))
        sns.barplot(x="Total Hours", y="Faculty", data=faculty_hours_df, palette="viridis", ax=ax_bar)
        ax_bar.set_title("Total Assigned Hours Per Faculty")
        st.pyplot(fig_bar)
        plt.clf()

    st.markdown("---")
    st.subheader("4. Theory vs. Lab Distribution by Period")

    theory_per_period = defaultdict(int)
    lab_per_period = defaultdict(int)
    
    for sc in chromosome.scheduled_classes:
        for p in range(sc.start_period, sc.end_period + 1):
            if sc.is_lab:
                lab_per_period[f"P{p}"] += 1
            else:
                theory_per_period[f"P{p}"] += 1

    period_labels = [f"P{i}" for i in range(1, PERIODS_PER_DAY + 1)]
    theory_counts = [theory_per_period[p] for p in period_labels]
    lab_counts = [lab_per_period[p] for p in period_labels]

    data = {
        'Period': period_labels,
        'Theory Classes': theory_counts,
        'Lab Classes': lab_counts
    }
    df_types = pd.DataFrame(data)

    fig_types, ax_types = plt.subplots(figsize=(10, 6))
    df_types.set_index('Period').plot(kind='bar', stacked=True, ax=ax_types, colormap='Paired')
    ax_types.set_title("Theory vs. Lab Classes Per Period")
    ax_types.set_xlabel("Period")
    ax_types.set_ylabel("Number of Classes")
    ax_types.set_xticklabels(period_labels, rotation=0)
    st.pyplot(fig_types)
    plt.clf()

def show_saved_timetables_page():
    st.header("Saved Timetables")
    user_id = st.session_state['user_id']

    saved_timetables = get_saved_timetables(user_id)

    if not saved_timetables:
        st.info("No timetables saved yet.")
        return

    df_saved = pd.DataFrame([dict(row) for row in saved_timetables])
    st.dataframe(df_saved.set_index('id'))

    st.subheader("Load / Delete Saved Timetable")
    saved_tt_options = {tt['id']: f"{tt['timetable_name']} (Generated: {tt['generated_on']})" for tt in saved_timetables}
    selected_saved_tt_id = st.selectbox(
        "Select Timetable",
        options=list(saved_tt_options.keys()),
        format_func=lambda x: saved_tt_options[x],
        key="select_saved_tt"
    )

    if selected_saved_tt_id:
        current_saved_tt_name = saved_tt_options[selected_saved_tt_id]
        col_load, col_delete = st.columns(2)
        with col_load:
            if st.button("Load and View Selected Timetable", type="primary"):
                with st.spinner(f"Loading '{current_saved_tt_name}'..."):
                    loaded_chromosome, loaded_data_snapshot = load_saved_timetable_data(user_id, selected_saved_tt_id)
                    if loaded_chromosome and loaded_data_snapshot:
                        st.session_state['generated_timetable_chromosome'] = loaded_chromosome
                        st.session_state['data_for_analysis'] = loaded_data_snapshot
                        st.success(f"Timetable '{current_saved_tt_name}' loaded successfully! Displaying below.")
                        display_generated_timetable(loaded_chromosome, loaded_data_snapshot)
                    else:
                        st.error("Failed to load timetable data.")
        with col_delete:
            if st.button("Delete Selected Timetable", type="secondary", key="init_delete_saved_tt"):
                st.session_state[f"confirm_delete_saved_tt_{selected_saved_tt_id}"] = True
            
            if st.session_state.get(f"confirm_delete_saved_tt_{selected_saved_tt_id}", False):
                confirmed = confirm_action(
                    f"Are you sure you want to delete '{current_saved_tt_name}'?",
                    f"confirm_del_saved_tt_{selected_saved_tt_id}"
                )
                if confirmed is not None:
                    if confirmed:
                        if delete_saved_timetable(user_id, selected_saved_tt_id):
                            st.success(f"Timetable '{current_saved_tt_name}' deleted.")
                            st.rerun()
                        else:
                            st.error(f"Failed to delete timetable '{current_saved_tt_name}'.")
                    st.session_state[f"confirm_delete_saved_tt_{selected_saved_tt_id}"] = False

def show_data_management_page():
    st.header("User Data Management")
    user_id = st.session_state['user_id']
    username = st.session_state['username']

    st.warning(f"This section allows you to delete all data associated with your user account: **{username}**.")
    st.info("This action is irreversible and will remove all departments, faculty, courses, mappings, preferences, and saved timetables created by you.")
    
    st.markdown("---")
    st.subheader("Delete All My Data")
    if st.button("Initiate Deletion of All My Data", type="primary", key="init_delete_all_data"):
        st.session_state["confirm_delete_all_user_data"] = True
    
    if st.session_state.get("confirm_delete_all_user_data", False):
        confirmed = confirm_action(
            f"<span style='color:red; font-weight:bold;'>WARNING:</span> Are you absolutely sure you want to delete ALL data for {username}? This cannot be undone!",
            "confirm_del_all_data"
        )
        if confirmed is not None:
            if confirmed:
                if delete_all_user_data(user_id):
                    st.success("All your data has been successfully deleted. You will now be logged out.")
                    st.session_state['logged_in'] = False
                    st.session_state['username'] = None
                    st.session_state['user_id'] = None
                    set_page("login")
                    st.rerun()
                else:
                    st.error("Failed to delete all data. An unexpected error occurred.")
            st.session_state["confirm_delete_all_user_data"] = False

# -----------------------------
# App Shell / Navigation
# -----------------------------
st.sidebar.title("Navigation")

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "login"

if st.session_state['logged_in']:
    st.sidebar.write(f"Logged in as: {st.session_state['username']}")
    st.sidebar.markdown("---")
    if st.sidebar.button("Home", key="nav_home"):
        set_page("welcome")
    if st.sidebar.button("Department & Semester Management", key="nav_dept"):
        set_page("departments")
    if st.sidebar.button("Faculty Management", key="nav_faculty"):
        set_page("faculty")
    if st.sidebar.button("Course Management", key="nav_courses"):
        set_page("courses")
    if st.sidebar.button("Course-Faculty-Semester Mapping", key="nav_mapping"):
        set_page("mapping")
    if st.sidebar.button("Faculty Preferences", key="nav_preferences"):
        set_page("preferences")
    st.sidebar.markdown("---")
    if st.sidebar.button("Generate Timetable", key="nav_generate"):
        set_page("generate_timetable")
    if st.sidebar.button("Timetable Analysis", key="nav_analyze"):
        set_page("analyze_timetable")
    st.sidebar.markdown("---")
    if st.sidebar.button("Account & Data Management", key="nav_data_management"):
        set_page("data_management")
    if st.sidebar.button("Logout", key="nav_logout"):
        st.session_state['logged_in'] = False
        st.session_state['username'] = None
        st.session_state['user_id'] = None
        set_page("login")
        st.rerun()
else:
    show_login_register_page()
#--------------------------------------------------------#
# -------------  Display current page  ------------------#
#--------------------------------------------------------#
if st.session_state['logged_in']:
    if st.session_state['current_page'] == "welcome":
        show_welcome_page()
    elif st.session_state['current_page'] == "departments":
        manage_departments_page()
    elif st.session_state['current_page'] == "faculty":
        manage_faculty_page()
    elif st.session_state['current_page'] == "courses":
        manage_courses_page()
    elif st.session_state['current_page'] == "mapping":
        manage_mapping_page()
    elif st.session_state['current_page'] == "preferences":
        manage_faculty_preferences_page()
    elif st.session_state['current_page'] == "generate_timetable":
        generate_timetable_page()
    elif st.session_state['current_page'] == "analyze_timetable":
        analyze_timetable_page()
    elif st.session_state['current_page'] == "data_management":
        show_data_management_page()
