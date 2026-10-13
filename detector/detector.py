
"""텍스트, 반복 스팸, 이미지 탐지를 통합 실행한다."""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import SCHEMA_VERSION
from .contracts import validate_inputs
from .text_detector import analyze_contents
from .spam_detector import detect_repeated_spam
from .image_detector import analyze_images
from .mapper import create_findings


def save_results(output, filename):
    """분석 결과를 JSON 파일로 저장한다."""

    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return str(path)


def run_detection(
    contents,
    entry_url,
    images=None,
    *,
    output_path=None,
):
    """크롤링 결과를 받아 모든 탐지 알고리즘을 실행한다."""

    # 1. 입력 데이터 검사
    validate_inputs(contents, images, entry_url)

    start_time = time.perf_counter()

    # 2. 텍스트 광고 탐지
    text_results = analyze_contents(contents)

    # 3. 반복 스팸 댓글 탐지
    spam_results = detect_repeated_spam(contents)

    # 4. 이미지 OCR 텍스트 탐지
    image_results, warnings = analyze_images(images or [])

    # 5. 모든 탐지 결과 통합
    all_results = (
        text_results
        + spam_results
        + image_results
    )

    # 6. 결과 형식 통일 및 중복 제거
    findings = create_findings(all_results)

    elapsed_ms = round(
        (time.perf_counter() - start_time) * 1000,
        2,
    )

    # 7. 최종 결과 생성
    output = {
        "schema_version": SCHEMA_VERSION,
        "target_url": entry_url,
        "findings": findings,
        "meta": {
            "analyzed_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "content_count": len(contents),
            "image_count": len(images or []),
            "finding_count": len(findings),
            "text_finding_count": len(text_results),
            "spam_finding_count": len(spam_results),
            "image_finding_count": len(image_results),
            "processing_time_ms": elapsed_ms,
            "score_kind": "heuristic",
            "warnings": warnings,
        },
    }

    # 8. 파일 저장이 요청된 경우에만 JSON 생성
    if output_path is not None:
        save_results(output, output_path)

    return output
