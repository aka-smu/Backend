"""반복적으로 게시되는 유사 광고 댓글을 탐지한다."""

from collections import defaultdict
from difflib import SequenceMatcher

from .config import (
    SIMILARITY_THRESHOLD,
    MIN_SIMILAR_COMMENTS,
    MAX_COMMENT_LENGTH,
    SPAM_BASE_SCORE,
)

from .keywords import (
    SEARCH_INDUCEMENT_KEYWORDS,
    BAIT_KEYWORDS,
)

from .normalizer import normalize_text


def is_comment(content):
    """댓글 영역에서 수집한 콘텐츠인지 확인한다."""

    source_type = str(
        content.get("source_type", "")
    ).lower()

    location = str(
        content.get("location", "")
    ).lower()

    return (
        source_type == "comment"
        or "comment" in location
        or "댓글" in location
    )


def similarity(text1, text2):
    """두 문장의 유사도를 0~1 사이 값으로 계산한다."""

    normalized1 = normalize_text(text1)
    normalized2 = normalize_text(text2)

    if not normalized1 or not normalized2:
        return 0.0

    return SequenceMatcher(
        None,
        normalized1,
        normalized2,
    ).ratio()


def has_ad_signal(text):
    """검색 유도 또는 광고성 표현이 있는지 확인한다."""

    normalized = normalize_text(text)

    keywords = (
        SEARCH_INDUCEMENT_KEYWORDS
        | BAIT_KEYWORDS
    )

    return any(
        normalize_text(keyword) in normalized
        for keyword in keywords
    )


def get_comment_scope(content):
    """같은 페이지와 댓글 영역에 속하는지 구분한다."""

    return (
        content.get("url", ""),
        content.get("frame_id") or "",
        content.get("frame_url") or "",
        content.get("frame_path") or "",
        content.get("comment_scope") or "",
    )


def detect_repeated_spam(contents):
    """같은 영역에 반복 게시된 유사 광고 댓글을 탐지한다."""

    groups = defaultdict(list)

    for content in contents:
        if not is_comment(content):
            continue

        text = str(content.get("text", "")).strip()

        if not text:
            continue

        if len(text) > MAX_COMMENT_LENGTH:
            continue

        scope = get_comment_scope(content)
        groups[scope].append(content)

    findings = []

    for scope, comments in groups.items():
        visited = set()

        for i, base in enumerate(comments):
            if i in visited:
                continue

            similar_indices = [i]

            for j in range(i + 1, len(comments)):
                if j in visited:
                    continue

                score = similarity(
                    base.get("text", ""),
                    comments[j].get("text", ""),
                )

                if score >= SIMILARITY_THRESHOLD:
                    similar_indices.append(j)

            if len(similar_indices) < MIN_SIMILAR_COMMENTS:
                continue

            matching_comments = [
                comments[index]
                for index in similar_indices
            ]

            if not any(
                has_ad_signal(item.get("text", ""))
                for item in matching_comments
            ):
                continue

            visited.update(similar_indices)

            for item in matching_comments:
                findings.append({
                    "url": item.get("url", ""),
                    "location": item.get("location", ""),
                    "text": item.get("text", ""),
                    "category": "spam",
                    "score": SPAM_BASE_SCORE,
                    "raw_score": SPAM_BASE_SCORE,
                    "matched_keywords": [],
                    "evidence": {},
                    "techniques": ["REPEATED_SPAM"],
                    "source_type": "comment",
                    "frame_id": item.get("frame_id"),
                    "frame_url": item.get("frame_url"),
                    "frame_path": item.get("frame_path"),
                    "details": {
                        "similar_count": len(similar_indices),
                        "similarity_threshold": SIMILARITY_THRESHOLD,
                    },
                })

    return findings