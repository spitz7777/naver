# -*- coding: utf-8 -*-
from flask import Flask, render_template, request, jsonify, redirect, url_for
from openai import OpenAI
import os
import requests
import random
import time
from bs4 import BeautifulSoup
import re
import urllib.parse
from markdown2 import markdown

app = Flask(__name__)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_title_from_reply(reply):
    """GPT 응답에서 '제목: (...)' 패턴을 찾아 제목을 추출합니다."""
    if not reply:
        return "딥러닝 블로그"
    
    # '제목: (...)' 또는 '제목:(...)' 패턴 찾기
    title_match = re.search(r'제목:\s*\((.*?)\)', reply)
    if title_match:
        return title_match.group(1).strip()
    return "딥러닝 블로그"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search')
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('home'))
    
    # 구글 검색 결과만 먼저 빠르게 로드
    search_results = get_mock_search_results(query)
    result_count = format_number(random.randint(10000000, 999999999))
    search_time = round(random.uniform(0.1, 0.4), 2) # 시간을 더 빠르게 조정
    
    return render_template(
        'search_results.html',
        query=query,
        search_results=search_results,
        result_count=result_count,
        search_time=search_time
    )

@app.route('/search_results')
def search_results():
    return render_template('search_results.html')

@app.route('/naverblog-results')
def naverblog_results():
    print(f"naverblog-results 라우트 호출됨, 쿼리: {request.args.get('q', '')}")
    query = request.args.get('q', '')
    if not query:
        print("쿼리가 없어서 홈으로 리다이렉트")
        return redirect(url_for('home'))
    
    # 웹검색 사용 여부 결정 (URL 파라미터가 우선)
    use_web_param = request.args.get('use_web')
    use_web = should_use_web_search(query) if use_web_param is None else use_web_param.lower() in ['1', 'true', 'yes', 'y']

    print(f"ChatGPT 응답 생성 시작 (use_web={use_web}): {query}")
    if use_web:
        reply = get_blog_response_with_web(query)
        # 웹검색 결과가 없으면 일반 응답으로 폴백
        if not reply or reply.startswith('웹검색 기반 응답 중 오류'):
            reply = get_chatgpt_response(query)
    else:
        reply = get_chatgpt_response(query)
    print(f"ChatGPT 응답 완료")

    # 제목 추출
    blog_title = extract_title_from_reply(reply)
    
    # 제목 패턴이 있다면 응답에서 제거
    cleaned_reply = re.sub(r'제목:\s*\(.*?\)\s*\n?', '', reply) if reply else ''

    # ChatGPT 텍스트 응답을 Markdown -> HTML로 변환
    try:
        reply_html = markdown(
            cleaned_reply or '',
            extras=[
                'fenced-code-blocks',
                'tables',
                'strike',
                'break-on-newline',
                'code-friendly',
                'cuddled-lists'
            ]
        )
    except Exception:
        reply_html = cleaned_reply or ''
    
    return render_template(
        'naverblog_results.html',
        query=query,
        reply=cleaned_reply,
        reply_html=reply_html,
        blog_title=blog_title
    )

@app.route('/api/naverblog-search')
def api_naverblog_search():
    """네이버 블로그 결과를 비동기적으로 가져오는 API 엔드포인트"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query is missing"}), 400
    
    reply = get_chatgpt_response(query)
    return jsonify({"reply": reply})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """멀티턴 대화를 처리하는 API 엔드포인트"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "요청 데이터가 없습니다"}), 400
        
        message = data.get('message', '')
        original_query = data.get('original_query', '')
        conversation_history = data.get('conversation_history', [])
        use_web = data.get('use_web', None)
        
        if not message:
            return jsonify({"error": "메시지가 없습니다"}), 400
        
        # 웹검색 사용 여부 자동 감지 (클라이언트에서 명시 전달 시 우선)
        if use_web is None:
            use_web = should_use_web_search(message)

        # 대화 응답 생성 (웹검색 분기)
        if use_web:
            reply = get_chat_response_with_web(message, original_query, conversation_history)
        else:
            reply = get_chat_response(message, original_query, conversation_history)
        
        # Markdown을 HTML로 변환
        try:
            reply_html = markdown(
                reply or '',
                extras=[
                    'fenced-code-blocks',
                    'tables',
                    'strike',
                    'break-on-newline',
                    'code-friendly',
                    'cuddled-lists'
                ]
            )
        except Exception:
            reply_html = reply or ''
        
        return jsonify({
            "reply": reply,
            "reply_html": reply_html
        })
        
    except Exception as e:
        return jsonify({"error": f"서버 오류가 발생했습니다: {str(e)}"}), 500

