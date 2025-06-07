# main.py
import os
import re
import math
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from bs4 import BeautifulSoup

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 환경 변수 또는 .env로 관리 권장
NAVER_CLIENT_ID = 'EcKdwVkFISXAtIMgPig4'
NAVER_CLIENT_SECRET = 'IaGsbrRSnq'
OPENAI_API_KEY = "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"

# ----- 1. 키워드 입력 (첫 페이지) -----
@app.get("/", response_class=HTMLResponse)
def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "keyword": ""})

@app.post("/", response_class=HTMLResponse)
def post_index(request: Request, keyword: str = Form(...)):
    if not keyword.strip():
        return templates.TemplateResponse("index.html", {"request": request, "keyword": ""})
    resp = RedirectResponse(f"/results?keyword={keyword}", status_code=302)
    return resp

# ----- 2. 네이버 카페 크롤링/ChatGPT SEO 제목 추천 -----
@app.get("/results", response_class=HTMLResponse)
def results(request: Request, keyword: str = "", tab: str = "cafe", page: int = 1):
    if not keyword.strip():
        return templates.TemplateResponse("results.html", {"request": request, "keyword": "", "tab": tab, "cafe_results": [], "seo_titles": [], "user_title": "", "post_result": ""})

    # 1. 네이버 카페 검색 크롤링
    url = f"https://section.cafe.naver.com/ca-fe/home/search/articles?q={keyword}"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")
    items = []
    today = datetime.today()
    one_year_ago = today - timedelta(days=365)
    for idx, item in enumerate(soup.select("ul.list_article > li")):
        # 날짜 추출 (포맷 맞게 수정 필요)
        try:
            date_text = item.select_one(".txt_date").text.strip()
            # 날짜 변환
            post_date = datetime.strptime(date_text, "%Y.%m.%d")
            if post_date < one_year_ago:
                continue
        except:
            continue

        title = item.select_one(".article_tit").text.strip() if item.select_one(".article_tit") else ""
        summary = item.select_one(".article_cont").text.strip() if item.select_one(".article_cont") else ""
        items.append({"no": idx + 1, "title": title, "summary": summary, "date": date_text})
        if len(items) >= 100:  # 최대 100개만 추출
            break

    total_count = len(items)
    start = (page - 1) * 20
    end = start + 20
    paged_items = items[start:end]

    # 2. ChatGPT SEO 제목 추천 (탭2)
    seo_titles = []
    if tab == "seo" and paged_items:
        text_block = ""
        for post in paged_items[:20]:
            text_block += f"제목: {post['title']}\n요약: {post['summary']}\n"
        prompt = f"""
아래는 최근 1년간 네이버 카페에 올라온 '{keyword}' 관련 게시글 제목과 요약입니다.
이 게시글들의 작성 의도를 파악하고, SEO에 최적화된 건강 블로그용 포스팅 제목 10개를 한글로 추천해줘.
각 제목은 클릭을 유도하는 스타일로 작성해줘.

{text_block}
        """
        openai_resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 512
            },
            timeout=60
        )
        result = openai_resp.json()
        raw = result["choices"][0]["message"]["content"]
        # 줄바꿈 기준 분리
        seo_titles = [x for x in re.split(r"[\n\-]+", raw) if x.strip()][:10]

    return templates.TemplateResponse("results.html", {
        "request": request,
        "keyword": keyword,
        "tab": tab,
        "cafe_results": paged_items,
        "total_count": total_count,
        "page": page,
        "total_pages": math.ceil(total_count / 20),
        "seo_titles": seo_titles,
        "user_title": "",
        "post_result": ""
    })

# ----- 2-2. 직접 포스팅 제목으로 ChatGPT 포스팅 생성 -----
@app.post("/generate_post", response_class=HTMLResponse)
def generate_post(request: Request, keyword: str = Form(...), user_title: str = Form(...)):
    # ChatGPT Prompt 구성
    post_prompt = f"""
[포스팅 제목] {user_title}
아래 조건에 맞춰 건강 블로그 포스팅글을 작성해줘.

1. 제목의 의도/목적에 맞게 글 전체를 작성
2. 공신력 있는 기관, 논문, 칼럼을 참고하되 웹상에 없는 고유한 내용으로 작성
3. H2, H3 태그로 서브제목 구분
4. '{keyword}' 질병/통증을 방치했을 때 위험성 (500자)
5. '{keyword}' 실제 사례 공감 내용 (500자)
6. 주요 증상 설명 (500자)
7. 극복/치료/예방법 (500자)
8. 전체 단어 수 1,000개 이상, 총 5,000자 이상, Paraphrasing 적극 사용

반드시 한글로 작성, 블로그 SEO 최적화 스타일로 부탁해.
"""
    openai_resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": post_prompt}],
            "max_tokens": 4096
        },
        timeout=120
    )
    result = openai_resp.json()
    post_content = result["choices"][0]["message"]["content"]

    # 결과 페이지로 전달
    return templates.TemplateResponse("results.html", {
        "request": request,
        "keyword": keyword,
        "tab": "seo",
        "cafe_results": [],
        "total_count": 0,
        "page": 1,
        "total_pages": 1,
        "seo_titles": [],
        "user_title": user_title,
        "post_result": post_content
    })

# ----- 3. 네이버 뉴스 API -----
@app.get("/news", response_class=HTMLResponse)
def news(request: Request, keyword: str = "", page: int = 1):
    if not keyword.strip():
        return templates.TemplateResponse("news.html", {"request": request, "keyword": "", "news_items": [], "total_count": 0, "page": 1, "total_pages": 1})

    start = (page - 1) * 20 + 1
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {
        "query": keyword,
        "display": 20,
        "start": start,
        "sort": "date"
    }
    res = requests.get("https://openapi.naver.com/v1/search/news.json", headers=headers, params=params)
    data = res.json()
    # 최근 1년 데이터만
    today = datetime.today()
    one_year_ago = today - timedelta(days=365)
    news_items = []
    for idx, item in enumerate(data.get("items", [])):
        # pubDate: 'Fri, 07 Jun 2024 10:13:00 +0900'
        try:
            pub_date = datetime.strptime(item['pubDate'], '%a, %d %b %Y %H:%M:%S %z')
            if pub_date < one_year_ago:
                continue
        except:
            continue
        news_items.append({
            "no": idx + 1 + start - 1,
            "title": item['title'],
            "link": item['link'],
            "desc": item['description'],
            "date": pub_date.strftime('%Y-%m-%d')
        })

    total_count = int(data.get('total', 0))
    return templates.TemplateResponse("news.html", {
        "request": request,
        "keyword": keyword,
        "news_items": news_items,
        "total_count": total_count,
        "page": page,
        "total_pages": math.ceil(total_count / 20)
    })

# ----- 정적 파일 (CSS 등) -----
app.mount("/static", StaticFiles(directory="static"), name="static")
