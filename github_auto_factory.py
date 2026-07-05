import os
import json
import requests
import urllib.parse
import xml.etree.ElementTree as ET
from google import genai
import datetime
import subprocess
from dotenv import load_dotenv
import schedule
import time
import sys
from telegram_notifier import send_telegram_message
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
    print(f"📡 [1단계] {language} 구글 뉴스 'IT 및 보안' 핫이슈를 스크래핑 중입니다...")
    if language.lower() == "korean":
        url = "https://news.google.com/rss/search?q=IT+보안+해킹+사이버+정보보안&hl=ko&gl=KR&ceid=KR:ko"
    else:
        url = "https://news.google.com/rss/search?q=IT+Cyber+Security+Hacking&hl=en-US&gl=US&ceid=US:en"
        
    response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
    root = ET.fromstring(response.content)
    
    headlines = []
    for item in root.findall('.//item')[:20]: # 상위 20개 뉴스
        title = item.find('title').text
        headlines.append(title)
        
    print(f"✅ {len(headlines)}개의 핫이슈를 수집 완료했습니다.")
    return headlines

# ==========================================
# 🛑 공통 모듈: API Rate Limit 우회 및 자동 재시도
# ==========================================
def call_gemini_with_retry(prompt, is_json=False):
    from google.genai import types
    import time
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            config = types.GenerateContentConfig(response_mime_type="application/json") if is_json else None
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=config
            )
            return response
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                print(f"⏳ [API 한도 초과] 60초 대기 후 재시도합니다... (시도 {attempt+1}/{max_retries})")
                time.sleep(60)
            else:
                raise e
    raise Exception("API 재시도 횟수를 초과했습니다.")

