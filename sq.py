import sqlite3

DB_NAME = "users.db"


# ---------------- DATABASE CONNECTION ---------------- #

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    return conn


# ---------------- CREATE TABLES ---------------- #

def create_tables():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# ---------------- CREATE ACCOUNT ---------------- #

def create_user(username, password):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )

        conn.commit()
        conn.close()

        return True

    except sqlite3.IntegrityError:
        conn.close()
        return False


# ---------------- LOGIN CHECK ---------------- #

def login_user(username, password):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (username, password)
    )

    user = cursor.fetchone()

    conn.close()

    if user:
        return True
    else:
        return False


# ---------------- CHECK USER EXISTS ---------------- #

def user_exists(username):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    )

    user = cursor.fetchone()

    conn.close()

    if user:
        return True
    else:
        return False
    
def reset_password(username, new_password):

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "UPDATE users SET password=? WHERE username=?",
            (new_password, username)
        )

        conn.commit()
        conn.close()

        return True

    except Exception as e:
        conn.close()
        return False
