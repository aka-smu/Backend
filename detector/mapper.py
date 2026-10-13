"""여러 탐지기의 분석 결과를 통일된 Finding 형식으로 변환한다."""

import hashlib
import json


def make_finding(result, index=None):
    """탐지 결과 한 건을 Finding 형식으로 변환한다."""

    techniques = list(dict.fromkeys(
        result.get("techniques", [])
    ))

    evidence_text = str(result.get("text", ""))

    finding = {
        "id": "",
        "url": result.get("url", ""),
        "location": result.get("location", ""),
        "category": result.get("category", ""),
        "techniques": techniques,
        "score": result.get("score", 0),
        "raw_score": result.get("raw_score", 0),
        "evidence_text": evidence_text,
        "matched_keywords": result.get("matched_keywords", []),
        "evidence": result.get("evidence", {}),
        "source_type": result.get("source_type", "text"),
        "frame_id": result.get("frame_id"),
        "frame_url": result.get("frame_url"),
        "frame_path": result.get("frame_path"),
        "details": result.get("details", {}),
    }

    # 탐지 결과의 주요 정보를 이용해 고유 ID 생성
    identity = {
        "url": finding["url"],
        "location": finding["location"],
        "category": finding["category"],
        "techniques": sorted(finding["techniques"]),
        "evidence_text": finding["evidence_text"],
        "source_type": finding["source_type"],
        "frame_id": finding["frame_id"],
        "frame_path": finding["frame_path"],
    }

    encoded = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    ).encode("utf-8")

    digest = hashlib.sha256(encoded).hexdigest()[:12]

    finding["id"] = f"f_{digest}"

    return finding


def create_findings(results):
    """탐지 결과 목록을 변환하고 중복 결과를 제거한다."""

    findings = []
    seen = set()

    for result in results:
        finding = make_finding(result)

        if finding["id"] in seen:
            continue

        seen.add(finding["id"])
        findings.append(finding)

    return findings