def get_chatgpt_response(query):
    """네이버 블로그 API를 호출하여 응답을 가져옵니다."""
    try:
        response = client.chat.completions.create(
            # model="gpt-3.5-turbo",
            model="gpt-4o",
            messages=[
                {"role": "system", "content": """너는 AI 전문가야. 물어보는 사항에 대해 전문가적 지식을 답변하고 그에 대한 상세한 설명을 해주세요.
                  문제를 물어보면 그에대한 정답을 말해주세요. 먼저 대답 맨 처음에는 '제목:' 이렇게 해서 대답에 대한 제목을 한문장으로 짧게 요약하고 시작해줘.
                 답변시 단계별로 설명하고, 필요시 번호나 글머리 기호를 사용해주세요."""},
                {"role": "user", "content": query}
            ],
            max_tokens=2000,  # 최대 토큰 수 증가
            temperature=0.7,  # 창의성과 다양성 증가
            presence_penalty=0.1,  # 새로운 주제 도입 장려
            frequency_penalty=0.1   # 반복 방지
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"네이버 블로그 응답 중 오류가 발생했습니다: {str(e)}"

def get_blog_response_with_web(query: str) -> str:
    """블로그 초기 응답에도 웹검색 결과를 포함하여 더 신뢰도 있는 답변 생성."""
    try:
        web_results = perform_web_search_duckduckgo(query, max_results=5)
        if not web_results:
            return get_chatgpt_response(query)

        sources_text_lines = []
        for i, r in enumerate(web_results, start=1):
            sources_text_lines.append(
                f"[{i}] 제목: {r.get('title','')}\nURL: {r.get('url','')}\n요약: {r.get('snippet','')}"
            )
        sources_text = "\n\n".join(sources_text_lines)

        system_message = (
            "너는 기술 블로그 글을 작성하는 전문가야. 아래 웹검색 결과를 활용해 정확하고 구조적인 한국어 글을 작성해줘.\n"
            "글의 맨 처음에는 '제목: (한문장 요약)' 형식으로 제목을 포함하고, 본문에서는 소제목, 목록, 코드블록 등을 적절히 사용해.\n"
            "가능하면 말미에 참조 링크를 [1], [2] 형식으로 표기해."
        )

        user_message = (
            f"주제: {query}\n\n"
            f"참고용 웹검색 결과:\n{sources_text}"
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            max_tokens=2000,
            temperature=0.5,
            presence_penalty=0.0,
            frequency_penalty=0.2
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"웹검색 기반 응답 중 오류가 발생했습니다: {str(e)}"

def get_chat_response(message, original_query, conversation_history):
    """멀티턴 대화를 처리하여 응답을 생성합니다."""
    try:
        # 시스템 메시지 구성
        system_message = f"""너는 AI 전문가야. 사용자가 '{original_query}'에 대해 질문했고, 이에 대한 답변을 제공한 후 추가적인 대화를 이어가고 있어.

이전 대화 맥락을 고려하여 사용자의 추가 질문에 답변해줘. 
- 이전 답변과 연결성을 유지하면서 자연스러운 대화를 이어가세요.
- 전문적이고 정확한 정보를 제공하되, 이해하기 쉽게 설명해주세요.
- 필요시 단계별로 설명하고, 번호나 글머리 기호를 사용해주세요.
- 사용자가 더 깊이 있는 질문을 한다면 상세한 설명을 제공해주세요."""

        # 메시지 리스트 구성
        messages = [{"role": "system", "content": system_message}]
        
        # 대화 히스토리 추가 (최근 5턴만 유지하여 토큰 사용량 최적화)
        recent_history = conversation_history[-10:] if len(conversation_history) > 10 else conversation_history
        for hist in recent_history:
            messages.append({
                "role": hist.get("role", "user"),
                "content": hist.get("content", "")
            })
        
        # 현재 메시지 추가
        messages.append({"role": "user", "content": message})
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1500,
            temperature=0.7,
            presence_penalty=0.1,
            frequency_penalty=0.1
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"대화 응답 중 오류가 발생했습니다: {str(e)}"

def should_use_web_search(message: str) -> bool:
    """메시지 내용으로부터 웹검색 필요성을 간단히 휴리스틱으로 판단합니다."""
    print("웹검색 필요성을 판단합니다.")
    if not message:
        return False
    lowered = message.strip().lower()
    # 명시 프리픽스
    if lowered.startswith(('웹검색', '웹 검색', '검색해줘', '웹에서', '인터넷검색', '인터넷 검색')):
        return True
    # 최신/뉴스/링크/근거 요청 등 키워드 포함
    keywords = [
        '최신', '방금', '최근', '뉴스', '실시간', '근거', '출처', '링크', '웹에서', '인터넷에서', '검색해', '검색 해서', '검색해서'
    ]
    return any(k in lowered for k in keywords)

def perform_web_search_duckduckgo(query: str, max_results: int = 5):
    """DuckDuckGo HTML 페이지를 파싱하여 간단한 웹검색 결과를 수집합니다. (무API, 비로그인)
    반환: [{title, url, snippet}]
    """
    try:
        print("웹검색 시작")
        q = urllib.parse.quote(query)
        url = f"https://duckduckgo.com/html/?q={q}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        results = []
        # 다양한 셀렉터 시도 (DuckDuckGo html 레이아웃 대응)
        candidates = soup.select('div.result') or soup.select('div.result__body') or []
        for item in candidates:
            a = item.select_one('a.result__a') or item.select_one('a[href]')
            if not a or not a.get('href'):
                continue
            title = a.get_text(strip=True)
            url = a.get('href')
            # 스니펫 추출
            snippet_el = item.select_one('.result__snippet') or item.select_one('.result__extras__url') or item
            snippet = snippet_el.get_text(' ', strip=True) if snippet_el else ''
            results.append({
                'title': title,
                'url': url,
                'snippet': snippet
            })
            if len(results) >= max_results:
                break

        return results
    except Exception as e:
        return []

def get_chat_response_with_web(message: str, original_query: str, conversation_history):
    """웹검색 결과를 활용해 답변을 생성합니다."""
    try:
        search_query = message.strip() or original_query
        web_results = perform_web_search_duckduckgo(search_query, max_results=5)

        # 웹 결과가 없을 경우 일반 응답으로 대체
        if not web_results:
            return get_chat_response(message, original_query, conversation_history)

        # 검색 결과를 컨텍스트로 구성
        sources_text_lines = []
        for i, r in enumerate(web_results, start=1):
            sources_text_lines.append(
                f"[{i}] 제목: {r.get('title','')}\nURL: {r.get('url','')}\n요약: {r.get('snippet','')}"
            )
        sources_text = "\n\n".join(sources_text_lines)

        system_message = (
            "너는 웹에서 수집된 최신 공개 정보를 바탕으로 정확하고 신뢰성 있는 답변을 작성하는 보조자야.\n"
            "아래 제공된 웹 검색 결과만을 주요 근거로 사용하고, 가능하면 답변 말미에 참조 링크를 [1], [2] 형식으로 표기해줘.\n"
            "불확실하면 모른다고 말하고, 추정은 분명히 표기해."
        )

        guidance = (
            "다음은 이 질문에 대한 웹 검색 결과야. 결과를 종합해 간결하고 구조적인 한국어 답변을 작성해줘.\n\n"
            f"질문: {message}\n\n"
            f"웹 검색 결과:\n{sources_text}"
        )

        messages = [
            {"role": "system", "content": system_message},
            # 맥락 유지 (최근 6턴만)
            *[
                {"role": h.get('role','user'), "content": h.get('content','')}
                for h in (conversation_history[-6:] if isinstance(conversation_history, list) else [])
            ],
            {"role": "user", "content": guidance}
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1400,
            temperature=0.4,
            presence_penalty=0.0,
            frequency_penalty=0.2
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"웹검색 기반 응답 중 오류가 발생했습니다: {str(e)}"

def get_mock_search_results(query):
    """구글 검색 결과를 모방한 가짜 결과를 생성합니다."""
    results = []
    
    # 쿼리를 마침표 기준으로 분할
    query_parts = [q.strip() for q in query.split('.') if q.strip()]
    if not query_parts:
        query_parts = [query]

    # 일반적인 웹사이트 결과
    domains = [
        "wikipedia.org", "naver.com", "youtube.com", "github.com", 
        "medium.com", "stackoverflow.com", "ted.com", "harvard.edu",
        "mit.edu", "stanford.edu", "bbc.com", "cnn.com", "nytimes.com"
    ]
    
    # 쿼리에 따른 타이틀과 스니펫 생성
    for i in range(8):
        domain = random.choice(domains)
        # 분할된 쿼리를 순환하며 각 결과에 할당
        current_query = query_parts[i % len(query_parts)]
        title = generate_title(current_query, domain)
        snippet = generate_snippet(current_query) # 스니펫에도 적용
        url = f"https://www.{domain}/{''.join(current_query.split())[:10]}/{random.randint(1000, 9999)}"
        
        results.append({
            "title": title,
            "url": url,
            "snippet": snippet
        })
    
    return results

def generate_title(query, domain):
    """쿼리에 기반한 가짜 제목을 생성합니다."""
    # 쿼리 길이에 따른 축약 (더 이상 필요하지 않을 수 있지만, 만일을 위해 유지)
    if len(query) > 15:
        query_short = query[:15] + "..."
    else:
        query_short = query
    
    templates = [
        "{query} - 상세 정보 및 가이드",
        "{query}에 대한 모든 것 | {domain}",
        "{query} 완벽 가이드 (2023년 최신)",
        "{query} - 전문가가 알려주는 핵심 정보",
        "왜 {query}가 중요한가? | {domain}",
        "{query} 관련 최신 트렌드와 정보",
        "{query} - 기초부터 고급까지",
        "{domain} - {query} 전문 리소스"
    ]
    
    title = random.choice(templates).format(query=query_short, domain=domain.split('.')[0].capitalize())
    return title

def generate_snippet(query):
    """쿼리에 기반한 가짜 스니펫을 생성합니다."""
    # 스니펫에서도 쿼리 길이 제한
    if len(query) > 20:
        query_short = query[:20] + "..."
    else:
        query_short = query
    
    templates = [
        "{query}는 현대 사회에서 중요한 주제로 부각되고 있습니다. 많은 전문가들이 {query}의 영향력에 주목하고 있으며, 최근 연구에 따르면 {query}는 미래 산업의 핵심 요소로 자리 잡을 것으로 예상됩니다. 특히 {query}의 발전 과정에서 나타나는 다양한 현상들과 그에 따른 사회적 변화는 우리가 주목해야 할 중요한 포인트입니다. 전문가들은 {query}가 가져올 변화에 대해 긍정적인 전망을 보이고 있으며, 이는 우리의 일상생활에도 큰 영향을 미칠 것으로 예상됩니다.",
        "{query}에 대한 이해는 현대 사회를 살아가는 데 필수적입니다. 본 가이드에서는 {query}의 기본 개념부터 실제 적용 사례까지 상세히 다루고 있습니다. {query}의 역사적 배경과 발전 과정을 통해 현재 상황을 이해하고, 미래 전망까지 포괄적으로 분석했습니다. 또한 {query}와 관련된 다양한 관점과 의견을 종합하여 균형 잡힌 시각을 제공하고자 노력했습니다. 이 글을 통해 {query}에 대한 깊이 있는 이해를 얻으실 수 있을 것입니다.",
        "최근 {query}에 관한 관심이 급증하고 있습니다. 이 글에서는 {query}의 역사, 현재 동향, 그리고 미래 전망에 대해 알아봅니다. {query}가 사회에 미치는 영향과 그 중요성에 대해 다양한 측면에서 분석하고 있으며, 특히 최신 트렌드와 기술적 발전에 초점을 맞추고 있습니다. 전문가 인터뷰와 실제 사례를 통해 {query}의 현실적 의미와 활용 방안을 제시하고 있습니다. 이 글을 통해 {query}에 대한 포괄적이고 실용적인 지식을 얻으실 수 있습니다.",
        "{query}에 관한 최신 정보와 전문가 인터뷰를 통해 심층적인 이해를 돕습니다. {query}가 우리 일상에 미치는 영향과 앞으로의 발전 방향에 대해 알아보세요. 본 기사에서는 {query}와 관련된 최신 연구 결과와 통계 데이터를 바탕으로 객관적인 분석을 제공합니다. 또한 {query}의 다양한 측면과 그에 따른 사회적 변화에 대해 깊이 있게 다루고 있으며, 독자들이 {query}에 대해 더 나은 이해를 가질 수 있도록 도움을 드립니다.",
        "{query}는 많은 사람들에게 여전히 미스터리로 남아있습니다. 이 글에서는 {query}에 관한 일반적인 오해와 진실을 파헤치고, 실제 사례를 통해 그 중요성을 설명합니다. {query}에 대한 잘못된 정보와 편견을 바로잡고, 과학적이고 객관적인 관점에서 접근하여 정확한 정보를 제공합니다. 또한 {query}와 관련된 다양한 의견과 연구 결과를 종합하여 균형 잡힌 시각을 제시하고, 독자들이 {query}에 대해 올바른 판단을 내릴 수 있도록 도움을 드립니다.",
        "{query}에 관심이 있으신가요? 이 종합 가이드에서는 {query}에 대한 모든 것을 다루고 있습니다. 초보자부터 전문가까지 모두에게 유용한 정보를 제공합니다. {query}의 기본 개념부터 고급 내용까지 단계별로 설명하고 있으며, 실제 적용 사례와 팁도 함께 제공합니다. 또한 {query}와 관련된 최신 동향과 트렌드를 파악할 수 있도록 도움을 드리며, 독자들이 {query}에 대해 더 깊이 있는 이해를 가질 수 있도록 다양한 관점에서 접근했습니다.",
        "{query}의 세계로 오신 것을 환영합니다. 이 페이지에서는 {query}의 기초 개념부터 고급 기술까지 단계별로 설명하고 있습니다. {query}에 대한 체계적이고 포괄적인 이해를 돕기 위해 다양한 학습 자료와 예제를 제공하고 있으며, 독자들의 수준에 맞는 맞춤형 정보를 제공합니다. 또한 {query}와 관련된 실무 경험과 노하우도 함께 공유하여, 이론과 실습을 모두 겸비한 지식을 얻으실 수 있도록 도움을 드립니다.",
        "전문가들이 추천하는 {query} 관련 최고의 리소스를 소개합니다. {query}에 대한 깊이 있는 이해와 실용적인 팁을 얻을 수 있습니다. 본 기사에서는 {query} 분야의 전문가들이 직접 추천하는 학습 자료, 도구, 그리고 방법론을 소개하고 있습니다. {query}에 대한 체계적인 학습 경로와 실무 적용 방안을 제시하며, 독자들이 {query}에 대해 더 효과적으로 접근할 수 있도록 도움을 드립니다. 또한 {query}와 관련된 커뮤니티와 네트워킹 기회도 함께 소개합니다."
    ]
    
    snippet = random.choice(templates).format(query=query_short)
    return snippet

def format_number(num):
    """숫자를 천 단위로 콤마를 찍어 포맷팅합니다."""
    return "{:,}".format(num)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

# Vercel 배포를 위한 설정
app.debug = False
