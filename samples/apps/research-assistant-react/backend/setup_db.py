import sqlite3


def create_db():
    # Connect to the database (or create a new one if it doesn't exist)
    conn = sqlite3.connect("database.sqlite")

    # Create a cursor object to execute SQL commands
    cursor = conn.cursor()

    # Create the table with the specified columns, appropriate data types, and a UNIQUE constraint on (rootMsgId, msgId)
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS messages (
        userId INTEGER NOT NULL,
        rootMsgId INTEGER NOT NULL,
        msgId INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        metadata TEXT,
        timestamp DATETIME NOT NULL,
        UNIQUE (userId,rootMsgId, msgId)
    )
    """
    )

    # Create a table for personalization profiles
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS personalization_profiles (
        userId INTEGER NOT NULL,
        profile TEXT,
        timestamp DATETIME NOT NULL,
        UNIQUE (userId)
    )
    """
    )

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    # print("Database setup complete with appropriate data types and unique constraint.")

    return


create_db()
