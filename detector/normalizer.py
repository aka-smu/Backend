"""광고 탐지를 방해하는 자모 분리와 유사 문자 등을 정규화한다."""

import re
import unicodedata


# 자주 사용되는 유사 문자 변환
HOMOGLYPH_MAP = {
    "а": "a",  # 키릴 문자
    "е": "e",
    "о": "o",
    "р": "p",
    "с": "c",
    "х": "x",
    "і": "i",
    "Α": "A",  # 그리스 문자
    "Β": "B",
    "Ε": "E",
    "Ο": "O",
    "Ρ": "P",
}


def normalize_unicode(text):
    """전각 문자 등 유니코드 표현을 통일한다."""
    return unicodedata.normalize("NFKC", str(text or ""))


def normalize_homoglyph(text):
    """일반 문자와 비슷하게 생긴 문자를 변환한다."""
    text = normalize_unicode(text)

    return "".join(
        HOMOGLYPH_MAP.get(char, char)
        for char in text
    )


def combine_korean_jamo(text):
    """분리된 한글 자모를 가능한 범위에서 완성형으로 결합한다."""
    text = normalize_unicode(text)

    # 호환 자모를 초성·중성·종성 조합으로 변환
    CHOSEONG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
    JUNGSEONG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
    JONGSEONG = "ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"

    result = []
    i = 0

    while i < len(text):
        if (
            i + 1 < len(text)
            and text[i] in CHOSEONG
            and text[i + 1] in JUNGSEONG
        ):
            initial = CHOSEONG.index(text[i])
            medial = JUNGSEONG.index(text[i + 1])
            final = 0
            consumed = 2

            if (
                i + 2 < len(text)
                and text[i + 2] in JONGSEONG
            ):
                # 다음 글자가 모음으로 시작하면 받침으로 사용하지 않는다.
                if not (
                    i + 3 < len(text)
                    and text[i + 3] in JUNGSEONG
                ):
                    final = JONGSEONG.index(text[i + 2]) + 1
                    consumed = 3

            syllable = chr(
                0xAC00 + (initial * 21 + medial) * 28 + final
            )

            result.append(syllable)
            i += consumed
        else:
            result.append(text[i])
            i += 1

    return "".join(result)


def compact_text(text):
    """공백과 일부 구분 문자를 제거해 우회 표기를 비교한다."""
    return re.sub(
        r"[\s\-_.,·•]+",
        "",
        str(text or "")
    )


def normalize_text(text):
    """탐지에 사용할 정규화 텍스트를 생성한다."""
    text = normalize_homoglyph(text)
    text = combine_korean_jamo(text)
    return compact_text(text).lower()


def detect_jamo(text):
    """자모 결합 과정에서 표현이 바뀌었는지 확인한다."""
    original = normalize_unicode(text)
    combined = combine_korean_jamo(original)

    return original != combined


def detect_homoglyph(text):
    """유사 문자 변환 과정에서 표현이 바뀌었는지 확인한다."""
    original = normalize_unicode(text)
    converted = normalize_homoglyph(original)

    return original != converted


def normalized_provenance(text):
    """원문과 정규화 결과, 사용된 변환 기술을 반환한다."""
    original = str(text or "")
    techniques = []

    if detect_jamo(original):
        techniques.append("JAMO")

    if detect_homoglyph(original):
        techniques.append("HOMOGLYPH")

    return {
        "original": original,
        "normalized": normalize_text(original),
        "techniques": techniques,
    }