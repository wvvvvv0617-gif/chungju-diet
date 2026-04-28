self.addEventListener('install', (e) => {
  console.log('서비스 워커 설치됨');
});

self.addEventListener('fetch', (e) => {
  // 앱 설치 조건을 충족하기 위한 코드
});
