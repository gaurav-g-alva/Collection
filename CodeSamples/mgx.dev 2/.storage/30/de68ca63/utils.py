# utils.py
from typing import List, Dict, Any
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from io import BytesIO

def format_timetable_for_display(timetable_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convert timetable data to a pandas DataFrame for display."""
    # Create empty DataFrame with days as rows and periods as columns
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    periods = list(range(1, 9))
    df = pd.DataFrame(index=days, columns=periods)
    
    # Fill in the timetable data
    for entry in timetable_data:
        day = entry['day']
        period = entry['period']
        course_info = f"{entry['course_code']}\n{entry['course_name']}\n({entry['type']})"
        df.at[day, period] = course_info
    
    return df

def generate_pdf(timetable_data: List[Dict[str, Any]]) -> bytes:
    """Generate a PDF version of the timetable."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Convert timetable data to a format suitable for PDF
    df = format_timetable_for_display(timetable_data)
    table_data = [['Period'] + list(df.columns)]
    for idx, row in df.iterrows():
        table_data.append([idx] + [str(cell) if pd.notna(cell) else '' for cell in row])
    
    # Create table
    table = Table(table_data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('BACKGROUND', (0, 0), (0, -1), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    return buffer.getvalue()

def validate_course_data(course_data: Dict[str, Any]) -> bool:
    """Validate course data before insertion."""
    required_fields = ['code', 'name', 'type', 'credits', 'theory_hours', 'lab_hours', 'semester']
    return all(field in course_data and course_data[field] is not None for field in required_fields)

def validate_faculty_availability(availability_data: Dict[str, Dict[str, str]]) -> bool:
    """Validate faculty availability data."""
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    for day in availability_data:
        if day not in days:
            return False
        if 'start' not in availability_data[day] or 'end' not in availability_data[day]:
            return False
    return True
