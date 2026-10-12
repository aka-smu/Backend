from .db import get_connection

def create_tables():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target_url TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'COMPLETED',
            verdict TEXT,
            risk_score REAL,
            summary TEXT,
            started_at TEXT,
            finished_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_id INTEGER NOT NULL,
            severity TEXT NOT NULL DEFAULT 'WARNING',
            category TEXT,
            title TEXT,
            reason TEXT,
            evidence_text TEXT,
            location_label TEXT,
            technique TEXT,
            score REAL,
            source_finding_id TEXT,
            url TEXT,
            FOREIGN KEY (analysis_id) REFERENCES analysis(id)
        )""")
        conn.commit()
    finally:
        conn.close()

if __name__ == '__main__':
    create_tables()
    print('테이블 생성 성공! (analysis, findings)')
