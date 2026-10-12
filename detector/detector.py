from bs4 import BeautifulSoup #Beautifulsoup: HTML을 Python이 분석하기 쉽게 만들어주는 도구

gambling_keywords = ["카지노", "도박", "토토", "배팅"]
loan_keywords = ["대출", "무직자", "즉시 승인", "당일 대출"]

def extract_text_from_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()

def detect_ad(text):

    for keyword in gambling_keywords:
        if keyword in text:
            return "도박 광고 의심"

    for keyword in loan_keywords:
        if keyword in text:
            return "불법 금융 광고 의심"

    return "정상"


#=============================================================
# 1. TRANSPARENT 탐지 (opacity:0으로 숨긴 요소 탐지- 투명 요소 탐지)

def detect_transparent(html):
    soup = BeautifulSoup(html, "html.parser")

    results = []

    for element in soup.find_all(style=True): # style 속성이 있는 모든 요소를 찾음
        style = element.get("style", "").replace(" ", "").lower()

        if "opacity:0" in style:
            results.append({
                "type": "TRANSPARENT",
                "reason": "opacity:0 발견",
                "text": element.get_text(strip=True)
            })

    return results


#=============================================================
# 2.OFFSCREEN 탐지 (화면 바깥 위치로 밀어내서 숨긴 요소 탐지)

def detect_offscreen(html):
    soup = BeautifulSoup(html, "html.parser")

    results = []

    for element in soup.find_all(style=True): # style 속성이 있는 모든 태그 탐색
        style = element.get("style", "").replace(" ", "").lower()

        # left:-9999px 또는 top:-9999px 같이 음수 좌표로 화면 밖에 배치를 시도했는지 확인
        if "left:-" in style or "top:-" in style:
            # 어떤 축을 이용해 화면 밖으로 밀어냈는지 근거 남기기
            if "left:-" in style:
                reason_msg = "left 음수 좌표 발견"
            else:
                reason_msg = "top 음수 좌표 발견"

            results.append({
                "type": "OFFSCREEN",
                "reason": reason_msg,
                "text": element.get_text(strip=True)
            })

    return results


#=============================================================
# 3. HIDDEN 탐지 (display:none, visibility:hidden, 크기 0 요소 탐지)

def detect_hidden(html):
    soup = BeautifulSoup(html, "html.parser")

    results = []

    for element in soup.find_all(style=True): # style 속성이 있는 모든 태그 탐색
        style = element.get("style", "").replace(" ", "").lower()

        # display:none 또는 visibility:hidden 속성 탐지
        if "display:none" in style:
            results.append({
                "type": "HIDDEN",
                "reason": "display:none 발견",
                "text": element.get_text(strip=True)
            })

        if "visibility:hidden" in style:
            results.append({
                "type": "HIDDEN",
                "reason": "visibility:hidden 발견",
                "text": element.get_text(strip=True)
            })

        # 너비(width)나 높이(height)를 0으로 만들어 숨긴 경우 탐지
        if "width:0" in style or "height:0" in style:
            results.append({
                "type": "HIDDEN",
                "reason": "크기 0(width/height) 발견",
                "text": element.get_text(strip=True)
            })

    return results


#=============================================================
# 4. COLOR_MATCH 탐지 (글자색과 배경색을 동일하게 만들어 숨긴 요소 탐지)

def detect_color_match(html):
    soup = BeautifulSoup(html, "html.parser")

    results = []

    for element in soup.find_all(style=True): # style 속성이 있는 모든 태그 탐색
        style = element.get("style", "").replace(" ", "").lower()

        # style 속성 안에서 color:와 background: (또는 background-color:) 구문 추출
        # 예: style="color:white; background:white;"
        if "color:" in style and ("background:" in style or "background-color:" in style):
            
            # 간단하게 color와 background의 값이 같은지 확인
            # (가장 흔한 패턴: color:white; background:white; 또는 color:#fff; background:#fff;)
            if "color:white" in style and "background:white" in style:
                results.append({
                    "type": "COLOR_MATCH",
                    "reason": "글자색과 배경색 동일(white/white) 발견",
                    "text": element.get_text(strip=True)
                })
            elif "color:#fff" in style and "background:#fff" in style:
                results.append({
                    "type": "COLOR_MATCH",
                    "reason": "글자색과 배경색 동일(#fff/#fff) 발견",
                    "text": element.get_text(strip=True)
                })

    return results


#=============================================================
# 5. 여러 탐지 기능을 하나로 합치기 (통합 함수)

