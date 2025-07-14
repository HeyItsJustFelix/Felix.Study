import sqlite3

class DatabaseManager:
    def __init__(self, db_name):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS userstats (
                userid = INTEGER,
                serverid INTEGER,
                last_
            )
        ''')
        self.connection.commit()

    def add_user(self, username):
        self.cursor.execute('INSERT INTO users (username) VALUES (?)', (username,))
        self.connection.commit()

    def get_user(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return self.cursor.fetchone()

    def close(self):
        self.connection.close()