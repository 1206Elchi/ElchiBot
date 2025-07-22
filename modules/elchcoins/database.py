# database.py
import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "databases")
os.makedirs(DB_DIR, exist_ok=True)

DB_PATH = os.path.join(DB_DIR, "elchcoins.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_points (
            username TEXT PRIMARY KEY,
            points INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def add_points(username, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO user_points (username, points)
        VALUES (?, ?)
        ON CONFLICT(username) DO UPDATE SET points = points + ?
    ''', (username.lower(), amount, amount))
    conn.commit()
    conn.close()

def remove_points(username, amount):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        UPDATE user_points
        SET points = MAX(points - ?, 0)
        WHERE username = ?
    ''', (amount, username.lower()))
    conn.commit()
    conn.close()

def get_points(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT points FROM user_points WHERE username = ?', (username.lower(),))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0
