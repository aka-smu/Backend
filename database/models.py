from .db import get_connection


def create_tables():

    conn = get_connection()

    try:
        cursor = conn.cursor()

        # 검사 정보 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_url TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                elapsed_sec REAL,
                topic TEXT,
                tool_version TEXT
            )
        """)

        # 불법광고 탐지 결과 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                finding_id TEXT,
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