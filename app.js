// [1] 서비스 워커 등록
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./service-worker.js')
            .then(reg => console.log('서비스 워커 등록 성공:', reg.scope))
            .catch(err => console.log('서비스 워커 등록 실패:', err));
    });
}

// [2] 기상청 실시간 날씨
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

// [3] AI 영양사 및 알레르기 분석 (통합 완성본)
async function askAI() {
    const outputDiv = document.getElementById('ai-output');
    if (!outputDiv) return;

    let currentMeal = "";
    
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

        const mealData = menuData.meals ? menuData.meals[targetDay] : null;
        if (mealData) {
            const menus = [mealData.breakfast, mealData.lunch, mealData.dinner]
                .filter(m => m && m.length > 2 && !m.includes("식단 없음"));
            currentMeal = menus.join(', ');
        }
    } catch (e) { console.error("식단 로드 실패:", e); }

    if (!currentMeal || currentMeal.length < 3) {
        outputDiv.innerHTML = "❌ 분석할 식단 정보가 없습니다.";
        return;
    }

    outputDiv.innerHTML = "✨ AI 영양사가 분석 중입니다...";

    try {
        // [수정] 주소 끝에 슬래시(/)를 절대 넣지 않고 파라미터로 캐시 방지
        const response = await fetch('https://gemini-proxy.wvvvvv0617.workers.dev?t=' + Date.now(), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{ parts: [{ text: `식단: ${currentMeal}` }] }]
            })
        });

        if (!response.ok) throw new Error(`서버 오류 (${response.status})`);
        const data = await response.json();

        if (data && data.candidates && data.candidates[0]) {
            let rawText = data.candidates[0].content.parts[0].text;
            
            // AI 응답에서 마크다운 기호가 포함된 경우 순수 JSON만 추출
            const jsonMatch = rawText.match(/\{[\s\S]*\}/);
            const aiResponse = JSON.parse(jsonMatch ? jsonMatch[0] : rawText);

            // 기존 이모지 삭제 후 새로 추가
            document.querySelectorAll('.allergy-icon').forEach(icon => icon.remove());
            if (aiResponse.allergy_map) {
                const menuItems = document.querySelectorAll('.bg-white.rounded-2xl span, li'); 
                menuItems.forEach(el => {
                    const name = el.innerText.trim();
                    if (aiResponse.allergy_map[name]) {
                        const icon = document.createElement('span');
                        icon.className = 'allergy-icon';
                        icon.style.marginLeft = '6px';
                        icon.innerText = aiResponse.allergy_map[name];
                        el.appendChild(icon);
                    }
                });
            }

            // 결과 조언 표시
            outputDiv.innerHTML = aiResponse.summary ? aiResponse.summary.replace(/\n/g, '<br>') : "분석 완료";
            outputDiv.style.textAlign = 'left';
        }
    } catch (error) {
        outputDiv.innerHTML = `❌ 오류: ${error.message}`;
    }
}