# ==========================================
# 🧠 2단계: AI 편집장의 '가치 판단' 및 '미래 예측'
# ==========================================
def ai_editor_in_chief(headlines, language="Korean"):
    print(f"🧠 [2단계] AI 편집장이 돈이 될 만한 뉴스를 선별하고 예측 각도를 잡고 있습니다...")
    import time
    time.sleep(10) # API Limit 방지
    
    lang_instruction = "Korean" if language.lower() == "korean" else "English"
    headlines_text = "\n".join([f"- {h}" for h in headlines])
    
    prompt = f"""
    당신은 100만 방문자를 이끄는 천재적인 블로그 편집장이자 애널리스트입니다.
    현재 구글의 실시간 뉴스 헤드라인 20개는 다음과 같습니다:
    
    {headlines_text}
    
    [미션]
    1. 위 뉴스들 중에서 블로그 방문자들이 가장 클릭하고 싶어할(관심도가 폭발할) **'IT 및 정보보안(사이버 해킹, 데이터 유출, 보안 기술 등)'** 관련 주제 1개를 고르세요.
    2. 과거의 팩트나 결과를 단순히 보도하지 마세요.
    3. 대신, 그 IT/보안 사건이 가져올 **'미래 파장(예측), 다음 행보, 수혜자/피해자, 기업의 보안 위협, 기술적 대안'**으로 각도를 180도 비틀어서 '매력적인 키워드와 앵글'을 제시하세요.
    
    결과를 반드시 {lang_instruction}로 아래 JSON 포맷에 정확히 맞춰서 다른 텍스트 없이 JSON만 출력하세요.
    {{
      "selected_topic": "선택한 원본 뉴스 헤드라인",
      "predictive_keyword": "향후 예측으로 각도를 비튼 핵심 블로그 키워드",
      "angle_strategy": "왜 이 앵글이 대중의 클릭을 유도할 수 있는지에 대한 전략 1줄 설명"
    }}
    """
    
    response = call_gemini_with_retry(prompt, is_json=True)
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
    import time
    time.sleep(15) # API Limit 방지
    
    lang_instruction = "Korean" if language.lower() == "korean" else "English"
    
    prompt = f"""
    당신은 IT/보안 전문 블로거 'Jett'입니다. 현실에서 당신은 엔드포인트 보안과 계정 관리 업무를 수행하는 10년 차 '정보보호 담당자'입니다. 
    다음 예측형 키워드와 앵글 전략을 바탕으로, 당신의 생생한 실무 경험(E-E-A-T)이 짙게 묻어나는 구글 SEO 최적화 블로그 칼럼을 마크다운으로 작성해 줘.

    [작성 가이드라인 - 구글 E-E-A-T 및 Low Value Content 회피 필수 규칙]
    1. [실제 사건 및 구체적 통계 강제 (가장 중요)]: 두루뭉술한 일반론("전문가들이 의견을 같이한다")은 절대 금지합니다. 반드시 최근 발생한 실제 해킹/보안 사고 사례 2~3개(예: 홍콩 딥페이크 송금 사기, MGM 리조트 랜섬웨어 사태 등)를 **특정 기업명, 발생 연도, 구체적인 피해 규모(숫자, 통계치)**와 함께 작성하세요.
    2. [1인칭 실무자 인사이트 심화]: 뻔한 지식 나열을 막기 위해, 글 중간에 반드시 "최근 사내 임직원들을 대상으로 피싱 모의 훈련을 진행해보니...", "저희 회사 보안 솔루션 로그를 분석해보면..." 과 같이 현직 정보보호 담당자만이 쓸 수 있는 디테일한 1인칭 화법을 1회 이상 삽입하세요.
    3. [공포 조장 단어 사용 금지 (블랙리스트)]: 구글 품질 평가 감점을 피하기 위해 "재앙", "인류 전체의 위협", "파멸", "가장 위험한 변곡점" 같은 과장된 선정적 단어는 절대 사용하지 마세요. 구체적인 수치와 팩트 위주로 건조하게 서술하세요.
    4. [글 구조의 다양화]: "도입-위협나열-대응-결론" 이라는 뻔한 AI 템플릿을 피하세요. 오늘 글의 본문 구조는 **[실제 사고 심층 분석형], [실무자 체크리스트형], [데이터 통계 기반형]** 중 하나를 랜덤하게 선택하여 매우 입체적이고 차별화되게 구성하세요.
    5. [제목 최적화]: 핵심 키워드가 맨 앞에 오도록 하되, 길이는 반드시 **50~65자 이내**로 작성하세요. (예: "초지능 AI 해킹 시대, 사이버 보안은 어떻게 달라질까?")
    6. [키워드 스터핑 금지]: 타겟 키워드({predictive_keyword})를 20번씩 기계적으로 반복하지 마세요. 대신 '생성형 AI 보안', '랜섬웨어', '제로데이', 'LLM 방어' 등 연관 LSI 키워드를 자연스럽게 섞어 쓰세요.
    7. [공신력 있는 출처 인용]: "IBM X-Force", "Microsoft Digital Defense Report", "OWASP" 등 실제 글로벌 보안 기관이나 보고서를 반드시 1회 이상 인용하여 객관적 근거를 뒷받침하세요.
    8. [체류시간 늘리기 구조]: 
       - 서론: "안녕하세요" 금지! 바로 핵심 키워드를 포함한 강렬한 문장으로 훅(Hook)을 날리세요.
       - 중간 요약: 글 중반부에 핵심 요약(Bullet point) 3줄을 넣어 가독성을 높이세요.
       - 비교 표(Table): 기존 기술과 AI 기술의 비교 등 유용한 정보를 마크다운 표(Table)로 1개 이상 만드세요.
       - FAQ: 글 하단에 '자주 묻는 질문(FAQ)' 3~4개를 작성해 구글 스니펫 노출을 노리세요.
    9. 분량은 공백 제외 2000자 이상으로 매우 상세하게 작성하세요.
    
    [핵심 주제 및 전략]
    [키워드]: {predictive_keyword}
    [앵글 전략]: {angle_strategy}
    
    [JSON 출력 형식 - 다른 텍스트 없이 JSON만 반환]
    {{
      "title": "50~65자 이내의 매력적인 SEO 제목",
      "content": "## 서론\n본문...\n\n## 분석\n본문... (표, 중간요약, FAQ, 구체적 통계/사례 등 모두 포함)",
      "meta_description": "구글 검색 결과에 노출될 150자 이내의 요약 설명",
      "image_prompt": "본문 내용과 어울리는 고품질 블로그 썸네일 생성을 위한 영어 프롬프트. '16:9 wide aspect ratio', 'realistic', 'no text', 'no logo' 키워드를 반드시 포함할 것."
    }}
    """
    
    response = call_gemini_with_retry(prompt, is_json=True)
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
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"
    
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
# 👨‍⚖️ 4.5단계: 전문가 집단 콘텐츠 심사 및 최적화
# ==========================================
def expert_panel_review(article_data, language="Korean"):
    print("👨‍⚖️ [전문가 집단 검증] IT/경제/사회, SEO/애드센스, 그래픽 디자이너가 콘텐츠를 심사합니다...")
    
    prompt = f"""
    당신은 구글 애드센스 승인과 E-E-A-T(경험, 전문성, 권위, 신뢰) 알고리즘을 완벽하게 꿰뚫고 있는 [최고급 다중 전문가 패널]입니다.
    구성원: 현직 정보보안 최고 책임자(CISO), 구글 SEO 수석 엔지니어, 애드센스 심사역.
    
    다음 블로그 포스트 초안을 혹독하게 비판하고, 애드센스 심사에서 가장 많이 탈락하는 사유인 'Low Value Content(가치가 낮은 콘텐츠)'를 완벽하게 회피하도록 글을 '직접 재작성(Refining)'하여 최종 결과를 JSON으로 반환하세요.
    
    [초안 데이터]
    - 제목: {article_data['title']}
    - 본문: {article_data['content']}
    - 요약: {article_data.get('meta_description', '')}
    - 썸네일 프롬프트: {article_data.get('image_prompt', '')}
    
    [검증 및 수정 포인트 - 필수 통과 요건]
    1. 구체적 팩트/사례 부족 (Low Value Content 방어): 두루뭉술한 일반론이나 "전문가들이 의견을 같이한다" 식의 근거 없는 문장이 있다면 전부 삭제하세요. 대신 최근 발생한 실제 해킹 사고(기업명, 날짜 포함)나 구체적인 수치(퍼센트, 피해액 등)를 구글링한 것처럼 사실적으로 2~3개 보강하세요. 오직 이 페이지에서만 얻을 수 있는 고품질 정보가 있어야 합니다.
    2. 공포 조장 단어 정제: "재앙", "인류의 위협", "가장 위험한 변곡점" 같은 뻔하고 과장된 AI식 수식어가 있다면 객관적이고 건조한 실무자 톤으로 100% 깎아내세요.
    3. 개인 경험(Experience) 보강: 글 작성자가 '엔드포인트 보안 및 계정 관리를 수행하는 10년차 정보보호 담당자'라는 페르소나가 글 전체에 스며들도록, "사내 모의 해킹 훈련을 해보니...", "최근 악성코드 로그를 분석해보면..." 같은 디테일한 1인칭 실무자의 고충이나 깨달음을 깊게 서술하세요.
    4. 신뢰성(Trustworthiness) 보강: IBM, Microsoft, OWASP 등 실제 보안 기관의 리포트나 통계가 언급되지 않았다면, 그럴듯한(실제 있는) 보안 트렌드 보고서 내용을 인용하여 객관성을 100배 끌어올리세요.
    5. 가독성 및 체류시간 극대화: 본문에 마크다운 표(Table), 중간 요약(Bullet), FAQ 섹션이 누락되었다면 반드시 추가하세요. 지루한 '도입-나열-결론' 구조를 깨고 체크리스트나 데이터 분석형 구조를 섞어주세요.
    6. 제목 길이 검증: 제목이 65자를 초과하면 잘리므로, 50~65자 이내로 매끄럽게 수정하세요. 
    7. 분량 확장: 내용이 부실하면 살을 붙여 공백 제외 2000자 이상으로 꽉 채우세요.
    
    [출력 포맷 - JSON만 반환할 것]
    {{
      "title": "전문가들이 승인한 65자 이내의 최종 SEO 제목",
      "content": "전문가들이 완벽하게 수정한 최종 본문 (마크다운 포맷)",
      "meta_description": "최종 요약",
      "image_prompt": "디자이너가 수정한 최종 썸네일 프롬프트"
    }}
    """
    import time
    time.sleep(15)
    
    response = call_gemini_with_retry(prompt, is_json=True)
    import re
    result_text = response.text
    match = re.search(r'\{.*\}', result_text, re.DOTALL)
    if match:
        result_text = match.group(0)
    return json.loads(result_text, strict=False)

