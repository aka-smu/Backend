
"""디텍터 기본 기능 테스트."""

import unittest

from detector import run_detection


class TestDetector(unittest.TestCase):

    def test_gambling_ad(self):
        """도박 광고가 탐지되는지 확인"""

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

        self.assertGreater(
            len(result["findings"]),
            0,
        )

    def test_loan_ad(self):
        """대출 광고가 탐지되는지 확인"""

        contents = [
            {
                "url": "https://example.com",
                "location": "comment_1",
                "text": "당일 대출 무직자 즉시 승인",
            }
        ]

        result = run_detection(
            contents=contents,
            entry_url="https://example.com",
        )

        self.assertGreater(
            len(result["findings"]),
            0,
        )

    def test_normal_text(self):
        """정상 문장은 탐지되지 않는지 확인"""

        contents = [
            {
                "url": "https://example.com",
                "location": "div.notice",
                "text": "안녕하세요. 공공기관 공지사항입니다.",
            }
        ]

        result = run_detection(
            contents=contents,
            entry_url="https://example.com",
        )

        self.assertEqual(
            len(result["findings"]),
            0,
        )


if __name__ == "__main__":
    unittest.main()
