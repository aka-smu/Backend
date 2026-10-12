import sqlite3

from .db import get_connection
from .models import create_tables


# ==========================================
# 1. 탐지 결과 DB 저장
# ==========================================

def save_scan_result(result):

    create_tables()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        meta = result["meta"]
        findings = result["findings"]

        # 검사 정보 저장
        cursor.execute("""
            INSERT INTO scans (
                entry_url,
                started_at,
                finished_at,
                elapsed_sec,
                topic,
                tool_version
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            meta["entry_url"],
            meta.get("started_at"),
            meta.get("finished_at"),
            meta.get("elapsed_sec"),
            meta.get("topic"),
            meta.get("tool_version")
        ))

        # 방금 저장한 검사 번호
        scan_id = cursor.lastrowid

        # 탐지된 광고 각각 저장
        for finding in findings:

            cursor.execute("""
                INSERT INTO findings (
                    scan_id,
                    finding_id,
                    url,
                    location,
                    evidence_text,
                    technique,
                    is_violation
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                scan_id,
                finding.get("id"),
                finding.get("url"),
                finding.get("location"),
                finding.get("evidence_text"),
                finding.get("technique"),
                int(finding.get("is_violation", False))
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


# ==========================================
# 2. 특정 검사 결과 조회
# ==========================================

def get_scan_result(scan_id):

    conn = get_connection()
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()

    try:
        # 검사 정보 조회
        cursor.execute("""
            SELECT *
            FROM scans
            WHERE id = ?
        """, (scan_id,))

        scan = cursor.fetchone()

        if scan is None:
            return None

        # 해당 검사에서 발견된 광고 조회
        cursor.execute("""
            SELECT *
            FROM findings
            WHERE scan_id = ?
            ORDER BY id
        """, (scan_id,))

        findings = cursor.fetchall()

        return {
            "scan": dict(scan),
            "findings": [
                dict(finding)
                for finding in findings
            ]
        }

    finally:
        conn.close()


# ==========================================
# 3. 전체 검사 기록 조회
# ==========================================

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
                scans.topic,
                scans.tool_version,
                COUNT(findings.id) AS finding_count

            FROM scans

            LEFT JOIN findings
                ON scans.id = findings.scan_id

            GROUP BY scans.id

            ORDER BY scans.id DESC
        """)

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        conn.close()