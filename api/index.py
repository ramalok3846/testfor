import urllib.parse
from flask import Flask, jsonify, request
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

BASE_URL = "https://www.horang2.com"
SEARCH_URL = "https://www.horang2.com/search"

# 차단 우회용 실제 브라우저 헤더 설정
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}


@app.route("/api/search", methods=["POST", "OPTIONS"])
def search():
    # CORS 허용 헤더 설정
    if request.method == "OPTIONS":
        response = jsonify({"status": "ok"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add(
            "Access-Control-Allow-Headers", "Content-Type"
        )
        response.headers.add("Access-Control-Allow-Methods", "POST")
        return response

    data = request.get_json() or {}
    raw_query = data.get("query", "")

    if not raw_query:
        res = jsonify(
            {"success": False, "error": "검색어를 입력해주세요."}
        )
        res.headers.add("Access-Control-Allow-Origin", "*")
        return res, 400

    try:
        params = {"q": raw_query}
        response = requests.get(
            SEARCH_URL, headers=HEADERS, params=params, timeout=10
        )

        soup = BeautifulSoup(response.text, "html.parser")
        items = []

        post_links = soup.select(
            "a[href*='board'], a[href*='article'], a[href*='post'], a[href*='view']"
        )

        for link in post_links[:5]:
            href = link.get("href", "")
            title = link.get_text(strip=True) or raw_query
            if not href:
                continue

            full_post_url = (
                href if href.startswith("http") else BASE_URL + href
            )

            try:
                post_res = requests.get(
                    full_post_url, headers=HEADERS, timeout=8
                )
                post_soup = BeautifulSoup(post_res.text, "html.parser")

                files = {"pdf": [], "script": [], "audio": []}
                file_links = post_soup.select("a[href]")

                for f in file_links:
                    file_url = f.get("href", "")
                    file_name = f.get_text(strip=True) or "다운로드"
                    if not file_url.startswith("http"):
                        file_url = BASE_URL + file_url

                    lower_url = file_url.lower()
                    lower_name = file_name.lower()

                    if (
                        ".mp3" in lower_url
                        or "듣기" in lower_name
                        or "음원" in lower_name
                    ):
                        files["audio"].append(
                            {"name": file_name, "url": file_url}
                        )
                    elif (
                        "대본" in lower_name
                        or "script" in lower_name
                        or ".txt" in lower_url
                    ):
                        files["script"].append(
                            {"name": file_name, "url": file_url}
                        )
                    elif (
                        ".pdf" in lower_url
                        or ".hwp" in lower_url
                        or "문제" in lower_name
                        or "정답" in lower_name
                    ):
                        files["pdf"].append(
                            {"name": file_name, "url": file_url}
                        )

                items.append(
                    {
                        "title": title,
                        "post_url": full_post_url,
                        "files": files,
                    }
                )
            except Exception:
                continue

        res = jsonify(
            {"success": True, "query": raw_query, "results": items}
        )
        res.headers.add("Access-Control-Allow-Origin", "*")
        return res

    except Exception as e:
        res = jsonify({"success": False, "error": str(e)})
        res.headers.add("Access-Control-Allow-Origin", "*")
        return res, 500
