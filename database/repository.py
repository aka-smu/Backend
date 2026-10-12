import sqlite3
from .db import get_connection
from .models import create_tables

def _severity(finding):
    value = str(finding.get('severity') or 'WARNING').upper()
    return value if value in {'CRITICAL', 'WARNING', 'MINOR'} else 'WARNING'

def save_scan_result(result):
    create_tables()
    conn = get_connection()
    cursor = conn.cursor()
    try:
        meta = result.get('meta', {})
        findings = result.get('findings', [])
        target_url = meta.get('target_url') or meta.get('entry_url') or (findings[0].get('url', '') if findings else '')
        status = meta.get('status') or 'COMPLETED'
        verdict = meta.get('verdict') or ('VIOLATION_FOUND' if findings else 'NO_VIOLATION')
        risk_score = meta.get('risk_score')

        if risk_score is None:
            risk_score = max((float(f.get('score') or 0) for f in findings), default=0.0)
        summary = meta.get('summary') or f'탐지 항목 {len(findings)}개'
        cursor.execute("""INSERT INTO analysis
            (target_url, status, verdict, risk_score, summary, started_at, finished_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (target_url, status, verdict, risk_score, summary, meta.get('started_at'), meta.get('finished_at')))
        analysis_id = cursor.lastrowid
        for f in findings:
            technique = f.get('technique') or 'KEYWORD'
            category = f.get('category') or technique
            title = f.get('title') or f'불법광고 탐지: {category}'
            evidence = f.get('evidence_text') or f.get('text') or ''
            reason = f.get('reason') or evidence or '탐지 규칙에 해당하는 내용이 발견됨'
            location = f.get('location_label') or f.get('location') or ''
            cursor.execute("""INSERT INTO findings
                (analysis_id, severity, category, title, reason, evidence_text, location_label, technique, score, source_finding_id, url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (analysis_id, _severity(f), category, title, reason, evidence, location, technique, f.get('score'), f.get('id'), f.get('url')))
        conn.commit()
        print('데이터베이스 저장 성공!')
        print('검사 번호:', analysis_id)
        print('저장된 탐지 결과:', len(findings), '개')
        return analysis_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_scan_result(analysis_id):
    conn = get_connection(); conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM analysis WHERE id = ?', (analysis_id,))
        analysis = cursor.fetchone()
        if analysis is None: return None
        cursor.execute('SELECT * FROM findings WHERE analysis_id = ? ORDER BY id', (analysis_id,))
        return {'analysis': dict(analysis), 'findings': [dict(r) for r in cursor.fetchall()]}
    finally: conn.close()

def get_scan_history():
    conn = get_connection(); conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("""SELECT analysis.*, COUNT(findings.id) AS finding_count
            FROM analysis LEFT JOIN findings ON analysis.id = findings.analysis_id
            GROUP BY analysis.id ORDER BY analysis.id DESC""")
        return [dict(r) for r in cursor.fetchall()]
    finally:
        conn.close()
