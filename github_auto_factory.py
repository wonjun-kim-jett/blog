import os
import json
import requests
import urllib.parse
import xml.etree.ElementTree as ET
from google import genai
import datetime
import subprocess
from dotenv import load_dotenv

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
load_dotenv()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)
REPO_DIR = os.path.dirname(os.path.abspath(__file__))
POSTS_DIR = os.path.join(REPO_DIR, "_posts")
IMAGES_DIR = os.path.join(REPO_DIR, "assets", "images")

os.makedirs(POSTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# ==========================================
# 📊 1단계: 실시간 트렌드 스크래핑 (구글 뉴스 RSS)
# ==========================================
def fetch_realtime_trends(language="Korean"):
    print(f"📡 [1단계] {language} 구글 뉴스 실시간 핫이슈를 스크래핑 중입니다...")
    if language.lower() == "korean":
        url = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
    else:
        url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
        
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    root = ET.fromstring(response.content)
    
    headlines = []
    for item in root.findall('.//item')[:20]: # 상위 20개 뉴스
        title = item.find('title').text
        headlines.append(title)
        
    print(f"✅ {len(headlines)}개의 핫이슈를 수집 완료했습니다.")
    return headlines

# ==========================================
# 🧠 2단계: AI 편집장의 '가치 판단' 및 '미래 예측'
# ==========================================
def ai_editor_in_chief(headlines, language="Korean"):
    print(f"🧠 [2단계] AI 편집장이 돈이 될 만한 뉴스를 선별하고 예측 각도를 잡고 있습니다...")
    lang_instruction = "Korean" if language.lower() == "korean" else "English"
    headlines_text = "\n".join([f"- {h}" for h in headlines])
    
    prompt = f"""
    당신은 100만 방문자를 이끄는 천재적인 블로그 편집장이자 애널리스트입니다.
    현재 구글의 실시간 뉴스 헤드라인 20개는 다음과 같습니다:
    
    {headlines_text}
    
    [미션]
    1. 위 뉴스들 중에서 블로그 방문자들이 가장 클릭하고 싶어할(관심도가 폭발할) 주제 1개를 고르세요.
    2. 과거의 팩트나 결과를 단순히 보도하지 마세요. (예: OOO 경기 패배)
    3. 대신, 그 사건이 가져올 **'미래 파장(예측), 다음 행보, 수혜자/피해자, 또는 숨겨진 의미'**로 각도를 180도 비틀어서 '매력적인 키워드와 앵글'을 제시하세요.
    
    결과를 반드시 {lang_instruction}로 아래 JSON 포맷에 정확히 맞춰서 다른 텍스트 없이 JSON만 출력하세요.
    {{
      "selected_topic": "선택한 원본 뉴스 헤드라인",
      "predictive_keyword": "향후 예측으로 각도를 비튼 핵심 블로그 키워드",
      "angle_strategy": "왜 이 앵글이 대중의 클릭을 유도할 수 있는지에 대한 전략 1줄 설명"
    }}
    """
    
    from google.genai import types
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        )
    )
    import re
    result_text = response.text
    match = re.search(r'\{.*\}', result_text, re.DOTALL)
    if match:
        result_text = match.group(0)
    return json.loads(result_text, strict=False)

# ==========================================
# 📝 3단계: AI SEO 글쓰기 및 이미지 프롬프트 생성
# ==========================================
def generate_seo_content(predictive_keyword, angle_strategy, language="Korean"):
    print(f"🤖 [3단계] Gemini가 예측 앵글('{predictive_keyword}')을 바탕으로 SEO 마크다운 글을 작성 중입니다...")
    lang_instruction = "Korean" if language.lower() == "korean" else "English"
    
    prompt = f"""
    당신은 최고 수준의 SEO 카피라이터입니다.
    다음 '예측형 키워드'와 '앵글 전략'을 바탕으로 구글 검색 1페이지에 노출될 수 있는 완벽한 예측/분석 칼럼을 마크다운 문법으로 작성하세요.
    언어는 반드시 {lang_instruction}로 작성하세요.
    
    [키워드]: {predictive_keyword}
    [앵글 전략]: {angle_strategy}
    
    [작성 규칙]
    1. 글자수: 1,500 단어 이상 (심도 있는 분석과 미래 예측 포함)
    2. 형식: Markdown 형식으로 작성. (예: ## 서론, ### 분석1 등)
    3. 구조: 서론(현 상황 요약 및 호기심 유발) -> 본론 1,2,3 (팩트 기반의 날카로운 미래 예측 및 분석) -> 결론(향후 관전 포인트 요약)
    
    [JSON 출력 형식 - 다른 텍스트 없이 JSON만 반환]
    {{
      "title": "클릭을 유도하는 매력적인 예측형 SEO 제목",
      "content": "## 서론\n본문...\n\n## 분석\n본문...",
      "meta_description": "구글 검색 결과에 노출될 150자 이내의 요약 설명",
      "image_prompt": "본문 내용과 어울리는 고품질 블로그 썸네일 생성을 위한 영어 프롬프트"
    }}
    """
    
    from google.genai import types
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        )
    )
    import re
    result_text = response.text
    match = re.search(r'\{.*\}', result_text, re.DOTALL)
    if match:
        result_text = match.group(0)
    return json.loads(result_text, strict=False)

