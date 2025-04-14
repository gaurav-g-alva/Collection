# models.py
from dataclasses import dataclass
from typing import List, Dict, Any
import sqlite3
import json
from datetime import datetime, time

@dataclass
class User:
    id: int
    email: str
    password_hash: str
    full_name: str
    role: str
    is_active: bool

@dataclass
class Course:
    id: int
    code: str
    name: str
    type: str
    credits: int
    theory_hours: int
    lab_hours: int
    semester: int

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('timetable.db')
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE,
                password_hash TEXT,
                full_name TEXT,
                role TEXT,
                is_active BOOLEAN
            );
            
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE,
                name TEXT,
                type TEXT,
                credits INTEGER,
                theory_hours INTEGER,
                lab_hours INTEGER,
                semester INTEGER
            );
            
            CREATE TABLE IF NOT EXISTS faculty_availability (
                id INTEGER PRIMARY KEY,
                faculty_id INTEGER,
                day TEXT,
                start_time TEXT,
                end_time TEXT,
                FOREIGN KEY (faculty_id) REFERENCES users (id)
            );
            
            CREATE TABLE IF NOT EXISTS timetables (
                id INTEGER PRIMARY KEY,
                semester INTEGER,
                data TEXT,
                generated_at TIMESTAMP
            );
        """)
        self.conn.commit()

db = Database()

def get_all_users() -> List[Dict[str, Any]]:
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM users")
    return [dict(zip(['id', 'email', 'password_hash', 'full_name', 'role', 'is_active'], row))
            for row in cursor.fetchall()]

def get_all_courses() -> List[Dict[str, Any]]:
    cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM courses")
    return [dict(zip(['id', 'code', 'name', 'type', 'credits', 'theory_hours', 'lab_hours', 'semester'], row))
            for row in cursor.fetchall()]

def get_faculty_schedule(faculty_id: int) -> List[Dict[str, Any]]:
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT t.data
        FROM timetables t
        WHERE t.data LIKE ?
    """, (f'%"faculty_id": {faculty_id}%',))
    schedules = []
    for row in cursor.fetchall():
        data = json.loads(row[0])
        if isinstance(data, list):
            schedules.extend([slot for slot in data if slot.get('faculty_id') == faculty_id])
    return schedules

def update_faculty_availability(faculty_id: int, availability: Dict[str, Dict[str, time]]):
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM faculty_availability WHERE faculty_id = ?", (faculty_id,))
    
    for day, times in availability.items():
        cursor.execute("""
            INSERT INTO faculty_availability (faculty_id, day, start_time, end_time)
            VALUES (?, ?, ?, ?)
        """, (faculty_id, day, times['start'].strftime('%H:%M'), times['end'].strftime('%H:%M')))
    
    db.conn.commit()

def get_student_semester(student_id: int) -> int:
    cursor = db.conn.cursor()
    cursor.execute("SELECT semester FROM student_info WHERE student_id = ?", (student_id,))
    result = cursor.fetchone()
    return result[0] if result else 1

def get_student_timetable(semester: int) -> List[Dict[str, Any]]:
    cursor = db.conn.cursor()
    cursor.execute("""
        SELECT data
        FROM timetables
        WHERE semester = ?
        ORDER BY generated_at DESC
        LIMIT 1
    """, (semester,))
    result = cursor.fetchone()
    return json.loads(result[0]) if result else None

def save_timetable(semester: int, timetable_data: List[Dict[str, Any]]):
    cursor = db.conn.cursor()
    cursor.execute("""
        INSERT INTO timetables (semester, data, generated_at)
        VALUES (?, ?, ?)
    """, (semester, json.dumps(timetable_data), datetime.now().isoformat()))
    db.conn.commit()