"""크롤러 입력과 탐지 알고리즘 출력의 데이터 형식을 정의한다."""

from typing import Any, Dict, List, Optional, TypedDict


class CrawlContent(TypedDict, total=False):
    """크롤러가 수집한 텍스트 콘텐츠."""

    url: str
    location: str
    text: str
    style: Dict[str, Any]
    source_type: str
    frame_id: str
    frame_url: str
    frame_path: str
    comment_scope: str


class ImageContent(TypedDict, total=False):
    """크롤러가 수집한 이미지 정보."""

    url: str
    location: str
    image_url: str
    ocr_text: str
    frame_id: str
    frame_url: str
    frame_path: str


class Finding(TypedDict, total=False):
    """탐지된 광고 한 건의 결과."""

    id: str
    category: str
    techniques: List[str]
    score: int
    raw_score: int
    evidence_text: str
    url: str
    location: str
    source_type: str
    details: Dict[str, Any]


class AlgorithmResult(TypedDict):
    """전체 탐지 알고리즘의 반환 결과."""

    schema_version: str
    target_url: str
    findings: List[Finding]
    meta: Dict[str, Any]


def validate_inputs(
    contents: List[Dict[str, Any]],
    images: Optional[List[Dict[str, Any]]],
    entry_url: str,
) -> None:
    """탐지 실행 전에 입력 데이터의 기본 형식을 확인한다."""

    if not isinstance(entry_url, str) or not entry_url.strip():
        raise ValueError("entry_url은 비어 있지 않은 문자열이어야 합니다.")

    if not isinstance(contents, list):
        raise TypeError("contents는 리스트여야 합니다.")

    for index, content in enumerate(contents):
        if not isinstance(content, dict):
            raise TypeError(
                f"contents[{index}]는 딕셔너리여야 합니다."
            )

        for field in ("url", "location"):
            if not isinstance(content.get(field), str):
                raise ValueError(
                    f"contents[{index}].{field}는 문자열이어야 합니다."
                )

        if "text" in content and not isinstance(content["text"], str):
            raise TypeError(
                f"contents[{index}].text는 문자열이어야 합니다."
            )

        if "style" in content and not isinstance(content["style"], dict):
            raise TypeError(
                f"contents[{index}].style은 딕셔너리여야 합니다."
            )

    if images is None:
        return

    if not isinstance(images, list):
        raise TypeError("images는 리스트여야 합니다.")

    for index, image in enumerate(images):
        if not isinstance(image, dict):
            raise TypeError(
                f"images[{index}]는 딕셔너리여야 합니다."
            )

        for field in ("url", "location"):
            if not isinstance(image.get(field), str):
                raise ValueError(
                    f"images[{index}].{field}는 문자열이어야 합니다."
                )

        if "ocr_text" in image and not isinstance(image["ocr_text"], str):
            raise TypeError(
                f"images[{index}].ocr_text는 문자열이어야 합니다."
            )

        