# auth.py
import hashlib
import secrets
from typing import Optional
import models

def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return f"{salt}${hash_obj.hexdigest()}"

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify a password against its hash."""
    salt, hash_value = stored_password.split('$')
    hash_obj = hashlib.sha256((provided_password + salt).encode())
    return hash_obj.hexdigest() == hash_value

def authenticate_user(email: str, password: str) -> Optional[models.User]:
    """Authenticate a user by email and password."""
    cursor = models.db.conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,))
    user_data = cursor.fetchone()
    
    if user_data and verify_password(user_data[2], password):
        return models.User(
            id=user_data[0],
            email=user_data[1],
            password_hash=user_data[2],
            full_name=user_data[3],
            role=user_data[4],
            is_active=user_data[5]
        )
    return None

def create_user(email: str, password: str, full_name: str, role: str) -> models.User:
    """Create a new user."""
    cursor = models.db.conn.cursor()
    password_hash = hash_password(password)
    
    cursor.execute("""
        INSERT INTO users (email, password_hash, full_name, role, is_active)
        VALUES (?, ?, ?, ?, 1)
    """, (email, password_hash, full_name, role))
    
    models.db.conn.commit()
    return authenticate_user(email, password)

def deactivate_user(user_id: int) -> bool:
    """Deactivate a user account."""
    cursor = models.db.conn.cursor()
    cursor.execute("UPDATE users SET is_active = 0 WHERE id = ?", (user_id,))
    models.db.conn.commit()
    return cursor.rowcount > 0

def update_password(user_id: int, new_password: str) -> bool:
    """Update user's password."""
    cursor = models.db.conn.cursor()
    password_hash = hash_password(new_password)
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    models.db.conn.commit()
    return cursor.rowcount > 0
