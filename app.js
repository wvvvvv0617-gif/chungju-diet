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
        if (!response.ok) throw new Error('Network response was not ok');
        
        const data = await response.json();

        if (data.response && data.response.header.resultCode === "00") {
            const items = data.response.body.items.item;
            const currentHourStr = String(now.getHours()).padStart(2, '0') + "00";
            
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

// [4] AI 영양사 분석 및 알레르기 이모지 표시 기능 (최종 수정본)
async function askAI() {
    const outputDiv = document.getElementById('ai-output');
    if (!outputDiv) return;

    let currentMeal = "";
    
    // 1. 식단 데이터 수집
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
    } catch (e) {
        console.error("식단 데이터 로드 실패:", e);
    }

    if (!currentMeal || currentMeal.length < 3) {
        outputDiv.innerHTML = "❌ 분석할 식단 정보가 없습니다. 요일을 확인해주세요.";
        return;
    }

    outputDiv.innerHTML = "✨ AI 영양사가 식단을 분석하고 알레르기 정보를 확인 중입니다...";

    try {
        // [중요] Worker URL 확인
        const response = await fetch('https://gemini-proxy.wvvvvv0617.workers.dev', {
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

        // 2. 데이터 구조 안전하게 파싱
        if (data && data.candidates && data.candidates[0]) {
            let rawText = data.candidates[0].content.parts[0].text;
            
            // AI가 마크다운 형식을 섞어줄 경우를 대비해 JSON만 추출
            const jsonMatch = rawText.match(/\{[\s\S]*\}/);
            const aiResponse = JSON.parse(jsonMatch ? jsonMatch[0] : rawText);

            // 3. 기존에 표시된 이모지 아이콘 제거 (새로고침 효과)
            document.querySelectorAll('.allergy-icon').forEach(icon => icon.remove());

            // 4. 알레르기 이모지 표시 (선택자 정밀화)
            if (aiResponse.allergy_map) {
                // 스크린샷의 UI 구조를 바탕으로 li 또는 span 내부 텍스트 매칭
                const menuItems = document.querySelectorAll('.bg-white.rounded-2xl span, li'); 
                
                menuItems.forEach(el => {
                    const menuName = el.innerText.trim();
                    // 메뉴명이 결과 맵에 존재한다면 이모지 추가
                    if (aiResponse.allergy_map[menuName]) {
                        const emojiSpan = document.createElement('span');
                        emojiSpan.className = 'allergy-icon';
                        emojiSpan.style.marginLeft = '6px';
                        emojiSpan.style.fontSize = '0.9em';
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
                outputDiv.innerHTML = "❌ 분석 결과 텍스트가 없습니다.";
            }

        } else {
            throw new Error("AI 응답 형식이 올바르지 않습니다.");
        }

    } catch (error) {
        console.error("분석 에러:", error);
        outputDiv.innerHTML = `❌ 오류 발생: ${error.message}<br>식단을 다시 확인하거나 잠시 후 시도해주세요.`;
    }
}
