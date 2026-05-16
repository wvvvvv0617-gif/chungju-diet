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

// [3] AI 영양사 및 알레르기 분석
async function askAI() {
    const outputDiv = document.getElementById('ai-output');
    if (!outputDiv) return;

    let currentMeal = "";
    
    try {
        const menuItems = document.querySelectorAll('.menu-name-text');
        if (menuItems.length > 0) {
            currentMeal = Array.from(menuItems).map(el => el.innerText).join(', ');
        }
    } catch (e) { console.error("데이터 수집 실패:", e); }

    if (!currentMeal || currentMeal.length < 3) {
        outputDiv.innerHTML = "❌ 분석할 식단 정보가 없습니다.";
        return;
    }

    outputDiv.innerHTML = "✨ AI 영양사가 분석 중입니다...";

    try {
        const workerUrl = 'https://gemini-proxy.wvvvvv0617.workers.dev';
        
        // 사용자의 요청 사항을 프롬프트에 엄격히 반영
        const systemInstruction = `
            당신은 학교 영양사입니다. 다음 식단을 분석하고 조언을 제공하세요.
            [분석할 식단]: ${currentMeal}

            [작성 지침]:
            1. 학교 안에는 '매점'만 있으며 스낵류, 음료, 냉동식품 위주라는 점을 고려하세요. 과일 등 신선식품 구매는 어렵다는 것을 조언에 반영하세요.
            2. 학생들을 위해 걷기, 러닝, 근력 운동 등 식후에 하면 좋은 운동을 간단하게 추천하세요.
            3. 답변의 마지막 문장은 반드시 "알레르기에 대한 내용은 식단에 알레르기 정보를 표기해놓았으니 확인 바랍니다."라고 작성하세요.

            [알레르기 이모지 매핑 가이드]:
            메뉴에 아래 성분이 포함된 경우 반드시 해당 이모지를 사용하세요 (⚠️ 대신 사용):
            - 난류: 🥚, 우유: 🥛, 메밀: 🌾, 땅콩: 🥜, 대두(콩): 🫘, 밀: 🌾, 고등어: 🐟, 게: 🦀, 새우: 🦐, 돼지고기: 🐷, 복숭아: 🍑, 토마토: 🍅, 아황산류: 🧪, 호두: 🥜, 닭고기: 🍗, 쇠고기: 🐮, 오징어: 🦑, 조개류(굴, 전복, 홍합 포함): 🐚, 잣: 🌲

            4. 출력은 반드시 아래와 같은 JSON 형식만 허용합니다:
               {"allergy_map": {"메뉴명": "알레르기이모지"}, "summary": "영양분석 및 조언내용(운동 추천 포함)"}
        `;

        const response = await fetch(workerUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{ parts: [{ text: systemInstruction }] }]
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || `서버 오류 ${response.status}`);
        }

        if (data && data.candidates && data.candidates[0]) {
            let rawText = data.candidates[0].content.parts[0].text;
            const jsonMatch = rawText.match(/\{[\s\S]*\}/);
            const aiResponse = JSON.parse(jsonMatch ? jsonMatch[0] : rawText);

            // 기존 이모지 초기화
            document.querySelectorAll('.allergy-icon').forEach(icon => icon.remove());
            
            if (aiResponse.allergy_map) {
                const mealCards = document.querySelectorAll('.meal-item-card'); 
                mealCards.forEach(card => {
                    const nameText = card.querySelector('.menu-name-text').innerText.trim();
                    if (aiResponse.allergy_map[nameText]) {
                        const iconContainer = card.querySelector('.allergy-icon-container');
                        if (iconContainer) {
                            const icon = document.createElement('span');
                            icon.className = 'allergy-icon ml-2 text-base';
                            icon.innerText = aiResponse.allergy_map[nameText];
                            iconContainer.appendChild(icon);
                        }
                    }
                });
            }
            outputDiv.innerHTML = aiResponse.summary ? aiResponse.summary.replace(/\n/g, '<br>') : "분석 완료";
        }
    } catch (error) {
        outputDiv.innerHTML = `❌ 오류: ${error.message}<br>잠시 후 다시 시도해주세요.`;
    }
}
