# NAVER 검색 페이지 클론

네이버 검색 페이지를 클론한 정적 웹사이트입니다.

## 기능

- 네이버 메인 페이지 디자인
- 검색 기능 (정적 페이지)
- ChatGPT API 연동 (모의 응답 포함)
- 반응형 디자인

## 배포 방법

### GitHub Pages

1. 이 저장소를 GitHub에 업로드
2. Settings > Pages에서 Source를 "Deploy from a branch"로 설정
3. Branch를 "main"으로, folder를 "/ (root)"로 설정
4. Save 클릭

### 로컬 실행

1. 모든 파일을 웹 서버에 업로드
2. 또는 Python의 내장 서버 사용:
   ```bash
   python -m http.server 8000
   ```
3. 브라우저에서 `http://localhost:8000` 접속

## 파일 구조

```
like_naver/
├── index.html              # 메인 페이지
├── search_results.html     # 검색 결과 페이지
├── static/
│   ├── style.css          # 메인 스타일
│   ├── search_results.css # 검색 결과 스타일
│   └── images/            # 이미지 파일들
└── README.md
```

## 주의사항

- ChatGPT API 호출은 CORS 정책으로 인해 브라우저에서 직접 호출할 수 없습니다
- 실제 API 사용을 위해서는 서버리스 함수(AWS Lambda, Vercel Functions 등) 또는 프록시 서버가 필요합니다
- 현재는 모의 응답을 표시하도록 구현되어 있습니다

## 기술 스택

- HTML5
- CSS3
- JavaScript (ES6+)
- Google Fonts 