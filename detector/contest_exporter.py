
"""알고리즘 결과를 공모전 제출용 JSON 파일로 변환한다."""

import json
from pathlib import Path


OFFICIAL_TECHNIQUES = {
    "JAMO",
    "HOMOGLYPH",
    "TRANSPARENT",
    "OFFSCREEN",
}


def build_contest_results(algorithm_result):
    """내부 탐지 결과를 공식 결과와 추가 결과로 분리한다."""

    target_url = algorithm_result.get("target_url", "")
    findings = algorithm_result.get("findings", [])

    official_findings = []
    extra_findings = []

    for finding in findings:
        techniques = finding.get("techniques", [])
        matched_official = [
            technique
            for technique in techniques
            if technique in OFFICIAL_TECHNIQUES
        ]

        base = {
            "id": finding.get("id", ""),
            "url": finding.get("url", target_url),
            "location": finding.get("location", ""),
            "evidence": finding.get("evidence_text", ""),
            "category": finding.get("category", ""),
            "score": finding.get("score", 0),
        }

        if matched_official and finding.get("source_type") != "image":
            for technique in matched_official:
                official_findings.append({
                    **base,
                    "technique": technique,
                })
        else:
            extra_findings.append({
                **base,
                "technique": "ETC",
                "extra_finding": {
                    "techniques": techniques,
                    "source_type": finding.get(
                        "source_type", "text"
                    ),
                    "details": finding.get("details", {}),
                },
            })

    official_result = {
        "entry_url": target_url,
        "findings": official_findings,
    }

    extra_result = {
        "entry_url": target_url,
        "extra_findings": extra_findings,
    }

    return official_result, extra_result


def write_contest_results(algorithm_result, output_dir):
    """공모전 제출용 JSON 파일 두 개를 저장한다."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    official_result, extra_result = build_contest_results(
        algorithm_result
    )

    result_path = output_path / "result.json"
    extra_path = output_path / "result_extra.json"

    with result_path.open("w", encoding="utf-8") as file:
        json.dump(
            official_result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    with extra_path.open("w", encoding="utf-8") as file:
        json.dump(
            extra_result,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return {
        "result_path": str(result_path),
        "result_extra_path": str(extra_path),
        "official_count": len(official_result["findings"]),
        "extra_count": len(extra_result["extra_findings"]),
    }
