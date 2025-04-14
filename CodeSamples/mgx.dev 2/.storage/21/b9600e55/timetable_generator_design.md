# TimeTable Generator System Design

## Implementation Approach

We will build the TimeTable Generator using Python with the following technology stack:

### Technology Stack
- **Frontend**: Streamlit for building interactive web interface
- **Backend**: FastAPI for RESTful API development
- **Database**: PostgreSQL for data persistence
- **ORM**: SQLAlchemy for database operations
- **Authentication**: JWT tokens with Streamlit session state

### Core Libraries
- **DEAP**: For implementing the genetic algorithm
- **Pandas**: For data manipulation and analysis
- **ReportLab**: For PDF generation
- **Pydantic**: For data validation

### Architecture Components

1. **Authentication System**
- JWT-based authentication
- Role-based access control (Admin/Faculty/Student)
- Session management using Streamlit state

2. **Data Management Layer**
- PostgreSQL database with following schema:
  - users (id, email, password_hash, full_name, role)
  - courses (id, code, name, type, credits, theory_hours, lab_hours, semester)
  - faculty_availability (id, faculty_id, day, start_time, end_time)
  - timetables (id, semester, status, generated_at)
  - schedules (id, timetable_id, course_id, faculty_id, timeslot)

3. **Timetable Generation Engine**
- Genetic Algorithm Implementation:
  - Chromosome: Complete timetable solution
  - Gene: Individual class scheduling (course-faculty-timeslot)
  - Population: Set of possible timetables
  - Fitness Function: Evaluates constraint satisfaction
  - Selection: Tournament selection
  - Crossover: Two-point crossover
  - Mutation: Random timeslot reassignment

4. **API Layer**
- Admin APIs:
  - /api/admin/users - User management
  - /api/admin/courses - Course management
  - /api/admin/timetable - Timetable generation and management

- Faculty APIs:
  - /api/faculty/availability - Manage availability
  - /api/faculty/timetable - View assigned schedule

- Student APIs:
  - /api/student/timetable - View semester timetable

5. **User Interface (Streamlit)**
- Login page with role-based redirection
- Admin dashboard:
  - User management
  - Course management
  - Timetable generation controls
- Faculty dashboard:
  - Availability management
  - Schedule view
- Student dashboard:
  - Timetable view
  - PDF export

### Security Measures
- Password hashing using bcrypt
- JWT token validation
- Input sanitization
- Role-based access control

### Performance Optimization
- Database indexing for frequent queries
- Caching of generated timetables
- Asynchronous API operations
- Pagination for large datasets

## Data Structures and Interfaces
See class diagram in timetable_generator_class_diagram.mermaid

## Program Call Flow
See sequence diagram in timetable_generator_sequence_diagram.mermaid

## Potential Concerns
1. Performance optimization for genetic algorithm with large datasets
2. Handling concurrent timetable generation requests
3. Backup and recovery strategy for timetable data
4. Scaling strategy for multiple departments