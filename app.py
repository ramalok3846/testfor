import re
import urllib.parse
from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# 호랭이닷컴 기본 URL
BASE_URL = "https://www.horang2.com"
SEARCH_URL = "https://www.horang2.com/search"

# 요청 헤더 (웹 브라우저로 위장)
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def parse_query(user_query):
    """자연어 검색어에서 주요 키워드(연도, 학년, 월, 과목)를 추출"""
    keywords = []

    # 연도 추출 (예: 2024년, 24년)
    year_match = re.search(r"(\d{2,4})\s*년?", user_query)
    if year_match:
        year = year_match.group(1)
        if len(year) == 2:
            year = "20" + year
        keywords.append(year)

    # 학년 추출 (예: 고3, 고2, 고1)
    grade_match = re.search(r"(고[1-3]|중[1-3])", user_query)
    if grade_match:
        keywords.append(grade_match.group(1))

    # 월 추출 (예: 6월, 11월)
    month_match = re.search(r"(\d{1,2})\s*월", user_query)
    if month_match:
        keywords.append(f"{month_match.group(1)}월")

    # 과목 추출
    for subject in ["영어", "국어", "수학", "한국사", "탐구"]:
        if subject in user_query:
            keywords.append(subject)
            break

    # 추출된 키워드가 없으면 원본 검색어 사용
    return " ".join(keywords) if keywords else user_query


@app.route("/api/search", methods=["POST"])
def search():
    data = request.get_json() or {}
    raw_query = data.get("query", "")

    if not raw_query:
        return jsonify({"success": False, "error": "검색어를 입력해주세요."}), 400

    # 1. 자연어 검색어에서 정제된 검색 키워드 생성
    refined_query = parse_query(raw_query)

    try:
        # 2. 호랭이닷컴 검색 요청
        params = {"q": refined_query}
        response = requests.get(
            SEARCH_URL, headers=HEADERS, params=params, timeout=10
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # 3. 게시글 검색 결과 파싱
        # (호랭이닷컴 게시글 링크 요소 파싱)
        items = []
        post_links = soup.select(".search_list a, .board_list a, article a")

        for link in post_links[:5]:  # 상위 5개 결과 분석
            href = link.get("href", "")
            title = link.get_text(strip=True)

            if not href or len(title) < 3:
                continue

            full_post_url = (
                href if href.startswith("http") else BASE_URL + href
            )

            # 상세 게시글 페이지 접속하여 다운로드 파일(PDF, MP3 등) 추출
            post_res = requests.get(
                full_post_url, headers=HEADERS, timeout=8
            )
            post_soup = BeautifulSoup(post_res.text, "html.parser")

            files = {"pdf": [], "script": [], "audio": []}

            # 게시글 내 첨부파일/다운로드 링크 수집
            file_links = post_soup.select(
                "a[href*='.pdf'], a[href*='.mp3'], a[href*='.hwp'], a[href*='download']"
            )

            for file_link in file_links:
                file_url = file_link.get("href", "")
                file_name = file_link.get_text(strip=True) or "다운로드"

                if not file_url.startswith("http"):
                    file_url = BASE_URL + file_url

                # 파일 유형별 분류
                if ".mp3" in file_url.lower() or "듣기" in file_name:
                    files["audio"].append(
                        {"name": file_name, "url": file_url}
                    )
                elif "대본" in file_name or "script" in file_name.lower():
                    files["script"].append(
                        {"name": file_name, "url": file_url}
                    )
                else:
                    files["pdf"].append({"name": file_name, "url": file_url})

            items.append(
                {
                    "title": title,
                    "post_url": full_post_url,
                    "files": files,
                }
            )

        return jsonify(
            {
                "success": True,
                "query": raw_query,
                "refined_query": refined_query,
                "results": items,
            }
        )

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    print("🚀 Pydroid 3 Flask 백엔드 서버 시작 (http://localhost:5000)")
    app.run(host="0.0.0.0", port=5000, debug=True)