# ==========================================
# 🖼️ 4단계: AI 무료 이미지 생성 및 다운로드
# ==========================================
def generate_and_download_image(image_prompt, filename="thumbnail.jpg"):
    print(f"🎨 [4단계] 썸네일 이미지를 생성 및 다운로드하고 있습니다... (프롬프트: {image_prompt})")
    encoded_prompt = urllib.parse.quote(image_prompt)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1200&height=630&nologo=true"
    
    filepath = os.path.join(IMAGES_DIR, filename)
    response = requests.get(image_url)
    if response.status_code == 200:
        with open(filepath, "wb") as f:
            f.write(response.content)
        print(f"✅ 이미지 다운로드 완료: {filepath}")
        return f"/assets/images/{filename}"
    else:
        print(f"❌ 이미지 다운로드 실패")
        return None

# ==========================================
# 🚀 5단계: Jekyll 마크다운 파일 생성
# ==========================================
def create_jekyll_post(title, content, meta_description, image_path):
    print("🚀 [5단계] Jekyll 형식의 마크다운(.md) 파일을 생성 중입니다...")
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M:%S") + " +0900"
    
    # 영문 소문자와 하이픈만으로 slug 생성 (한글 제목 방지)
    import uuid
    slug_id = str(uuid.uuid4())[:8]
    filename = f"{date_str}-trend-forecast-{slug_id}.md"
    filepath = os.path.join(POSTS_DIR, filename)
    image_url_path = f"/blog/assets/images/{os.path.basename(image_path)}"
    
    frontmatter = f"""---
layout: post
title: "{title.replace('"', '')}"
date: {time_str}
categories: [Trend, Forecast]
tags: [AI, Prediction]
excerpt: "{meta_description.replace('"', '')}"
image: {image_url_path}
---

![Thumbnail]({image_url_path})

{content}
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter)
    print(f"✅ 마크다운 파일 생성 완료: {filepath}")
    return filepath

# ==========================================
# ☁️ 6단계: GitHub 자동 푸시 (퍼블리싱)
# ==========================================
def push_to_github():
    print("☁️ [6단계] 생성된 콘텐츠를 GitHub로 자동 배포(Push) 합니다...")
    try:
        subprocess.run(["git", "add", "."], cwd=REPO_DIR, check=True)
        subprocess.run(["git", "commit", "-m", f"Auto post: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"], cwd=REPO_DIR, check=True)
        # GitHub Remote 가 세팅되어 있으므로 푸시합니다.
        subprocess.run(["git", "push", "origin", "main"], cwd=REPO_DIR, check=True)
        print("🎉 로컬 Git Commit 및 GitHub 자동 Push 완벽하게 성공! 전 세계 배포 완료!")
    except Exception as e:
        print(f"❌ Git 커밋 실패: {e}")

# ==========================================
# 자율 주행 팩토리 실행 (Main)
# ==========================================
def run_autonomous_factory():
    print("==========================================================")
    print(" 🔥 GitHub Pages V3.0 실시간 트렌드 예측 봇 (완전 자율주행) 🔥")
    print("==========================================================")
    print("데이터베이스도 서버도 필요 없습니다. 파일 하나면 전 세계와 연결됩니다.\n")
    
    language = "Korean"
        
    try:
        # 1. 실시간 트렌드 스크래핑
        headlines = fetch_realtime_trends(language)
        
        # 2. AI 편집장의 가치 판단 및 예측 앵글 추출
        editor_decision = ai_editor_in_chief(headlines, language)
        print("\n💡 [편집장 분석 결과]")
        print(f" - 채택된 원본 뉴스: {editor_decision['selected_topic']}")
        print(f" - 도출된 예측 키워드: {editor_decision['predictive_keyword']}")
        print(f" - 앵글(셀링 포인트): {editor_decision['angle_strategy']}\n")
        
        # 3. 글 & 이미지 프롬프트 생성
        article_data = generate_seo_content(editor_decision['predictive_keyword'], editor_decision['angle_strategy'], language)
        
        # 4. 이미지 생성 (유니크한 파일명)
        import uuid
        image_filename = f"thumbnail_{str(uuid.uuid4())[:8]}.jpg"
        image_path = generate_and_download_image(article_data["image_prompt"], image_filename)
        
        # 5. 마크다운 파일 발행
        create_jekyll_post(article_data["title"], article_data["content"], article_data.get("meta_description", ""), image_path)
        
        # 6. GitHub 자동 푸시
        push_to_github()
            
    except Exception as e:
        print(f"\n❌ 파이프라인 에러 발생: {e}")

if __name__ == "__main__":
    run_autonomous_factory()
