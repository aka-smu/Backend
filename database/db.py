import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "results.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


if __name__ == "__main__":
    conn = get_connection()
    print("데이터베이스 연결 성공!")
    print("DB 파일 위치:", DB_PATH)
    conn.close()