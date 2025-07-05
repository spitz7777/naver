from flask import Flask, render_template, request, jsonify, redirect, url_for
from openai import OpenAI
import os
import requests
import random
import time
from bs4 import BeautifulSoup
import re

app = Flask(__name__)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # 환경변수로 API Key 설정

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

@app.route('/api/chatgpt-search')
def api_chatgpt_search():
    """ChatGPT 결과를 비동기적으로 가져오는 API 엔드포인트"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query is missing"}), 400
    
    reply = get_chatgpt_response(query)
    return jsonify({"reply": reply})

def get_chatgpt_response(query):
    """ChatGPT API를 호출하여 응답을 가져옵니다."""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "너는 AI 전문가야. 물어보는 사항에 대해 전문가적 지식을 답변하고 그에 대하 상세한 설명을 해줘."},
                {"role": "user", "content": query}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"ChatGPT 응답 중 오류가 발생했습니다: {str(e)}"

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
