
"""크롤링 결과 JSON을 읽어 디텍터를 실행하는 예제."""

import argparse
import json
from pathlib import Path

from detector import run_detection
from detector.contest_exporter import write_contest_results


def main():
    parser = argparse.ArgumentParser(
        description="불법광고 디텍터 실행 예제"
    )

    parser.add_argument(
        "--input",
        default="examples/crawl_input.json",
        help="크롤러 입력 JSON 파일 경로",
    )

    parser.add_argument(
        "--output",
        default="output/algorithm_result.json",
        help="알고리즘 결과 저장 경로",
    )

    parser.add_argument(
        "--contest-output-dir",
        default="output",
        help="공모전 제출용 JSON 저장 폴더",
    )

    args = parser.parse_args()

    # 1. 크롤러 결과 JSON 읽기
    input_path = Path(args.input)

    with input_path.open("r", encoding="utf-8") as file:
        crawl_data = json.load(file)

    # 2. 디텍터 실행
    result = run_detection(
        contents=crawl_data["contents"],
        entry_url=crawl_data["entry_url"],
        images=crawl_data.get("images", []),
        output_path=args.output,
    )

    # 3. 공모전 제출용 JSON 생성
    exports = write_contest_results(
        result,
        output_dir=args.contest_output_dir,
    )

    # 4. 실행 결과 출력
    print("=== 디텍터 실행 완료 ===")
    print("전체 탐지 건수:", len(result["findings"]))
    print("알고리즘 결과:", args.output)
    print("공식 결과:", exports["result_path"])
    print("추가 결과:", exports["result_extra_path"])


if __name__ == "__main__":
    main()
