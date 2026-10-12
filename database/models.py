from .db import get_connection


def create_tables():
    conn = get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_url TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                elapsed_sec REAL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                url TEXT,
                location TEXT,
                evidence_text TEXT,
                technique TEXT,
                is_violation INTEGER,

                FOREIGN KEY (scan_id)
                    REFERENCES scans(id)
            )
        """)

        conn.commit()

    finally:
        conn.close()


if __name__ == "__main__":
    create_tables()
    print("테이블 생성 성공!")