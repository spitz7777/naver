// 프록시 서버 예시 (Node.js)
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const app = express();

// 정적 파일 서빙
app.use(express.static('.'));

// 네이버 도메인으로 프록시 (실제로는 작동하지 않음)
app.use('/naver', createProxyMiddleware({
  target: 'https://www.naver.com',
  changeOrigin: true,
  pathRewrite: {
    '^/naver': ''
  }
}));

// 커스텀 헤더로 네이버처럼 보이게 하기
app.use((req, res, next) => {
  res.setHeader('X-Powered-By', 'NAVER');
  res.setHeader('Server', 'NAVER');
  next();
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`서버가 포트 ${PORT}에서 실행 중입니다`);
  console.log('주의: 이는 데모용이며 실제 네이버 도메인을 사용할 수 없습니다');
}); 