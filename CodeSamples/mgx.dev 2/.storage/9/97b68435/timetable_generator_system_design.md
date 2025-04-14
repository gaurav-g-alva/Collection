# TimeTable Generator System Design

## Implementation Approach

### Technology Stack
- Frontend: Streamlit (Python-based web framework for rapid development)
- Backend: FastAPI (Modern, fast Python web framework)
- Database: PostgreSQL (Robust relational database)
- Authentication: JWT with FastAPI security
- ORM: SQLAlchemy

### Key Libraries
- DEAP (Distributed Evolutionary Algorithms in Python) for genetic algorithm
- Pandas for data manipulation
- ReportLab for PDF generation
- Pydantic for data validation
- PyTest for testing

### Architecture Overview
1. **Three-Tier Architecture**:
   - Presentation Layer (Streamlit)
   - Application Layer (FastAPI)
   - Data Layer (PostgreSQL)

2. **Key Components**:
   - User Authentication System
   - Role-Based Access Control (RBAC)
   - Timetable Generator Engine
   - PDF Export Service
   - Data Management System

3. **Genetic Algorithm Approach**:
   - Population: Set of possible timetables
   - Chromosome: Complete timetable solution
   - Gene: Individual class assignment
   - Fitness Function: Evaluates constraints satisfaction
   - Selection: Tournament selection
   - Crossover: Two-point crossover
   - Mutation: Random reassignment

### Security Measures
- JWT-based authentication
- Password hashing using bcrypt
- Role-based access control
- Input validation and sanitization
- CORS policy implementation

### Performance Optimization
- Database indexing for frequent queries
- Caching frequently accessed data
- Async operations for non-blocking I/O
- Pagination for large datasets

## Data Structures and Interfaces
See class diagram in timetable_generator_class_diagram.mermaid

## Program Call Flow
See sequence diagram in timetable_generator_sequence_diagram.mermaid

## Anything UNCLEAR
1. Maximum concurrent users expected for performance tuning
2. Specific priority rules for different types of classes
3. Policy for handling failed timetable generation attempts
4. Data retention policy for historical timetables