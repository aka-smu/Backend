import os
import re
import json
import time
import unicodedata

from datetime import datetime

from detector.keywords import (
    gambling_keywords,
    loan_keywords,
    contact_keywords,
    homoglyph_map
)
from detector.spam_detector import detect_repeated_spam


DETECTION_THRESHOLD = 30


# ==================================================
# 한글 자모 결합
# ==================================================

def combine_korean_jamo(text):

    CHOSUNG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
    JUNGSUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
    JONGSUNG = "ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"

    result = ""
    i = 0

    while i < len(text):

        if (
            i + 1 < len(text)
            and text[i] in CHOSUNG
            and text[i + 1] in JUNGSUNG
        ):

            cho = CHOSUNG.index(text[i])
            jung = JUNGSUNG.index(text[i + 1])

            jong = 0
            move = 2

            if (
                i + 2 < len(text)
                and text[i + 2] in JONGSUNG
            ):

                if not (
                    i + 3 < len(text)
                    and text[i + 2] in CHOSUNG
                    and text[i + 3] in JUNGSUNG
                ):

                    jong = JONGSUNG.index(
                        text[i + 2]
                    ) + 1

                    move = 3

            unicode_value = (
                0xAC00
                + (cho * 21 + jung) * 28
                + jong
            )

            result += chr(unicode_value)

            i += move

        else:

            result += text[i]
            i += 1

    return result


# ==================================================
# JAMO 탐지
# ==================================================

def detect_jamo(text):

    combined_text = combine_korean_jamo(text)

    if combined_text == text:
        return False

    all_keywords = (
        list(gambling_keywords.keys())
        + list(loan_keywords.keys())
    )

    for keyword in all_keywords:

        original_has_keyword = (
            keyword in text
        )

        combined_has_keyword = (
            keyword in combined_text
        )

        if (
            not original_has_keyword
            and combined_has_keyword
        ):
            return True

    return False


# ==================================================
# HOMOGLYPH 정규화
# ==================================================

def normalize_homoglyph(text):

    normalized = unicodedata.normalize(
        "NFKC",
        text
    )

    result = ""

    for char in normalized:

        if char in homoglyph_map:
            result += homoglyph_map[char]

        else:
            result += char

    return result


# ==================================================
# 전체 텍스트 정규화
# ==================================================

def normalize_text(text):

    if not text:
        return ""

    normalized = text.lower()

    normalized = normalize_homoglyph(
        normalized
    )

    # 공백 및 광고 우회용 특수문자 제거
    normalized = re.sub(
        r"[\s._\-★☆♥♡˙·。,]+",
        "",
        normalized
    )

    normalized = combine_korean_jamo(
        normalized
    )

    return normalized


# ==================================================
# HOMOGLYPH 탐지
# ==================================================

def detect_homoglyph(text):

    if not text:
        return False

    # JAMO와 HOMOGLYPH 중복 판정 방지
    if re.search(
        r"[ㄱ-ㅎㅏ-ㅣ]",
        text
    ):
        return False

    normalized_text = normalize_homoglyph(
        text
    )

    if normalized_text == text:
        return False

    all_keywords = (
        list(gambling_keywords.keys())
        + list(loan_keywords.keys())
    )

    for keyword in all_keywords:

        original_has_keyword = (
            keyword in text
        )

        normalized_has_keyword = (
            keyword in normalized_text
        )

        if (
            not original_has_keyword
            and normalized_has_keyword
        ):
            return True

    return False


# ==================================================
# TRANSPARENT 탐지
#
# playwright_crawler.py가 넘기는 style:
#
# {
#     "opacity": "...",
#     "color": "...",
#     "display": "...",
#     "visibility": "...",
#     ...
# }
# ==================================================

def detect_transparent(style):

    if not isinstance(style, dict):
        return False

    opacity = str(
        style.get("opacity", "")
    ).strip()

    color = str(
        style.get("color", "")
    ).lower().replace(" ", "")

    visibility = str(
        style.get("visibility", "")
    ).lower()

    # 완전 투명
    if opacity == "0":
        return True

    # rgba(...,0)
    if re.search(
        r"rgba\([^)]*,0(?:\.0+)?\)",
        color
    ):
        return True

    # transparent 색상
    if color == "transparent":
        return True

    # visibility:hidden
    if visibility == "hidden":
        return True

    return False


# ==================================================
# OFFSCREEN / 숨김 탐지
# ==================================================

