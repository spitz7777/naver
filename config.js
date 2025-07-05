// URL 설정 파일
const URL_CONFIG = {
  // URL 패턴 설정 (원하는 패턴을 선택하세요)
  pattern: 'search', // 'search', 'results', 'query', 'find', 'naver' 중 선택
  
  // 사용 가능한 패턴들
  patterns: {
    'search': 'search',
    'results': 'results', 
    'query': 'query',
    'find': 'find',
    'naver': 'naver',
    'custom': 'my-search' // 사용자 정의 패턴
  },
  
  // 페이지 제목 설정
  titleFormat: '{query} - NAVER 검색',
  
  // 홈페이지 URL
  homeURL: 'index.html',
  
  // 검색 결과 페이지 URL
  resultsPage: 'search_results.html'
};

// 설정을 전역으로 내보내기
if (typeof module !== 'undefined' && module.exports) {
  module.exports = URL_CONFIG;
} else {
  window.URL_CONFIG = URL_CONFIG;
} 