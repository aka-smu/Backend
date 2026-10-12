from detector import (
    detect_ad,
    analyze_content,
    analyze_contents,
    save_results,
    detect_jamo,
    create_findings,
    run_detection,
    normalize_homoglyph,
    detect_homoglyph,
    detect_transparent,
    detect_offscreen
)

test_cases = [
    ("오늘 학교에서 수업을 들었습니다.", False),

    ("경찰이 불법 카지노를 단속했습니다.", False),

    ("카지노 첫충 가입머니 지급! 텔레그램 문의", True),

    ("무직자 즉시 승인 당일 대출 가능합니다.", True),

    ("예약 문의는 010-1234-5678로 연락주세요.", False),

    ("카지노 문의 010-1234-5678", True),

    ("학교 홈페이지는 https://school.com 입니다.", False),

    ("카지노 첫충! 텔레그램 문의 https://abc.com 010-1111-2222", True),

    ("카 지 노 첫 충 가입머니 지급", True),

    ("카.지.노 첫.충 텔레그램 문의", True),

    ("카-지-노 첫-충 이벤트", True),

    ("ㅋㅏㅈㅣㄴㅗ 첫충 가입머니 지급", True),
    
    ("ㅌㅗㅌㅗ 첫충 텔레그램 문의", True)

    
]


for text, expected in test_cases:

    result = detect_ad(text)

    actual = result["detected"]

    print("=" * 50)
    print("입력:", text)
    print("예상:", expected)
    print("실제:", actual)

    if actual == expected:
        print("테스트 성공")
    else:
        print("테스트 실패")

print("\n===== 필수 4종 통합 테스트 =====")

crawler_contents = [
    # 1. JAMO
    {
        "url": "https://example.com/post/1",
        "text": "ㅋㅏㅈㅣㄴㅗ 첫충 가입머니",
        "location": "div.jamo-ad",
        "element": "div",
        "style": ""
    },

    # 2. TRANSPARENT
    {
        "url": "https://example.com/post/2",
        "text": "카지노 첫충 가입머니",
        "location": "div.transparent-ad",
        "element": "div",
        "style": "opacity: 0;"
    },

    # 3. OFFSCREEN
    {
        "url": "https://example.com/post/3",
        "text": "무직자 즉시 승인 당일 대출",
        "location": "div.offscreen-ad",
        "element": "div",
        "style": "position: absolute; left: -9999px;"
    },

    # 4. 정상
    {
        "url": "https://example.com/post/4",
        "text": "오늘 학교에서 수업을 들었습니다.",
        "location": "div.normal",
        "element": "div",
        "style": "font-size: 16px;"
    }
]

findings = run_detection(
    contents=crawler_contents,
    entry_url="https://example.com"
)

for finding in findings:
    print(finding)
