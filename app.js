// [1] 서비스 워커 등록 로직
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./service-worker.js')
            .then(reg => console.log('서비스 워커 등록 성공:', reg.scope))
            .catch(err => console.log('서비스 워커 등록 실패:', err));
    });
}

// [2] 기상청 실시간 날씨 가져오기 기능
const WEATHER_API_KEY = "e45e99f92f1e612fe4190678af2e64592c0fffa1eb08bb1291215d9c3ae01aae";
const NX = 76; // 충주 격자 X
const NY = 114; // 충주 격자 Y

async function fetchRealtimeWeather() {
    try {
        const now = new Date();
        // 기상청 API는 정해진 시간에만 데이터를 생성하므로, 현재 시간 기준 가장 최근 발표 시간을 계산
        let baseDate = now.getFullYear() + String(now.getMonth() + 1).padStart(2, '0') + String(now.getDate()).padStart(2, '0');
        const hours = now.getHours();
        const apiTimes = [2, 5, 8, 11, 14, 17, 20, 23]; // 단기예보 발표 시각
        
        // 현재 시각보다 작거나 같은 발표 시각 중 가장 최근 것 찾기
        let lastTime = apiTimes.filter(t => t <= hours).pop();
        
        // 새벽 2시 이전인 경우 어제 날짜 23시 데이터를 참조
        if (lastTime === undefined) {
            const yesterday = new Date(now.setDate(now.getDate() - 1));
            baseDate = yesterday.getFullYear() + String(yesterday.getMonth() + 1).padStart(2, '0') + String(yesterday.getDate()).padStart(2, '0');
            lastTime = 23;
        }
        
        const baseTime = String(lastTime).padStart(2, '0') + "00";
        const url = `https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst?serviceKey=${WEATHER_API_KEY}&numOfRows=100&pageNo=1&dataType=JSON&base_date=${baseDate}&base_time=${baseTime}&nx=${NX}&ny=${NY}`;

        const response = await fetch(url);
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();

        if (data.response && data.response.header.resultCode === "00") {
            const items = data.response.body.items.item;
            const currentHourStr = String(now.getHours()).padStart(2, '0') + "00";
            
            // 현재 시간 이후의 가장 가까운 TMP(기온), POP(강수확률) 찾기
            const tmpItem = items.find(i => i.category === "TMP" && i.fcstTime >= currentHourStr);
            const popItem = items.find(i => i.category === "POP" && i.fcstTime >= currentHourStr);

            if (tmpItem) document.getElementById('realtime-temp').innerText = tmpItem.fcstValue + "°";
            if (popItem) document.getElementById('precipitation').innerText = popItem.fcstValue + "%";
            console.log("실시간 날씨 정보 갱신 완료");
        }
    } catch (error) {
        console.error("날씨 API 호출 오류:", error);
    }
}

// [3] index.html의 loadData에서 호출할 수 있도록 전역으로 노출하거나 자동 실행
// 이 함수는 index.html의 loadData() 안에서 fetchRealtimeWeather(); 로 호출하시면 됩니다.

// [4] AI 영양사 분석 및 알레르기 이모지 표시 기능
async function askAI() {
    const outputDiv = document.getElementById('ai-output');
    if (!outputDiv) return;

    let currentMeal = "";
    
    // [수정] 식단 데이터 수집 로직 개선
    try {
        const res = await fetch('data.json?v=' + Date.now());
        const menuData = await res.json();

        const pageText = document.body.innerText;
        let targetDay = "";
        if (pageText.includes("월요일")) targetDay = "월";
        else if (pageText.includes("화요일")) targetDay = "화";
        else if (pageText.includes("수요일")) targetDay = "수";
        else if (pageText.includes("목요일")) targetDay = "목";
        else if (pageText.includes("금요일")) targetDay = "금";

        // 화면에 날짜 텍스트가 있다면 (예: 2026-05-11) 해당 날짜 데이터를 먼저 찾음
        // 여기서는 요일 기반으로 가져오는 로직을 유지하되, 데이터가 있는지 엄격히 체크
        const mealData = menuData.meals ? menuData.meals[targetDay] : null;

        if (mealData) {
            const menus = [mealData.breakfast, mealData.lunch, mealData.dinner]
                .filter(m => m && m.length > 2 && !m.includes("식단 없음"));
            currentMeal = menus.join(', ');
        }
    } catch (e) {
        console.error("식단 데이터 로드 실패:", e);
    }

    if (!currentMeal || currentMeal.length < 3) {
        outputDiv.innerHTML = "❌ 분석할 식단 정보가 없습니다. 요일을 확인해주세요.";
        return;
    }

    outputDiv.innerHTML = "✨ AI 영양사가 식단을 분석 중입니다...";

    try {
        // [주의] URL 끝에 /를 붙여보거나 대시보드 주소와 대조하세요
        const response = await fetch('https://gemini-proxy.wvvvvv0617.workers.dev/', { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{
                    parts: [{ text: `식단: ${currentMeal}` }]
                }]
            })
        });

        if (!response.ok) throw new Error(`서버 응답 오류 (${response.status})`);

        const data = await response.json();

        // [방어 코드] 데이터 구조가 있는지 확인 후 파싱
        if (data && data.candidates && data.candidates[0]) {
            const rawText = data.candidates[0].content.parts[0].text;
            // AI가 간혹 ```json ... ``` 형태로 줄 때를 대비해 정규식으로 순수 JSON만 추출
            const jsonMatch = rawText.match(/\{[\s\S]*\}/);
            const aiResponse = JSON.parse(jsonMatch ? jsonMatch[0] : rawText);

            // 1. 알레르기 이모지 표시 (선택자 정밀화)
            if (aiResponse.allergy_map) {
                // 메뉴 리스트 내의 글자들만 타겟팅 (HTML 구조에 맞춰 .menu-item-text 등으로 수정 필요)
                const menuItems = document.querySelectorAll('.menu-item span, .menu-list li'); 
                menuItems.forEach(el => {
                    const menuName = el.innerText.trim();
                    if (aiResponse.allergy_map[menuName]) {
                        // 중복 방지
                        if (!el.innerHTML.includes('allergy-icon')) {
                            el.innerHTML += ` <span class="allergy-icon" style="margin-left:5px;">${aiResponse.allergy_map[menuName]}</span>`;
                        }
                    }
                });
            }

            // 2. 조언 출력
            outputDiv.innerHTML = aiResponse.summary.replace(/\n/g, '<br>');
            outputDiv.style.textAlign = 'left';
        } else {
            throw new Error("잘못된 AI 응답 구조");
        }

    } catch (error) {
        console.error("분석 에러:", error);
        outputDiv.innerHTML = `❌ 오류 발생: ${error.message}<br>Worker 주소와 설정을 확인하세요.`;
    }
}