def detect_offscreen(style):

    if not isinstance(style, dict):
        return False

    display = str(
        style.get("display", "")
    ).lower()

    font_size = str(
        style.get("fontSize", "")
    ).lower()

    position = str(
        style.get("position", "")
    ).lower()

    left = str(
        style.get("left", "")
    ).lower()

    top = str(
        style.get("top", "")
    ).lower()

    # display:none
    if display == "none":
        return True

    # 글자 크기를 극단적으로 줄여 숨김
    if font_size in (
        "0px",
        "1px"
    ):
        return True

    # absolute/fixed 위치로 화면 밖 이동
    if position in (
        "absolute",
        "fixed"
    ):

        left_match = re.search(
            r"(-?\d+(?:\.\d+)?)px",
            left
        )

        if left_match:

            left_value = float(
                left_match.group(1)
            )

            if left_value <= -1000:
                return True

        top_match = re.search(
            r"(-?\d+(?:\.\d+)?)px",
            top
        )

        if top_match:

            top_value = float(
                top_match.group(1)
            )

            if top_value <= -1000:
                return True

    return False


# ==================================================
# 전화번호 탐지
# ==================================================

def detect_phone(text):

    phone_pattern = (
        r"01[016789]-?\d{3,4}-?\d{4}"
    )

    return re.findall(
        phone_pattern,
        text
    )


# ==================================================
# URL 탐지
# ==================================================

def detect_url(text):

    url_pattern = r"https?://[^\s]+"

    return re.findall(
        url_pattern,
        text
    )


# ==================================================
# 연락 유도 표현
# ==================================================

def detect_contact(text):

    found_contacts = []

    for keyword in contact_keywords:

        if keyword.lower() in text.lower():
            found_contacts.append(
                keyword
            )

    return found_contacts


# ==================================================
# 증거 점수 추가
# ==================================================

def add_evidence_score(
    results,
    evidence_name,
    score
):

    for result in results:

        result["score"] += score

        if "evidence" not in result:
            result["evidence"] = []

        result["evidence"].append(
            evidence_name
        )


# ==================================================
# 불법광고 내용 탐지
# ==================================================

def detect_ad(text):

    results = []

    normalized_text = normalize_text(
        text
    )

    phones = detect_phone(text)
    urls = detect_url(text)
    contacts = detect_contact(text)

    # ----------------------------------------------
    # 도박 광고
    # ----------------------------------------------

    gambling_found = []
    gambling_score = 0

    for keyword, weight in gambling_keywords.items():

        if (
            normalize_text(keyword)
            in normalized_text
        ):

            gambling_found.append(
                keyword
            )

            gambling_score += weight

    if gambling_found:

        results.append({
            "type": "도박 광고 의심",
            "matched_keywords":
                gambling_found,
            "score":
                gambling_score,
            "evidence": []
        })

    # ----------------------------------------------
    # 불법 금융 광고
    # ----------------------------------------------

    loan_found = []
    loan_score = 0

    for keyword, weight in loan_keywords.items():

        if (
            normalize_text(keyword)
            in normalized_text
        ):

            loan_found.append(
                keyword
            )

            loan_score += weight

    if loan_found:

        results.append({
            "type":
                "불법 금융 광고 의심",

            "matched_keywords":
                loan_found,

            "score":
                loan_score,

            "evidence": []
        })

    # ----------------------------------------------
    # 추가 증거 점수
    # ----------------------------------------------

    if phones and results:

        add_evidence_score(
            results,
            "phone",
            20
        )

    if urls and results:

        add_evidence_score(
            results,
            "url",
            20
        )

    if contacts and results:

        add_evidence_score(
            results,
            "contact",
            20
        )

    if not results:

        return {
            "detected": False,
            "results": [],
            "phones": phones,
            "urls": urls,
            "contacts": contacts
        }

    max_score = max(
        result["score"]
        for result in results
    )

    return {
        "detected":
            max_score
            >= DETECTION_THRESHOLD,

        "results":
            results,

        "phones":
            phones,

        "urls":
            urls,

        "contacts":
            contacts
    }


# ==================================================
# 크롤링 요소 하나 분석
# ==================================================

