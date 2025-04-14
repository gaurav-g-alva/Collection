# Project Summary
The TimeTable Generator is a Python-based web application that automates the creation of academic timetables for educational institutions. It provides a user-friendly dashboard tailored for different roles—admins, faculty, and students—enabling efficient interaction with the system. By employing a genetic algorithm, the application generates conflict-free schedules while considering faculty availability and academic constraints. This solution enhances the scheduling process, improves user experience, and offers effective management tools for educational settings.

# Project Module Description
- **User Management**: Facilitates role-based access control, allowing admins to manage users and permissions.
- **Timetable Generation**: Utilizes a genetic algorithm to create optimal timetables based on courses, faculty availability, and constraints.
- **Data Management**: Oversees course and faculty data, including historical timetables for reference.
- **Export Functionality**: Allows users to export generated timetables in PDF format.
- **Role-Based Dashboards**: Provides customized interfaces for admins, faculty, and students.

# Directory Tree
```
.
├── docs
│   ├── timetable_generator_class_diagram.mermaid  # Class diagram for system architecture
│   ├── timetable_generator_design.json              # System design document in JSON format
│   ├── timetable_generator_design.md                 # System design document in Markdown format
│   ├── timetable_generator_prd.json                  # Product Requirements Document in JSON format
│   ├── timetable_generator_prd.md                    # Product Requirements Document in Markdown format
│   ├── timetable_generator_sequence_diagram.mermaid  # Sequence diagram for system processes
│   └── timetable_generator_system_design.md          # Detailed system design document
└── streamlit_template
    ├── app.py                                       # Main application file
    ├── auth.py                                      # User authentication logic
    ├── generator.py                                  # Genetic algorithm implementation
    ├── models.py                                     # Database models and interactions
    ├── requirements.txt                              # Project dependencies
    ├── template_config.json                          # Configuration for templates
    ├── timetable.db                                  # SQLite database for storing timetable data
    └── utils.py                                      # Utility functions, including PDF generation
```

# File Description Inventory
- **app.py**: Main entry point for the Streamlit application, handling routing and user interactions.
- **auth.py**: Manages user authentication and role-based access.
- **generator.py**: Implements the genetic algorithm for timetable generation.
- **models.py**: Defines data models and handles database operations.
- **requirements.txt**: Lists all dependencies required for the application.
- **template_config.json**: Configuration settings for templates used in the application.
- **timetable.db**: SQLite database file for storing generated timetables and related data.
- **utils.py**: Contains helper functions, including those for PDF generation.

# Technology Stack
- **Frontend**: Streamlit for building interactive web applications.
- **Backend**: FastAPI for RESTful API development.
- **Database**: PostgreSQL for data persistence.
- **ORM**: SQLAlchemy for database interactions.
- **Authentication**: JWT for secure user sessions.
- **Key Libraries**: DEAP (Genetic Algorithm), Pandas (Data Manipulation), ReportLab (PDF Generation), Pydantic (Data Validation).

# Usage
1. **Install Dependencies**: Run `pip install -r requirements.txt` to install the necessary packages.
2. **Run the Application**: Execute `streamlit run app.py` to start the application on the appropriate port.
3. **Access the Application**: Open the application in your web browser to interact with the timetable generator.
