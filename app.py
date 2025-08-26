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
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # ✅ 최신 방식

def extract_title_from_reply(reply):
    """GPT 응답에서 '제목: (...)' 패턴을 찾아 제목을 추출합니다."""
    if not reply:
        return "딥러닝 블로그"
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
    
    search_results = get_mock_search_results(query)
    result_count = format_number(random.randint(10000000, 999999999))
    search_time = round(random.uniform(0.1, 0.4), 2)
    
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

# ✅ 정적 블로그 페이지 라우트들
@app.route('/blog_page_<int:page_id>')
def blog_page(page_id):
    return render_template(f'blog_page_{page_id}.html')

@app.route('/naverblog-results')
def naverblog_results():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('home'))
    
    use_web_param = request.args.get('use_web')
    use_web = should_use_web_search(query) if use_web_param is None else use_web_param.lower() in ['1','true','yes','y']

    if use_web:
        reply = get_blog_response_with_web(query)
        if not reply or reply.startswith('웹검색 기반 응답 중 오류'):
            reply = get_chatgpt_response(query)
    else:
        reply = get_chatgpt_response(query)

    blog_title = extract_title_from_reply(reply)
    cleaned_reply = re.sub(r'제목:\s*\(.*?\)\s*\n?', '', reply) if reply else ''

    try:
        reply_html = markdown(cleaned_reply or '',
                              extras=['fenced-code-blocks','tables','strike',
                                      'break-on-newline','code-friendly','cuddled-lists'])
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
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query is missing"}), 400
    reply = get_chatgpt_response(query)
    return jsonify({"reply": reply})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "요청 데이터가 없습니다"}), 400
        message = data.get('message','')
        original_query = data.get('original_query','')
        conversation_history = data.get('conversation_history',[])
        use_web = data.get('use_web', None)

        if not message:
            return jsonify({"error": "메시지가 없습니다"}), 400

        if use_web is None:
            use_web = should_use_web_search(message)

        if use_web:
            reply = get_chat_response_with_web(message, original_query, conversation_history)
        else:
            reply = get_chat_response(message, original_query, conversation_history)

        try:
            reply_html = markdown(reply or '',
                                  extras=['fenced-code-blocks','tables','strike',
                                          'break-on-newline','code-friendly','cuddled-lists'])
        except Exception:
            reply_html = reply or ''

        return jsonify({"reply": reply, "reply_html": reply_html})
    except Exception as e:
        return jsonify({"error": f"서버 오류가 발생했습니다: {str(e)}"}), 500

# ✅ OpenAI 응답 함수들 (최신 방식)
def get_chatgpt_response(query):
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role":"system","content":"너는 AI 전문가야. ... (생략 가능)"},
                {"role":"user","content":query}
            ],
            max_tokens=2000,
            temperature=0.7,
            presence_penalty=0.1,
            frequency_penalty=0.1
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"네이버 블로그 응답 중 오류가 발생했습니다: {str(e)}"

def get_blog_response_with_web(query):
    try:
        # (DuckDuckGo 검색 로직은 위 코드 참고, 그대로 사용 가능)
        # ...
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role":"system","content":"..."},
                      {"role":"user","content":"..."}],
            max_tokens=2000,
            temperature=0.5
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"웹검색 기반 응답 중 오류가 발생했습니다: {str(e)}"

def get_chat_response(message, original_query, conversation_history):
    try:
        messages = [{"role":"system","content":"너는 AI 전문가야. ..."}]
        for hist in conversation_history[-10:]:
            messages.append({"role":hist.get("role","user"),"content":hist.get("content","")})
        messages.append({"role":"user","content":message})

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1500,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"대화 응답 중 오류가 발생했습니다: {str(e)}"

def get_chat_response_with_web(message, original_query, conversation_history):
    try:
        # (웹 검색 로직은 동일)
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role":"system","content":"..."}, {"role":"user","content":"..."}],
            max_tokens=1400,
            temperature=0.4
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"웹검색 기반 응답 중 오류가 발생했습니다: {str(e)}"

# ✅ 나머지 mock search/format 함수는 기존과 동일 (생략)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

# Vercel 배포용 설정
app.debug = False