def analyze_content(content):

    text = content.get(
        "text",
        ""
    )

    url = content.get(
        "url",
        ""
    )

    location = content.get(
        "location",
        ""
    )

    element = content.get(
        "element",
        ""
    )

    element_type = content.get(
        "element_type",
        "content"
    )

    style = content.get(
        "style",
        {}
    )

    visible = content.get(
        "visible",
        True
    )

    detection = detect_ad(
        text
    )

    # 광고 내용 자체가 탐지된 경우에만
    # 은닉 기법을 violation으로 판단
    jamo_detected = (
        detect_jamo(text)
        and detection["detected"]
    )

    homoglyph_detected = (
        detect_homoglyph(text)
        and detection["detected"]
    )

    transparent_detected = (
        detect_transparent(style)
        and detection["detected"]
    )

    offscreen_detected = (
        detect_offscreen(style)
        and detection["detected"]
    )

    techniques = []

    if jamo_detected:
        techniques.append(
            "JAMO"
        )

    if homoglyph_detected:
        techniques.append(
            "HOMOGLYPH"
        )

    if transparent_detected:
        techniques.append(
            "TRANSPARENT"
        )

    if offscreen_detected:
        techniques.append(
            "OFFSCREEN"
        )

    return {
        "url":
            url,

        "location":
            location,

        "element":
            element,

        "element_type":
            element_type,

        "visible":
            visible,

        "text":
            text,

        "style":
            style,

        "detected":
            detection["detected"],

        "techniques":
            techniques,

        "results":
            detection["results"],

        "phones":
            detection["phones"],

        "urls":
            detection["urls"],

        "contacts":
            detection["contacts"]
    }


# ==================================================
# 전체 크롤링 결과 분석
# ==================================================

def analyze_contents(contents):

    analyzed_results = []

    for content in contents:

        result = analyze_content(
            content
        )

        analyzed_results.append(
            result
        )

    return analyzed_results


# ==================================================
# 공식 result.json findings 생성
#
# 공식 은닉 탐지 기법만 result.json에 기록
# ==================================================

def create_findings(
    analyzed_results
):

    findings = []

    seen = set()

    for result in analyzed_results:

        if not result["detected"]:
            continue

        techniques = result["techniques"] or ["KEYWORD"]

        for technique in techniques:

            # 동일 위치 + 동일 기법 중복 방지
            key = (
                result["url"],
                result["location"],
                technique
            )

            if key in seen:
                continue

            seen.add(key)

            finding = {

                "id":
                    f"f_{len(findings) + 1:03d}",

                "url":
                    result["url"],

                "is_violation":
                    True,

                "location":
                    result["location"],

                "evidence_text":
                    result["text"],

                "technique":
                    technique
            }

            findings.append(
                finding
            )

    return findings


# ==================================================
# result.json 저장
# ==================================================

def save_results(
    findings,
    entry_url,
    started_at,
    finished_at,
    elapsed_sec,
    filename="result.json"
):

    output = {

        "meta": {

            "topic":
                "TOPIC",

            "entry_url":
                entry_url,

            "started_at":
                started_at,

            "finished_at":
                finished_at,

            "elapsed_sec":
                elapsed_sec,

            "tool_version":
                "1.0.0"
        },

        "findings":
            findings
    }

    # detector.py가 있는 폴더 경로
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # detector 폴더 안에 result.json 저장
    file_path = os.path.join(base_dir, filename)

    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=4
        )

    return output


# ==================================================
# main.py에서 호출
# ==================================================

def run_detection(
    contents,
    entry_url
):

    started_at = (
        datetime.now()
        .astimezone()
    )

    start_time = (
        time.perf_counter()
    )

    analyzed_results = (
        analyze_contents(
            contents
        )
    )

    findings = create_findings(
        analyzed_results
    )

        # 반복 스팸 탐지
    spam_results = detect_repeated_spam(contents)

    # 반복 스팸 결과를 findings에 추가
    for spam in spam_results:
        for evidence in spam["evidence"]:

            findings.append({
                "id": f"f_{len(findings) + 1:03d}",
                "url": evidence["url"],
                "is_violation": True,
                "location": evidence["location"],
                "evidence_text": evidence["text"],
                "technique": "REPEATED_SPAM"
            })

    end_time = (
        time.perf_counter()
    )

    finished_at = (
        datetime.now()
        .astimezone()
    )

    elapsed_sec = round(
        end_time - start_time,
        3
    )

    save_results(
        findings=findings,
        entry_url=entry_url,
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        elapsed_sec=elapsed_sec
    )

    return findings

if __name__ == "__main__":

        test_data = [
        {
            "url": "https://example.com",
            "location": f"comment_{i}",
            "element_type": "comment",
            "text": f"꾸글에 검..색해봐 충격 영상 공개!! {i}",
            "style": {},
            "visible": True
        }
        for i in range(1, 6)
    ]

print("1. 광고 탐지 결과:")
print(detect_ad(test_data[0]["text"]))

print("2. 전체 분석 결과:")
print(analyze_contents(test_data))

print("3. 최종 findings:")
print(run_detection(test_data, "https://example.com"))

print("4. 반복 스팸 탐지 결과:")
print(detect_repeated_spam(test_data))