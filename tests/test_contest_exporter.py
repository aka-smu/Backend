
"""공모전 결과 JSON 저장 기능 테스트."""

import json
import tempfile
import unittest
from pathlib import Path

from detector import run_detection
from detector.contest_exporter import write_contest_results


class TestContestExporter(unittest.TestCase):

    def test_export_json_files(self):
        """결과 JSON 파일 2개가 생성되는지 확인"""

        contents = [
            {
                "url": "https://example.com",
                "location": "div.ad",
                "text": "카지노 첫충 가입머니 지급",
            }
        ]

        result = run_detection(
            contents=contents,
            entry_url="https://example.com",
        )

        with tempfile.TemporaryDirectory() as temp_dir:

            write_contest_results(
                result,
                output_dir=temp_dir,
            )

            result_path = Path(temp_dir) / "result.json"
            extra_path = Path(temp_dir) / "result_extra.json"

            self.assertTrue(result_path.exists())
            self.assertTrue(extra_path.exists())

            with result_path.open(
                "r", encoding="utf-8"
            ) as file:
                official_result = json.load(file)

            with extra_path.open(
                "r", encoding="utf-8"
            ) as file:
                extra_result = json.load(file)

            self.assertIsInstance(official_result, (dict, list))
            self.assertIsInstance(extra_result, (dict, list))


if __name__ == "__main__":
    unittest.main()
