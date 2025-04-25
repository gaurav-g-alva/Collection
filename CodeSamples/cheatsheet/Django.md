# 🐍 Django CLI Commands Cheat Sheet

## 🚀 Project Initialization
| Command | Description |
|--------|-------------|
| `django-admin startproject projectname` | Create a new Django project |
| `python manage.py startapp appname` | Create a new Django app within a project |

## 🧩 Project Management
| Command | Description |
|--------|-------------|
| `python manage.py runserver` | Start development server (default: 127.0.0.1:8000) |
| `python manage.py runserver 8080` | Run server on port 8080 |
| `python manage.py check` | Check for any problems in your project |

## 🧬 Database Management
| Command | Description |
|--------|-------------|
| `python manage.py makemigrations` | Create migration files from model changes |
| `python manage.py migrate` | Apply migrations to the database |
| `python manage.py showmigrations` | List migrations and their applied status |
| `python manage.py sqlmigrate appname migration_number` | Show SQL for a migration |

## 👤 User and Admin
| Command | Description |
|--------|-------------|
| `python manage.py createsuperuser` | Create a new superuser |
| `python manage.py changepassword username` | Change a user's password |

## 🔍 Shell and Debugging
| Command | Description |
|--------|-------------|
| `python manage.py shell` | Start an interactive Django shell |
| `python manage.py dbshell` | Open DB shell (if database configured) |

## 📦 Static Files
| Command | Description |
|--------|-------------|
| `python manage.py collectstatic` | Collect static files for deployment |

## 🧪 Testing
| Command | Description |
|--------|-------------|
| `python manage.py test` | Run all tests |
| `python manage.py test appname` | Run tests for a specific app |

## 🛠️ Utilities and Maintenance
| Command | Description |
|--------|-------------|
| `python manage.py help` | Show all available commands |
| `python manage.py help <command>` | Show help for a specific command |
| `python manage.py flush` | Remove all data and reset the DB |
| `python manage.py loaddata filename.json` | Load data from a fixture file |
| `python manage.py dumpdata` | Dump data to a JSON file |
