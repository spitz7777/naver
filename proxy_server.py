from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

@app.route('/api/chatgpt', methods=['POST'])
def chatgpt_proxy():
    try:
        # 클라이언트로부터 데이터 받기
        data = request.json
        query = data.get('query', '')
        
        # OpenAI API 호출
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}'
        }
        
        payload = {
            'model': 'gpt-4o',
            'messages': [
                {
                    'role': 'system',
                    'content': '너는 AI 전문가야. 물어보는 사항에 대해 전문가적 지식을 답변하고 그에 대하 상세한 설명을 해줘.'
                },
                {
                    'role': 'user',
                    'content': query
                }
            ],
            'max_tokens': 1500,
            'temperature': 0.7
        }
        
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'reply': result['choices'][0]['message']['content']
            })
        else:
            return jsonify({
                'success': False,
                'error': 'API 호출 실패'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("프록시 서버가 시작되었습니다.")
    print("외부 IP: 218.147.76.201")
    print("포트: 8081")
    print("GitHub Pages에서 다음 URL로 요청: http://218.147.76.201:8081/api/chatgpt")
    app.run(host='0.0.0.0', port=8081, debug=True) 