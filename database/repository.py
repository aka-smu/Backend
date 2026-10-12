import sqlite3
from .db import get_connection
from .models import create_tables


def save_scan_result(result):
    # 테이블이 없으면 생성
    create_tables()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        meta = result["meta"]
        findings = result["findings"]

        # 1. 검사 기록 저장
        cursor.execute("""
            INSERT INTO scans (
                entry_url,
                started_at,
                finished_at,
                elapsed_sec
            )
            VALUES (?, ?, ?, ?)
        """, (
            meta["entry_url"],
            meta["started_at"],
            meta["finished_at"],
            meta["elapsed_sec"]
        ))

        # 방금 저장한 검사 번호
        scan_id = cursor.lastrowid

        # 2. 탐지 결과 저장
        for finding in findings:
            cursor.execute("""
                INSERT INTO findings (
                    scan_id,
                    url,
                    location,
                    evidence_text,
                    technique,
                    is_violation
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                scan_id,
                finding["url"],
                finding["location"],
                finding["evidence_text"],
                finding["technique"],
                int(finding["is_violation"])
            ))

        conn.commit()

        print("데이터베이스 저장 성공!")
        print("검사 번호:", scan_id)
        print("저장된 탐지 결과:", len(findings), "개")

        return scan_id

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def get_scan_result(scan_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT * FROM scans WHERE id = ?",
            (scan_id,)
        )
        scan = cursor.fetchone()

        if scan is None:
            return None

        cursor.execute(
            "SELECT * FROM findings WHERE scan_id = ? ORDER BY id",
            (scan_id,)
        )
        findings = cursor.fetchall()

        return {
            "scan": dict(scan),
            "findings": [dict(f) for f in findings]
        }

    finally:
        conn.close()

def get_scan_history():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT
                scans.id,
                scans.entry_url,
                scans.started_at,
                scans.finished_at,
                scans.elapsed_sec,
                COUNT(findings.id) AS finding_count
            FROM scans
            LEFT JOIN findings
                ON scans.id = findings.scan_id
            GROUP BY scans.id
            ORDER BY scans.id DESC
        """)

        rows = cursor.fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()