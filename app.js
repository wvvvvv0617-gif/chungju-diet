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
    let allMenusArray = []; // 이모지 표시를 위해 메뉴들을 배열로 저장

    try {
        const res = await fetch('data.json?v=' + Date.now());
        const menuData = await res.json();

        // 1. 현재 화면에 표시된 요일 추출 (UI 텍스트 기반)
        const pageText = document.body.innerText;
        let targetDay = "";
        if (pageText.includes("월요일")) targetDay = "월";
        else if (pageText.includes("화요일")) targetDay = "화";
        else if (pageText.includes("수요일")) targetDay = "수";
        else if (pageText.includes("목요일")) targetDay = "목";
        else if (pageText.includes("금요일")) targetDay = "금";

        // 2. [수정] 현재 선택된 요일의 데이터를 우선적으로 가져오도록 변경
        // 기존 코드는 오늘 날짜(Date)를 먼저 찾아버려서 다른 날 분석이 안 될 수 있음
        const mealData = menuData.meals ? menuData.meals[targetDay] : null;

        if (mealData) {
            allMenusArray = [
                ...(mealData.breakfast || "").split(','),
                ...(mealData.lunch || "").split(','),
                ...(mealData.dinner || "").split(',')
            ].map(m => m.trim()).filter(m => m.length > 0 && !m.includes("식단 없음"));

            currentMeal = allMenusArray.join(', ');
        }
    } catch (e) {
        console.error("식단 데이터 로드 실패:", e);
    }

    // 3. 식단 정보 체크
    if (!currentMeal || currentMeal.length < 3) {
        outputDiv.innerHTML = "❌ 분석할 식단 정보가 없습니다. (요일을 확인해주세요)";
        return;
    }

    outputDiv.innerHTML = "✨ AI 영양사가 식단을 분석하고 알레르기 정보를 확인 중입니다...";

    try {
        const response = await fetch('https://gemini-proxy.wvvvvv0617.workers.dev', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: `오늘의 전체 식단 리스트야: ${currentMeal}. 
                        각 메뉴별 알레르기 성분을 이모지로 분류하고, 전체적인 영양 조언을 해줘.`
                    }]
                }]
            })
        });

        const data = await response.json();
        // Worker에서 설정한 JSON 응답 파싱
        const aiResponse = JSON.parse(data.candidates[0].content.parts[0].text);

        // 4. [추가] 메뉴 옆에 알레르기 이모지 표시 로직
        if (aiResponse.allergy_map) {
            // 화면에 있는 모든 메뉴 텍스트 요소들을 찾음 (보라색 점 옆의 글자들)
            // HTML 구조에 따라 'li' 또는 'span' 등 적절한 선택자로 수정이 필요할 수 있습니다.
            const menuElements = document.querySelectorAll('.menu-item span, li'); 
            
            menuElements.forEach(el => {
                const menuName = el.innerText.trim();
                // Gemini가 준 allergy_map에 해당 메뉴명이 있으면 이모지 추가
                if (aiResponse.allergy_map[menuName]) {
                    const emojiSpan = document.createElement('span');
                    emojiSpan.style.marginLeft = "8px";
                    emojiSpan.innerText = aiResponse.allergy_map[menuName];
                    el.appendChild(emojiSpan);
                }
            });
        }

        // 5. 영양 조언 출력
        if (aiResponse.summary) {
            outputDiv.innerHTML = aiResponse.summary.replace(/\n/g, '<br>');
            outputDiv.style.textAlign = 'left';
        } else {
            outputDiv.innerHTML = "❌ 분석 결과를 가져오지 못했습니다.";
        }

    } catch (error) {
        console.error("연결 오류:", error);
        outputDiv.innerHTML = "❌ 분석 중 오류가 발생했습니다. (Worker 설정을 확인하세요)";
    }
}
