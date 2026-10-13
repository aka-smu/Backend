"""텍스트에서 불법광고 의심 키워드와 우회 표현을 탐지한다."""

import re

from .config import DETECTION_THRESHOLD, EVIDENCE_WEIGHTS
from .keywords import KEYWORDS, CONTACT_KEYWORDS
from .normalizer import (
    normalize_text,
    normalized_provenance,
)
from .css_detector import detect_hidden_css


PHONE_PATTERN = re.compile(
    r"(?<!\d)01[016789][-\s]?\d{3,4}[-\s]?\d{4}(?!\d)"
)

URL_PATTERN = re.compile(
    r"https?://[^\s]+|www\.[^\s]+",
    re.IGNORECASE,
)


def detect_ad(text):
    """문장 하나의 광고 의심 점수와 유형을 계산한다."""

    original = str(text or "")
    normalized = normalize_text(original)

    category_scores = {}
    category_matches = {}

    for category, words in KEYWORDS.items():
        score = 0
        matched = []

        for keyword, weight in words.items():
            normalized_keyword = normalize_text(keyword)

            if normalized_keyword and normalized_keyword in normalized:
                score += weight
                matched.append(keyword)

        category_scores[category] = score
        category_matches[category] = matched

    if not category_scores:
        return {
            "detected": False,
            "category": None,
            "score": 0,
            "raw_score": 0,
            "matched_keywords": [],
            "evidence": {},
        }

    category = max(category_scores, key=category_scores.get)
    raw_score = category_scores[category]

    evidence = {
        "phone": bool(PHONE_PATTERN.search(original)),
        "url": bool(URL_PATTERN.search(original)),
        "contact": any(
            normalize_text(word) in normalized
            for word in CONTACT_KEYWORDS
        ),
    }

    evidence_score = sum(
        EVIDENCE_WEIGHTS.get(name, 0)
        for name, found in evidence.items()
        if found
    )

    total_score = raw_score + evidence_score

    # 광고 관련 키워드가 전혀 없으면 연락처만으로 탐지하지 않는다.
    detected = (
        raw_score > 0
        and total_score >= DETECTION_THRESHOLD
    )

    return {
        "detected": detected,
        "category": category if detected else None,
        "score": total_score,
        "raw_score": raw_score,
        "matched_keywords": category_matches[category],
        "evidence": evidence,
    }


def analyze_content(content):
    """크롤러가 수집한 콘텐츠 한 건을 분석한다."""

    text = content.get("text", "")
    result = detect_ad(text)

    if not result["detected"]:
        return None

    provenance = normalized_provenance(text)

    techniques = ["KEYWORD"]

    for technique in provenance["techniques"]:
        if technique not in techniques:
            techniques.append(technique)

    for technique in detect_hidden_css(content.get("style", {})):
        if technique not in techniques:
            techniques.append(technique)

    return {
        "url": content.get("url", ""),
        "location": content.get("location", ""),
        "text": text,
        "category": result["category"],
        "score": result["score"],
        "raw_score": result["raw_score"],
        "matched_keywords": result["matched_keywords"],
        "evidence": result["evidence"],
        "techniques": techniques,
        "source_type": content.get("source_type", "text"),
        "frame_id": content.get("frame_id"),
        "frame_url": content.get("frame_url"),
        "frame_path": content.get("frame_path"),
        "details": {
            "normalized_text": provenance["normalized"],
        },
    }


def analyze_contents(contents):
    """크롤러가 수집한 모든 텍스트를 분석한다."""

    results = []

    for content in contents:
        result = analyze_content(content)

        if result is not None:
            results.append(result)

    return results