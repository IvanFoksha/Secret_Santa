import sqlite3
from config import DB_PATH


def init_bd():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(
        '''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        wishes_sent INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS rooms (
        room_id TEXT PRIMARY KEY,
        creator_id INTEGER,
        max_users INTEGER DEFAULT 5,
        is_paid BOOLEAN DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS room_users (
        room_id TEXT,
        user_id INTEGER,
        FOREIGN KEY(room_id) REFERENCES rooms(room_id),
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    );

    CREATE TABLE IF NOT EXISTS wishes (
        wish_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        room_id TEXT,
        wish_text TEXT,
        target_user_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        FOREIGN KEY(room_id) REFERENCES rooms(room_id)
    );

    ''')
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)', (user_id, username))
    conn.commit()
    conn.close()

def create_room(room_id, creator_id, max_users):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO rooms (room_id, creator_id, max_users) VALUES (?, ?, ?)', (room_id, creator_id, max_users))
    conn.commit()
    conn.close()

def add_user_to_room(room_id, user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO room_users (room_id, user_id) VALUES (?, ?)', (room_id, user_id))
    conn.commit()
    conn.close()

def count_users_in_room(room_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM room_users WHERE room_id = ?', (room_id))
    result = cursor.fetchone()[0]
    conn.close()
    return result

def add_wish(user_id, wish_text):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO wishes (user_id, wish_text) VALUES (?, ?)', (user_id, wish_text))
    conn.commit()
    conn.close()

def edit_wish(user_id, wish_id, new_text):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE wishes SET wich_text = ? WHERE user_id = ? AND wish_id = ? ', (new_text, user_id, wish_id))
    update = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return update

def delete_wish(user_id, wish_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE DROM wishes WHERE user_id = ? AND wish_id = ?', (user_id, wish_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_user_wishes(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT wish_id, wish_text FROM wishes WHERE user_id = ?', (user_id))
    wishes = cursor.fetchall()
    conn.commit()
    conn.close()
    return wishes

def get_all_rooms():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT room_id, creator_id FROM rooms', (user_id))
    rooms = cursor.fetchall()
    conn.close()
    return rooms

def get_room_wishes(romm_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT w.wish_text, w.user_id, u.username AS user_name
        FROM wishes w
        JOIN user u ON w.user_id = u.user_id
        WHERE w.room_id = ?
        ''', (room_id,))
    wishes = cursor.fetchall()
    conn.close()
    return wishes

def grant_access(user_id, room_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE rooms SET is_paid = 1 WHERE creator_id = ?', (user_id,))
    conn.commit()
    conn.close()
