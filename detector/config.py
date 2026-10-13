"""팀이 데이터로 조정할 탐지 정책. 점수는 확률이 아니다."""

DETECTION_THRESHOLD = 30

EVIDENCE_WEIGHTS = {
    "phone": 20,
    "url": 20,
    "contact": 20
}

SIMILARITY_THRESHOLD = 0.75

MIN_SIMILAR_COMMENTS = 5

MAX_COMMENT_LENGTH = 500

SPAM_BASE_SCORE = 40

SCHEMA_VERSION = "2.1.0"