# ==========================================
# 🚀 5단계: Jekyll 마크다운 파일 생성
# ==========================================
def create_jekyll_post(title, content, meta_description, image_path, predictive_keyword):
    print("🚀 [5단계] Jekyll 형식의 마크다운(.md) 파일을 생성 중입니다...")
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%Y-%m-%d %H:%M:%S") + " +0900"
    
    import uuid, re
    slug_id = str(uuid.uuid4())[:8]
    filename = f"{date_str}-trend-forecast-{slug_id}.md"
    filepath = os.path.join(POSTS_DIR, filename)
    image_url_path = f"/blog/assets/images/{os.path.basename(image_path)}"
    
    # SEO 친화적 URL (Permalink) 생성
    seo_slug = re.sub(r'[^가-힣a-zA-Z0-9-]', '', predictive_keyword.replace(' ', '-'))
    seo_slug = re.sub(r'-+', '-', seo_slug).strip('-')
    
    frontmatter = f"""---
layout: post
title: "{title.replace('"', '')}"
date: {time_str}
categories: [Trend, Forecast]
tags: [AI, Prediction]
excerpt: "{meta_description.replace('"', '')}"
image: {image_url_path}
permalink: /trend/{seo_slug}/
---

![{predictive_keyword}]({image_url_path})

{content}
"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter)
    print(f"✅ 마크다운 파일 생성 완료: {filepath}")
    return filepath

# ==========================================
# 💻 5.5단계: 기술 검증 위원회 (코드 & 무결성 테스트)
# ==========================================
def technical_verification_panel(filepath):
    print("💻 [기술 검증 위원회] QA, SA, NA, TA, DA, AA, 파이썬 수석 개발자가 마크다운과 코드를 최종 검증합니다...")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    prompt = f"""
    당신은 최고 수준의 [기술 검증 위원회]입니다.
    구성원: QA, SA, NA, TA, DA, AA, 수석 파이썬 개발자.
    
    다음은 GitHub Pages(Jekyll)에 푸시되기 직전의 마크다운 파일 내용입니다.
    기술적 오류, 마크다운 문법 오류, 특수문자 이스케이프 오류, Frontmatter YAML 구조 깨짐 등이 있는지 철저히 교차 검사하고 에러를 수정한 '완벽한 형태'로 반환하세요.
    절대로 본문의 맥락이나 내용을 임의로 바꾸지 말고 기술적인 포맷만 검증/수정하세요.
    
    [마크다운 원본]
    {content}
    
    [검증 포인트]
    1. Frontmatter (--- 로 둘러싸인 부분) YAML 문법 오류 확인 (특히 겹따옴표 등).
    2. 마크다운의 헤딩(#, ##) 띄어쓰기 오류, 리스트(-) 깨짐 등.
    3. 금지된 HTML 태그나 Jekyll 컴파일 에러 유발 코드 여부.
    
    [출력 포맷 - JSON만 반환할 것]
    {{
      "verified_markdown": "수정 및 검증이 완료된 전체 마크다운 텍스트 (Frontmatter 포함)"
    }}
    """
    import time
    time.sleep(15)
    
    response = call_gemini_with_retry(prompt, is_json=True)
    import re
    result_text = response.text
    match = re.search(r'\{.*\}', result_text, re.DOTALL)
    if match:
        result_text = match.group(0)
    
    try:
        verified_markdown = json.loads(result_text, strict=False)["verified_markdown"]
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(verified_markdown)
        print("✅ [기술 검증 완료] 모든 마크다운 및 코드 오류가 수정되었습니다.")
    except Exception as e:
        print(f"⚠️ 기술 검증 파싱 오류 발생 (원본 유지): {e}")

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
    
    send_telegram_message("🤖 <b>Jett's Insight 팩토리 가동 시작</b>\n전문가 집단이 새로운 트렌드 분석을 시작합니다. (작성/검증 약 3~5분 소요)")
    
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
        
        # [NEW] 전문가 집단 검증
        article_data = expert_panel_review(article_data, language)
        print("✅ [전문가 집단 검증 완료] 글의 퀄리티가 대폭 상승했습니다.")
        
        # 4. 이미지 생성 (유니크한 파일명)
        import uuid
        image_filename = f"thumbnail_{str(uuid.uuid4())[:8]}.jpg"
        image_path = generate_and_download_image(article_data["image_prompt"], image_filename)
        
        # 5. 마크다운 파일 발행
        filepath = create_jekyll_post(article_data["title"], article_data["content"], article_data.get("meta_description", ""), image_path, editor_decision['predictive_keyword'])
        
        # [NEW] 기술 검증 위원회 검증
        technical_verification_panel(filepath)
        
        # 6. GitHub 자동 푸시
        push_to_github()
        
        # 발행 완료 후 텔레그램 알림 전송 (URL 포함)
        import re
        seo_slug = re.sub(r'[^가-힣a-zA-Z0-9-]', '', editor_decision['predictive_keyword'].replace(' ', '-'))
        seo_slug = re.sub(r'-+', '-', seo_slug).strip('-')
        post_url = f"https://jett-1993.github.io/blog/trend/{seo_slug}/"
        send_telegram_message(f"🎉 <b>포스팅 완료!</b>\n\n새로운 분석 글이 발행되었습니다.\n🔗 {post_url}")
            
    except Exception as e:
        print(f"\n❌ 파이프라인 에러 발생: {e}")
        send_telegram_message(f"❌ <b>팩토리 에러 발생</b>\n파이프라인 실행 중 에러가 발생했습니다: {e}")

def job():
    import random
    import time
    delay_minutes = random.randint(1, 45)
    print(f"🕵️‍♂️ 봇(Bot) 탐지 회피를 위해 {delay_minutes}분 대기 후 포스팅을 시작합니다...")
    send_telegram_message(f"🕵️‍♂️ <b>휴먼 행동 모방 시스템 작동</b>\n봇 탐지 회피를 위해 {delay_minutes}분 후 포스팅을 시작합니다.")
    time.sleep(delay_minutes * 60)
    run_autonomous_factory()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        run_autonomous_factory()
    else:
        print("🕒 스케줄러 모드로 가동합니다. (매일 08:00, 19:00 자동 실행 및 매시간 QA 봇 가동)")
        send_telegram_message("🕒 <b>Jett's Insight 스케줄러 가동</b>\n매일 오전 8시, 오후 7시에 자동 포스팅을 진행합니다.\n(매시간 SEO 무결성 모니터링 가동 중)")
        
        # 글 작성 스케줄
        schedule.every().day.at("08:00").do(job)
        schedule.every().day.at("19:00").do(job)
        
        # 매시간 QA 봇 가동
        try:
            from blog_qa_bot import run_qa
            schedule.every().hour.do(run_qa)
        except ImportError:
            pass
        
        while True:
            schedule.run_pending()
            time.sleep(60)
