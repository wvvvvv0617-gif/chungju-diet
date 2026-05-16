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

// [3] AI 영양사 및 알레르기 분석 (모든 메뉴 분석 및 매칭 강화 버전)
async function askAI() {
    const outputDiv = document.getElementById('ai-output');
    if (!outputDiv) return;

    let menuNames = [];
    try {
        const menuItems = document.querySelectorAll('.menu-name-text');
        if (menuItems.length > 0) {
            // 현재 화면에 표시된 메뉴 이름들을 배열로 수집
            menuNames = Array.from(menuItems).map(el => el.innerText.trim());
        }
    } catch (e) { console.error("데이터 수집 실패:", e); }

    if (menuNames.length === 0) {
        outputDiv.innerHTML = "❌ 분석할 식단 정보가 없습니다.";
        return;
    }

    const currentMeal = menuNames.join(', ');
    outputDiv.innerHTML = "✨ AI 영양사가 현재 식단을 분석 중입니다...";

    try {
        const workerUrl = 'https://gemini-proxy.wvvvvv0617.workers.dev';
        
        // AI에게 모든 메뉴를 개별적으로 분석하도록 지시 (프롬프트 강화)
        const systemInstruction = `
            당신은 학교 영양사입니다. 다음 [식단 리스트]의 **모든 메뉴**를 하나도 빠짐없이 분석하세요.
            [식단 리스트]: ${currentMeal}

            [작성 지침]:
            1. 제공된 식단 리스트의 **각 메뉴명을 키(key)**로 하여 알레르기 성분이 있으면 해당 이모지를, 없으면 빈 문자열("")을 넣으세요.
            2. 학교 매점 제품(스낵, 음료 등)으로 보충할 영양 조언과 상황에 맞는 운동(걷기, 러닝, 근력 운동 중 하나)을 추천하세요.
            3. 답변 마지막은 "알레르기에 대한 내용은 식단에 알레르기 정보를 표기해놓았으니 확인 바랍니다."로 끝내세요.

            [알레르기 이모지 가이드]:
            난류: 🥚, 우유: 🥛, 메밀: 🌾, 땅콩: 🥜, 대두: 🫘, 밀: 🌾, 고등어: 🐟, 게: 🦀, 새우: 🦐, 돼지고기: 🐷, 복숭아: 🍑, 토마토: 🍅, 아황산류: 🧪, 호두: 🥜, 닭고기: 🍗, 쇠고기: 🐮, 오징어: 🦑, 조개류: 🐚, 잣: 🌲

            [출력 형식]: 반드시 아래 JSON 형식으로만 답변하세요.
            {"allergy_map": {"메뉴명": "이모지"}, "summary": "영양 조언 및 운동 추천"}
        `;

        const response = await fetch(workerUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{ parts: [{ text: systemInstruction }] }]
            })
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.error || `서버 오류 ${response.status}`);

        if (data && data.candidates && data.candidates[0]) {
            let rawText = data.candidates[0].content.parts[0].text;
            const jsonMatch = rawText.match(/\{[\s\S]*\}/);
            const aiResponse = JSON.parse(jsonMatch ? jsonMatch[0] : rawText);

            // 기존 이모지 초기화 (중복 표시 방지)
            document.querySelectorAll('.allergy-icon').forEach(icon => icon.remove());
            
            if (aiResponse.allergy_map) {
                const mealCards = document.querySelectorAll('.meal-item-card'); 
                mealCards.forEach(card => {
                    const nameText = card.querySelector('.menu-name-text').innerText.trim();
                    
                    // 유연한 매칭: AI가 준 키값이 현재 메뉴명에 포함되거나 그 반대인 경우 매칭
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
            }
            outputDiv.innerHTML = aiResponse.summary ? aiResponse.summary.replace(/\n/g, '<br>') : "분석 완료";
        }
    } catch (error) {
        outputDiv.innerHTML = `❌ 오류: ${error.message}<br>잠시 후 다시 시도해주세요.`;
    }
}

// [4] 날짜 변경 시 결과를 초기화하는 함수 (화살표 클릭 이벤트에 이 함수를 연결하세요)
function clearAIResults() {
    const outputDiv = document.getElementById('ai-output');
    if (outputDiv) {
        outputDiv.innerHTML = "✨ 분석 버튼을 누르면 AI 영양사가 분석을 시작합니다.";
    }
    document.querySelectorAll('.allergy-icon').forEach(icon => icon.remove());
}
