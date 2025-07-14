import sqlite3
import random

class DatabaseManager:
    def __init__(self, db_name):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS userstats (
                userid INTEGER,
                serverid INTEGER,
                last_study_session_time INTEGER DEFAULT NULL,
                last_study_session_id INTEGER DEFAULT NULL,
                total_study_time INTEGER DEFAULT 0,
                user_xp INTEGER DEFAULT 0,
                user_level INTEGER DEFAULT 1,
                PRIMARY KEY (userid, serverid)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS study_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                start_time INTEGER,
                end_time INTEGER
            )
        ''')
        self.connection.commit()

    def add_user(self, user_id, server_id):
        self.cursor.execute('INSERT INTO userstats (userid, serverid) VALUES (?, ?)', (user_id, server_id))
        try:
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            print(f"Error adding user: {e}")
            return False

    def get_user(self, user_id, server_id):
        self.cursor.execute('SELECT * FROM userstats WHERE userid = ? AND serverid = ?', (user_id, server_id))
        return self.cursor.fetchone()
    
    def get_last_session(self, user_id, server_id):
        self.cursor.execute('SELECT last_study_session_time, last_study_session_id FROM userstats WHERE userid = ? AND serverid = ?', (user_id, server_id))
        return self.cursor.fetchone()
    
    def increment_xp(self, user_id, server_id):
        user_data = self.get_user(user_id, server_id)
        if not user_data:
            # Create user if doesn't exist
            self.add_user(user_id, server_id)
            user_data = self.get_user(user_id, server_id)
        
        current_xp = user_data[5]  # user_xp column
        current_level = user_data[6]  # user_level column
        xp_gain = random.randint(15, 25)
        new_xp = current_xp + xp_gain
        
        # Calculate XP needed for next level (same formula as main.py)
        next_level_xp = 5 * (current_level * current_level) + 50 * current_level + 100
        
        # Check if user levels up
        if new_xp >= next_level_xp:
            new_level = current_level + 1
            remaining_xp = new_xp - next_level_xp
            self.cursor.execute('UPDATE userstats SET user_xp = ?, user_level = ? WHERE userid = ? AND serverid = ?', 
                              (remaining_xp, new_level, user_id, server_id))
            self.connection.commit()
            return True, new_level, xp_gain  # Return level up status, new level, and XP gained
        else:
            self.cursor.execute('UPDATE userstats SET user_xp = ? WHERE userid = ? AND serverid = ?', 
                              (new_xp, user_id, server_id))
            self.connection.commit()
            return False, current_level, xp_gain  # Return no level up, current level, and XP gained

    def start_study_session(self, server_id):
        """Start a new study session and return the session ID"""
        import time
        start_time = int(time.time())
        self.cursor.execute('INSERT INTO study_sessions (server_id, start_time) VALUES (?, ?)', 
                          (server_id, start_time))
        self.connection.commit()
        return self.cursor.lastrowid

    def end_study_session(self, session_id):
        """End a study session"""
        import time
        end_time = int(time.time())
        self.cursor.execute('UPDATE study_sessions SET end_time = ? WHERE session_id = ?', 
                          (end_time, session_id))
        self.connection.commit()

    def update_user_session(self, user_id, server_id, session_id):
        """Update user's last study session info"""
        import time
        current_time = int(time.time())
        self.cursor.execute('UPDATE userstats SET last_study_session_time = ?, last_study_session_id = ? WHERE userid = ? AND serverid = ?',
                          (current_time, session_id, user_id, server_id))
        self.connection.commit()

    def get_session_duration(self, session_id):
        """Get the duration of a study session in minutes"""
        self.cursor.execute('SELECT start_time, end_time FROM study_sessions WHERE session_id = ?', (session_id,))
        session = self.cursor.fetchone()
        if session and session[1]:  # If session exists and has end time
            duration_seconds = session[1] - session[0]
            return duration_seconds // 60  # Return duration in minutes
        return 0

    def update_total_study_time(self, user_id, server_id, minutes):
        """Add study time to user's total"""
        user_data = self.get_user(user_id, server_id)
        if user_data:
            current_total = user_data[4]  # total_study_time column
            new_total = current_total + minutes
            self.cursor.execute('UPDATE userstats SET total_study_time = ? WHERE userid = ? AND serverid = ?',
                              (new_total, user_id, server_id))
            self.connection.commit()

    def get_leaderboard(self, server_id, limit=10):
        """Get leaderboard data for a server, ordered by level then XP"""
        self.cursor.execute('''
            SELECT userid, total_study_time, user_xp, user_level 
            FROM userstats 
            WHERE serverid = ? 
            ORDER BY user_level DESC, user_xp DESC, total_study_time DESC 
            LIMIT ?
        ''', (server_id, limit))
        return self.cursor.fetchall()

    def close(self):
        self.connection.close()