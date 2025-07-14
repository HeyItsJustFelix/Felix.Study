#!/usr/bin/env python3
"""
Simple test script to verify the database manager works correctly
"""

from dbmanager import DatabaseManager
import os

def test_database():
    # Use a test database
    test_db = "test_study.db"
    
    # Clean up any existing test database
    if os.path.exists(test_db):
        os.remove(test_db)
    
    print("Testing DatabaseManager...")
    
    # Initialize database manager
    db = DatabaseManager(test_db)
    
    # Test adding a user
    print("\n1. Testing add_user...")
    result = db.add_user(12345, 67890)
    print(f"Add user result: {result}")
    
    # Test getting a user
    print("\n2. Testing get_user...")
    user_data = db.get_user(12345, 67890)
    print(f"User data: {user_data}")
    
    # Test incrementing XP
    print("\n3. Testing increment_xp...")
    leveled_up, level, xp_gained = db.increment_xp(12345, 67890)
    print(f"Leveled up: {leveled_up}, Level: {level}, XP gained: {xp_gained}")
    
    # Test multiple XP increments to trigger level up
    print("\n4. Testing multiple XP increments...")
    for i in range(10):
        leveled_up, level, xp_gained = db.increment_xp(12345, 67890)
        if leveled_up:
            print(f"Level up! New level: {level}, XP gained: {xp_gained}")
            break
        else:
            user_data = db.get_user(12345, 67890)
            current_xp = user_data[5]
            print(f"Increment {i+1}: Level {level}, XP: {current_xp}, Gained: {xp_gained}")
    
    # Test study session
    print("\n5. Testing study session...")
    session_id = db.start_study_session(67890)
    print(f"Started session ID: {session_id}")
    
    db.update_user_session(12345, 67890, session_id)
    print("Updated user session")
    
    import time
    time.sleep(1)  # Wait a second
    
    db.end_study_session(session_id)
    print("Ended session")
    
    duration = db.get_session_duration(session_id)
    print(f"Session duration: {duration} minutes")
    
    # Test updating study time
    print("\n6. Testing study time update...")
    db.update_total_study_time(12345, 67890, 30)  # Add 30 minutes
    user_data = db.get_user(12345, 67890)
    print(f"Total study time: {user_data[4]} minutes")
    
    # Test leaderboard
    print("\n7. Testing leaderboard...")
    # Add another user for leaderboard test
    db.add_user(54321, 67890)
    db.increment_xp(54321, 67890)
    db.update_total_study_time(54321, 67890, 15)
    
    leaderboard = db.get_leaderboard(67890)
    print("Leaderboard:")
    for i, (user_id, total_time, xp, level) in enumerate(leaderboard, 1):
        print(f"  {i}. User {user_id}: Level {level}, {xp} XP, {total_time} minutes")
    
    # Clean up
    db.close()
    
    # Remove test database
    if os.path.exists(test_db):
        os.remove(test_db)
    
    print("\n✅ All tests completed successfully!")

if __name__ == "__main__":
    test_database()
