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

// [3] AI 영양사 및 알레르기 분석 (현재 화면 식단 매칭 및 캐싱 최적화 버전)
async function askAI() {
    const outputDiv = document.getElementById('ai-output');
    if (!outputDiv) return;

    // 현재 화면에 실제로 보이는(Visible) 메뉴 카드들만 수집 (날짜 변경 대응)
    const visibleCards = Array.from(document.querySelectorAll('.meal-item-card'))
                              .filter(card => card.offsetParent !== null);

    if (visibleCards.length === 0) {
        outputDiv.innerHTML = "❌ 분석할 식단 정보가 없습니다.";
        return;
    }

    const menuNames = visibleCards.map(card => card.querySelector('.menu-name-text').innerText.trim());
    const currentMeal = menuNames.join(', ');
    
    outputDiv.innerHTML = "✨ AI 영양사가 분석 중입니다...";

    try {
        const workerUrl = 'https://gemini-proxy.wvvvvv0617.workers.dev';
        
        const systemInstruction = `당신은 학교 영양사입니다. 다음 [식단 리스트]의 모든 메뉴를 분석하세요.
[식단 리스트]: ${currentMeal}

[작성 지침]:
1. 식단 리스트의 각 메뉴명을 키(key)로 하여 알레르기 이모지 맵을 만드세요. 성분이 없으면 빈 문자열("")을 넣으세요.
2. 매점 제품 보충 조언과 운동 추천을 포함하세요.
3. 답변 마지막은 "알레르기에 대한 내용은 식단에 알레르기 정보를 표기해놓았으니 확인 바랍니다."로 끝내세요.

[알레르기 가이드]: 난류:🥚,우유:🥛,메밀:🌾,땅콩:🥜,대두:🫘,밀:🌾,고등어:🐟,게:🦀,새우:🦐,돼지:🐷,복숭아:🍑,토마토:🍅,아황산:🧪,호두:🥜,닭:🍗,소:🐮,오징어:🦑,조개류:🐚,잣:🌲

[출력 형식]: 반드시 아래 JSON 형식으로만 답변하세요.
{"allergy_map": {"메뉴명": "이모지"}, "summary": "내용"}`;

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

            // 현재 보이는 카드의 이모지만 초기화 후 다시 표시
            visibleCards.forEach(card => {
                const oldIcon = card.querySelector('.allergy-icon');
                if (oldIcon) oldIcon.remove();

                const nameText = card.querySelector('.menu-name-text').innerText.trim();
                
                // 유연한 매칭 (AI 응답 키와 화면 메뉴명 비교)
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
            outputDiv.innerHTML = aiResponse.summary ? aiResponse.summary.replace(/\n/g, '<br>') : "분석 완료";
        }
    } catch (error) {
        outputDiv.innerHTML = `❌ 오류: ${error.message}<br>잠시 후 다시 시도해주세요.`;
    }
}

// [4] 날짜 변경 시 결과를 초기화하는 함수
// HTML의 날짜 이동 화살표 클릭 이벤트 리스너에 clearAIResults()를 추가해 주세요.
function clearAIResults() {
    const outputDiv = document.getElementById('ai-output');
    if (outputDiv) {
        outputDiv.innerHTML = "✨ 분석 버튼을 누르면 AI 영양사가 분석을 시작합니다.";
    }
    document.querySelectorAll('.allergy-icon').forEach(icon => icon.remove());
}
