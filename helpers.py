from flask import redirect, session
from functools import wraps
import sqlite3

# Login required decorator
def login_required(f):  
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

def create_db():
    # If the database doesn't exist, create it and the necessary tables
    conn = sqlite3.connect("rentals.db")
    cursor = conn.cursor()

    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS property_owners (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            hash TEXT NOT NULL
        );
        ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            number TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            hash TEXT NOT NULL
        );
        ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apartments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            rent REAL NOT NULL,
            location TEXT NOT NULL,
            FOREIGN KEY (owner_id) REFERENCES property_owners(id)
        );
        ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS apartment_images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apartment_id INTEGER NOT NULL,
            image_blob BLOB NOT NULL, 
            FOREIGN KEY (apartment_id) REFERENCES apartments (id)
        )
        ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rent_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id INTEGER NOT NULL,
            tenant_number TEXT NOT NULL,
            apartment_id INTEGER NOT NULL,
            status TEXT NOT NULL
        )
        ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_name INTEGER NOT NULL,
            tenant_email TEXT NOT NULL,
            message TEXT NOT NULL,
            apartment_id INTEGER NOT NULL,
            owner_id INTEGER NOT NULL,
            FOREIGN KEY (apartment_id) REFERENCES apartments (id),
            FOREIGN KEY (owner_id) REFERENCES property_owners (id)
        )
        ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apartment_id INTEGER NOT NULL,
            tenant_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (apartment_id) REFERENCES apartments (id),
            FOREIGN KEY (tenant_id) REFERENCES tenants (id)
        )
        ''')
    
    
    # Commit changes and close the connection
    conn.commit()
    conn.close()

# Call this function when the app starts
create_db()
