// [1] 서비스 워커 등록
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./service-worker.js')
            .then(reg => console.log('서비스 워커 등록 성공:', reg.scope))
            .catch(err => console.log('서비스 워커 등록 실패:', err));
    });
}

// [2] 기상청 실시간 날씨 (기존 로직 유지)
const WEATHER_API_KEY = "e45e99f92f1e612fe4190678af2e64592c0fffa1eb08bb1291215d9c3ae01aae";
const NX = 76; 
const NY = 114;

async function fetchRealtimeWeather() {
    try {
        const now = new Date();
        let baseDate = now.getFullYear() + String(now.getMonth() + 1).padStart(2, '0') + String(now.getDate()).padStart(2, '0');
        const hours = now.getHours();
        const apiTimes = [2, 5, 8, 11, 14, 17, 20, 23];
        let lastTime = apiTimes.filter(t => t <= hours).pop();
        if (lastTime === undefined) {
            const yesterday = new Date(now.setDate(now.getDate() - 1));
            baseDate = yesterday.getFullYear() + String(yesterday.getMonth() + 1).padStart(2, '0') + String(yesterday.getDate()).padStart(2, '0');
            lastTime = 23;
        }
        const baseTime = String(lastTime).padStart(2, '0') + "00";
        const url = `https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst?serviceKey=${WEATHER_API_KEY}&numOfRows=100&pageNo=1&dataType=JSON&base_date=${baseDate}&base_time=${baseTime}&nx=${NX}&ny=${NY}`;

        const response = await fetch(url);
        if (!response.ok) throw new Error('Weather API Error');
        const data = await response.json();
        if (data.response && data.response.header.resultCode === "00") {
            const items = data.response.body.items.item;
            const currentHourStr = String(now.getHours()).padStart(2, '0') + "00";
            const tmpItem = items.find(i => i.category === "TMP" && i.fcstTime >= currentHourStr);
            const popItem = items.find(i => i.category === "POP" && i.fcstTime >= currentHourStr);
            if (tmpItem) document.getElementById('realtime-temp').innerText = tmpItem.fcstValue + "°";
            if (popItem) document.getElementById('precipitation').innerText = popItem.fcstValue + "%";
        }
    } catch (error) { console.error("날씨 호출 오류:", error); }
}

// [3] AI 영양사 분석 (프론트엔드 최적화 버전)
async function askAI() {
    const outputDiv = document.getElementById('ai-output');
    if (!outputDiv) return;

    // 1. 현재 화면에 실제로 보이는(Visible) 메뉴 카드들만 수집
    const visibleCards = Array.from(document.querySelectorAll('.meal-item-card'))
                              .filter(card => card.offsetParent !== null);

    if (visibleCards.length === 0) {
        outputDiv.innerHTML = "❌ 분석할 식단 정보가 없습니다.";
        return;
    }

    // 2. 메뉴 이름만 추출하여 쉼표로 연결
    const menuNames = visibleCards.map(card => card.querySelector('.menu-name-text').innerText.trim());
    const currentMeal = menuNames.join(', ');
    
    outputDiv.innerHTML = "✨ AI 영양사가 분석 중입니다...";

    try {
        const workerUrl = 'https://gemini-proxy.wvvvvv0617.workers.dev';
        
        // 3. Worker 서버로 식단 데이터 전송 (지시문은 Worker에서 처리함)
        const response = await fetch(workerUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                mealData: currentMeal // 식단 데이터만 깔끔하게 전달
            })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `서버 오류 ${response.status}`);

        // 4. AI 응답 처리 (JSON 파싱)
        if (data && data.candidates && data.candidates[0]) {
            let rawText = data.candidates[0].content.parts[0].text;
            // JSON 형식만 추출하는 정규식
            const jsonMatch = rawText.match(/\{[\s\S]*\}/);
            const aiResponse = JSON.parse(jsonMatch ? jsonMatch[0] : rawText);

            // 5. 알레르기 이모지 업데이트
            visibleCards.forEach(card => {
                // 기존 아이콘 제거
                const oldIcon = card.querySelector('.allergy-icon');
                if (oldIcon) oldIcon.remove();

                const nameText = card.querySelector('.menu-name-text').innerText.trim();
                
                // AI 응답의 allergy_map에서 현재 메뉴와 일치하는 키 찾기
                const matchingKey = Object.keys(aiResponse.allergy_map).find(key => 
                    nameText.includes(key) || key.includes(nameText)
                );

                const emojiStr = matchingKey ? aiResponse.allergy_map[matchingKey] : "";

                if (emojiStr && emojiStr.trim() !== "") {
                    const iconContainer = card.querySelector('.allergy-icon-container');
                    if (iconContainer) {
                        const icon = document.createElement('span');
                        icon.className = 'allergy-icon ml-2 text-base';
                        icon.innerText = emojiStr;
                        iconContainer.appendChild(icon);
                    }
                }
            });

            // 6. 요약 텍스트 출력
            outputDiv.innerHTML = aiResponse.summary ? aiResponse.summary.replace(/\n/g, '<br>') : "분석 완료";
        }
    } catch (error) {
        console.error("AI 호출 오류:", error);
        outputDiv.innerHTML = `❌ 오류: ${error.message}<br>잠시 후 다시 시도해주세요.`;
    }
}

// [4] 날짜 변경 시 결과를 초기화하는 함수
// 요일 이동 버튼(화살표)을 클릭할 때 이 함수가 실행되도록 연결되어 있어야 합니다.
function clearAIResults() {
    const outputDiv = document.getElementById('ai-output');
    if (outputDiv) {
        outputDiv.innerHTML = "✨ 분석 버튼을 누르면 AI 영양사가 분석을 시작합니다.";
    }
    // 모든 카드에서 기존 알레르기 아이콘 제거
    document.querySelectorAll('.allergy-icon').forEach(icon => icon.remove());
}

// 초기 실행 (필요 시)
window.addEventListener('DOMContentLoaded', () => {
    fetchRealtimeWeather();
});
