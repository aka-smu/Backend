from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import sys
import os

# detector 폴더를 불러올 수 있도록 경로 추가
sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)

from detector.detector import detect_ad

visited = set()


def crawl(url):

    if url in visited:
        return

    visited.add(url)

    print("방문:", url)

    # 1. URL에 접속해서 HTML 받아오기
    response = requests.get(url)

    # 2. HTML 분석하기
    soup = BeautifulSoup(response.text, "html.parser")

    # 3. 페이지 안의 댓글 찾기
    comments = soup.find_all(class_ = "comment")

    print("=== 불법 광고 탐지 결과 ===")

    for comment in comments:

        text = comment.get_text(strip=True)

        result = detect_ad(text)

        print()
        print("내용:", text)
        print("판정:", result)

    # 4. 페이지 안의 링크 찾기
    links = soup.find_all("a")

    for link in links:
        href = link.get("href")

        
        full_url = urljoin(url, href)

        
        print("발견", full_url)

        #재귀호출
        crawl(full_url)

start_url = "http://127.0.0.1:5500/test_site/index.html"

crawl(start_url)