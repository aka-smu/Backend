import re
import unicodedata
from difflib import SequenceMatcher


# --------------------------------------------------
# 반복 스팸 판단 기준
# 실제 데이터 튜닝 시 이 값만 조정 가능
# --------------------------------------------------

SIMILARITY_THRESHOLD = 0.75
MIN_SIMILAR_COMMENTS = 5


# --------------------------------------------------
# 우회 문자 정규화
# --------------------------------------------------

HOMOGLYPH_MAP = {
    "ι": "i",
    "Ι": "i",
    "ｉ": "i",
    "ⓘ": "i",

    "０": "0",
    "１": "1",
    "２": "2",
    "３": "3",
    "４": "4",
    "５": "5",
    "６": "6",
    "７": "7",
    "８": "8",
    "９": "9",
}


def normalize_homoglyph(text):
    """
    전각 문자 등 Unicode 우회 문자를
    일반 문자 형태로 정규화
    """

    text = unicodedata.normalize(
        "NFKC",
        text
    )

    for fake, normal in HOMOGLYPH_MAP.items():
        text = text.replace(
            fake,
            normal
        )

    return text


# --------------------------------------------------
# 댓글 비교용 정규화
# --------------------------------------------------

def normalize_comment(text):

    if not text:
        return ""

    text = text.lower()

    # Unicode 정규화
    text = normalize_homoglyph(text)

    # Instagram UI 문자열 제거
    text = re.sub(
        r"like|reply",
        "",
        text,
        flags=re.IGNORECASE
    )

    # 시간 표시 제거
    # 5w / 2d / 3h 등
    text = re.sub(
        r"\b\d+\s*[wdhms]\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    # 특수문자 / 공백 제거
    # 광고 문구 사이에 ., ˙, 。 등을
    # 삽입하는 우회 대응
    text = re.sub(
        r"[^가-힣ㄱ-ㅎㅏ-ㅣa-z0-9]",
        "",
        text
    )

    return text


# --------------------------------------------------
# URL 존재 여부
# --------------------------------------------------

def contains_url(text):

    if not text:
        return False

    pattern = r"https?://[^\s]+"

    return bool(
        re.search(
            pattern,
            text,
            re.IGNORECASE
        )
    )


# --------------------------------------------------
# 검색 유도 표현 탐지
# --------------------------------------------------

def contains_search_inducement(text):

    if not text:
        return False

    normalized = normalize_comment(text)

    keywords = [
        "검색",
        "검색하면",
        "검색해봐",
        "검색해보면",
        "찾아봐",
        "찾아보면",
        "네이버",

        # 실제 스팸에서 확인된 변형
        "구글",
        "꾸글",
        "google",
    ]

    for keyword in keywords:

        normalized_keyword = normalize_comment(
            keyword
        )

        if normalized_keyword in normalized:
            return True

    # '검 ... 색'처럼 글자를 분리한 경우
    if "검" in normalized and "색" in normalized:
        return True

    return False


# --------------------------------------------------
# 낚시성 표현 탐지
# --------------------------------------------------

def contains_bait(text):

    if not text:
        return False

    normalized = normalize_comment(text)

    keywords = [
        "유출",
        "유츨",
        "영상",
        "사진",
        "실화",
        "진짜였어",
        "삭제되기전에",
        "믿기힘들",
        "충격",
        "이중생활",
        "어린애들은",
        "남자만",
    ]

    for keyword in keywords:

        normalized_keyword = normalize_comment(
            keyword
        )

        if normalized_keyword in normalized:
            return True

    return False


# --------------------------------------------------
# 두 댓글의 유사도
# --------------------------------------------------

def calculate_similarity(
    text1,
    text2
):

    normalized1 = normalize_comment(
        text1
    )

    normalized2 = normalize_comment(
        text2
    )

    if not normalized1 or not normalized2:
        return 0.0

    return SequenceMatcher(
        None,
        normalized1,
        normalized2
    ).ratio()


# --------------------------------------------------
# 완전히 같은 댓글 제거
# --------------------------------------------------

def remove_duplicate_comments(comments):

    unique = []
    seen = set()

    for comment in comments:

        text = comment.get(
            "text",
            ""
        ).strip()

        if not text:
            continue

        # 같은 URL + 같은 위치 + 같은 텍스트는
        # 동일한 DOM 데이터로 판단
        key = (
            comment.get("url", ""),
            comment.get("location", ""),
            text
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(comment)

    return unique


# --------------------------------------------------
# 유사 댓글 그룹 생성
# --------------------------------------------------

def find_similar_comment_groups(
    comments
):

    groups = []

    used = set()

    for i in range(len(comments)):

        if i in used:
            continue

        base = comments[i]

        group = [base]
        group_indexes = [i]

        for j in range(
            i + 1,
            len(comments)
        ):

            if j in used:
                continue

            similarity = calculate_similarity(
                base["text"],
                comments[j]["text"]
            )

            if similarity >= SIMILARITY_THRESHOLD:

                group.append(
                    comments[j]
                )

                group_indexes.append(j)

        if len(group) >= MIN_SIMILAR_COMMENTS:

            groups.append(group)

            for index in group_indexes:
                used.add(index)

    return groups


# --------------------------------------------------
# 반복 스팸 최종 탐지
# --------------------------------------------------

def detect_repeated_spam(
    crawl_results
):

    # ----------------------------------------------
    # 댓글로 분류된 데이터만 사용
    # ----------------------------------------------

    comments = []

    for item in crawl_results:

        if item.get(
            "element_type"
        ) != "comment":
            continue

        text = item.get(
            "text",
            ""
        )

        if not text:
            continue

        # 지나치게 긴 부모 DOM 제외
        if len(text) > 500:
            continue

        comments.append(item)

    # DOM 중복 제거
    comments = remove_duplicate_comments(
        comments
    )

    # 유사 댓글 그룹 생성
    groups = find_similar_comment_groups(
        comments
    )

    spam_results = []

    for group in groups:

        texts = [
            item["text"]
            for item in group
        ]

        has_url = any(
            contains_url(text)
            for text in texts
        )

        has_search = any(
            contains_search_inducement(text)
            for text in texts
        )

        has_bait = any(
            contains_bait(text)
            for text in texts
        )

        # 단순히 비슷하기만 한 댓글은
        # 스팸으로 처리하지 않음
        if not (
            has_url
            or has_search
            or has_bait
        ):
            continue

        evidence = []

        for item in group:

            evidence.append({
                "url": item.get(
                    "url",
                    ""
                ),

                "location": item.get(
                    "location",
                    ""
                ),

                "text": item.get(
                    "text",
                    ""
                )
            })

        spam_results.append({

            "type":
                "REPEATED_SPAM",

            "count":
                len(group),

            "has_url":
                has_url,

            "has_search_inducement":
                has_search,

            "has_bait":
                has_bait,

            "evidence":
                evidence
        })

    return spam_results