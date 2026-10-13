"""외부에서는 from detector import run_detection 으로 사용한다."""

from .detector import run_detection, save_results
from .text_detector import detect_ad, analyze_content, analyze_contents
from .mapper import create_findings
from .css_detector import detect_transparent, detect_offscreen
from .normalizer import (
    normalize_homoglyph,
    normalize_text,
    combine_korean_jamo,
    detect_jamo,
    detect_homoglyph,
)

__all__ = [
    "run_detection",
    "save_results",
    "detect_ad",
    "analyze_content",
    "analyze_contents",
    "create_findings",
    "detect_transparent",
    "detect_offscreen",
    "normalize_homoglyph",
    "normalize_text",
    "combine_korean_jamo",
    "detect_jamo",
    "detect_homoglyph",
]