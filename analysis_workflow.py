
"""크롤러와 디텍터를 연결하고 분석 결과를 저장한다."""

import time
from pathlib import Path

from detector import run_detection
from detector.contest_exporter import write_contest_results


def run_analysis(
    entry_url,
    crawl,
    output_dir,
):
    """크롤링부터 광고 탐지, 결과 저장까지 실행한다."""

    start_time = time.perf_counter()

    # 1. 크롤러 실행
    crawl_result = crawl(entry_url)

    if not isinstance(crawl_result, dict):
        raise TypeError(
            "크롤러 결과는 딕셔너리여야 합니다."
        )

    contents = crawl_result.get("contents")

    if not isinstance(contents, list):
        raise ValueError(
            "크롤러 결과에 contents 리스트가 필요합니다."
        )

    images = crawl_result.get("images", [])

    # 2. 결과 저장 폴더 생성
    output_path = Path(output_dir)
    output_path.mkdir(
        parents=True,
        exist_ok=True,
    )

    # 3. 디텍터 실행
    algorithm_result = run_detection(
        contents=contents,
        entry_url=entry_url,
        images=images,
        output_path=output_path / "algorithm_result.json",
    )

    # 4. 공모전 제출용 JSON 생성
    exports = write_contest_results(
        algorithm_result,
        output_dir=output_path,
    )

    # 5. 전체 소요 시간 계산
    elapsed_ms = round(
        (time.perf_counter() - start_time) * 1000,
        2,
    )

    return {
        "algorithm_result": algorithm_result,
        "exports": exports,
        "total_processing_time_ms": elapsed_ms,
    }