def detect_all_elements(html):
    """
    투명, 오프스크린, 숨김, 색상 숨김 등 
    모든 탐지 기능을 한 번에 실행하고 결과를 합쳐서 반환합니다.
    """
    total_results = []

    # 1. TRANSPARENT 탐지 결과 추가
    total_results.extend(detect_transparent(html))

    # 2. OFFSCREEN 탐지 결과 추가
    total_results.extend(detect_offscreen(html))

    # 3. HIDDEN 탐지 결과 추가
    total_results.extend(detect_hidden(html))

    # 4. COLOR_MATCH 탐지 결과 추가
    total_results.extend(detect_color_match(html))

    return total_results


#=============================================================
# 6·7번. 실제 게시판 HTML을 대상으로 한 최종 통합 테스트 실행

if __name__ == "__main__":
    # 실제 웹사이트의 게시글 구조를 모사한 테스트 HTML
    real_board_html = """
    <html>
        <body>
            <div class="post-header">
                <h2>2026년도 상반기 주민 공청회 안내</h2>
                <p>작성자: 관리자 | 조회수: 152</p>
            </div>
            
            <div class="post-body">
                <p>주민 여러분 안녕하십니까. 다가오는 상반기 공청회 일정을 안내해 드립니다.</p>
                <p>많은 참여 부탁드립니다.</p>
                
                <!-- 숨겨진 불법 광고 요소들 (숨김 방식별 테스트) -->
                <div style="display:none">카지노 신규가입 대박 이벤트 10만 원 즉시 지급</div>
                <div style="position:absolute; left:-9999px">당일 무직자 대출 즉시 승인 소액 대출 문의</div>
                <div style="opacity:0">실시간 스포츠 토토 배팅 사이트 주소 안내</div>
                <div style="color:white; background:white;">비밀 오픈채팅 대출 상담 환영</div>
            </div>
        </body>
    </html>
    """

    print("=== 6·7번: 실제 게시판 HTML 통합 탐지 및 근거 출력 테스트 ===")
    
    # 5번에서 만든 통합 탐지 함수 실행
    all_detections = detect_all_elements(real_board_html)

    # 결과가 어떻게 나오는지 상세히 출력
    for idx, item in enumerate(all_detections, start=1):
        print(f"\n[탐지 번호 {idx}]")
        print(f" - 탐지 유형 (Type) : {item['type']}")
        print(f" - 탐지 근거 (Reason) : {item['reason']}") # 6번 요구사항: 왜 탐지됐는지 명확한 근거
        print(f" - 숨겨진 텍스트  : {item['text']}")


#=============================================================
# 8·9번. 크롤러 연동 및 텍스트 탐지(detect_ad) 결과 최종 결합 함수

def analyze_final_result(main_html, iframe_html_list=None):
    """
    크롤러가 넘겨준 메인 HTML과 iframe HTML들을 분석하고,
    CSS 숨김 탐지 결과와 텍스트 키워드 분석(detect_ad) 결과를 최종 결합합니다.
    """
    all_detections = []

    # 1) 메인 페이지 분석 실행
    main_results = detect_all_elements(main_html)
    for item in main_results:
        item["is_iframe"] = False
        all_detections.append(item)

    # 2) 크롤러가 수집한 iframe 내부 HTML 분석 (8번 크롤러 연동)
    if iframe_html_list:
        for idx, iframe_html in enumerate(iframe_html_list, start=1):
            iframe_results = detect_all_elements(iframe_html)
            for item in iframe_results:
                item["is_iframe"] = True
                item["reason"] = f"[iframe #{idx}] " + item["reason"] # 어디서 발견됐는지 표시
                all_detections.append(item)

    # 3) 텍스트 탐지 결과와 CSS 탐지 결과 합치기 (9번 요구사항)
    final_reports = []
    for item in all_detections:
        # 파일 상단에 있는 detect_ad 함수를 호출해 불법 키워드 검사
        ad_status = detect_ad(item["text"])
        
        final_reports.append({
            "ad_keyword_status": ad_status,      # 예: "도박 광고 의심" 또는 "불법 금융 광고 의심"
            "detection_type": item["type"],      # 예: "TRANSPARENT", "OFFSCREEN" 등
            "reason": item["reason"],            # 예: "opacity:0 발견"
            "text": item["text"],                # 숨겨져 있던 실제 텍스트
            "is_iframe": item["is_iframe"]       # iframe 여부
        })

    return final_reports