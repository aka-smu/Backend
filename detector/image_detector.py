"""이미지에서 추출된 OCR 텍스트를 분석하여 광고를 탐지한다."""

from .text_detector import detect_ad
from .normalizer import normalized_provenance


def analyze_image(image):
    """이미지 한 건의 OCR 텍스트를 분석한다."""

    ocr_text = str(image.get("ocr_text") or "").strip()

    # OCR 결과가 없으면 분석할 수 없다.
    if not ocr_text:
        return None

    result = detect_ad(ocr_text)

    if not result["detected"]:
        return None

    provenance = normalized_provenance(ocr_text)

    techniques = ["IMAGE_TEXT"]

    for technique in provenance["techniques"]:
        if technique not in techniques:
            techniques.append(technique)

    return {
        "url": image.get("url", ""),
        "location": image.get("location", ""),
        "text": ocr_text,
        "category": result["category"],
        "score": result["score"],
        "raw_score": result["raw_score"],
        "matched_keywords": result["matched_keywords"],
        "evidence": result["evidence"],
        "techniques": techniques,
        "source_type": "image",
        "frame_id": image.get("frame_id"),
        "frame_url": image.get("frame_url"),
        "frame_path": image.get("frame_path"),
        "details": {
            "image_url": image.get("image_url", ""),
            "normalized_text": provenance["normalized"],
        },
    }


def analyze_images(images):
    """여러 이미지의 OCR 텍스트를 분석한다."""

    results = []
    warnings = []

    for index, image in enumerate(images or []):
        ocr_text = str(image.get("ocr_text") or "").strip()

        if not ocr_text:
            warnings.append({
                "code": "IMAGE_OCR_UNAVAILABLE",
                "image_index": index,
                "image_url": image.get("image_url", ""),
                "message": "OCR 텍스트가 없어 이미지 분석을 건너뛰었습니다.",
            })
            continue

        result = analyze_image(image)

        if result is not None:
            results.append(result)

    return results, warnings