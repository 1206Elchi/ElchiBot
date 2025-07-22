from .database import init_db, add_points, remove_points, get_points
import sqlite3
import os

init_db()
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "databases", "elchcoins.db")

def get_user_points(username: str) -> int:
    return get_points(username)

def give_user_points(username: str, amount: int):
    add_points(username, amount)

def take_user_points(username: str, amount: int):
    remove_points(username, amount)

def get_top_users(limit=3):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username, points FROM user_points ORDER BY points DESC LIMIT ?", (limit,))
    result = c.fetchall()
    conn.close()
    return result