// [1] 서비스 워커 등록
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./service-worker.js')
            .then(reg => console.log('서비스 워커 등록 성공:', reg.scope))
            .catch(err => console.log('서비스 워커 등록 실패:', err));
    });
}

// [2] 기상청 실시간 날씨 (기존 유지)
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
    } catch (error) {
        console.error("날씨 호출 오류:", error);
    }
}

// [3] AI 영양사 분석
async function askAI() {
    const outputDiv = document.getElementById('ai-output');
    if (!outputDiv) return;

    // 화면에 보이는 식단 카드들만 가져오기
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
        
        const response = await fetch(workerUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ mealData: currentMeal })
        });

        let data = null;

        try {
            data = await response.json();
        } catch (jsonError) {
            data = null;
        }

        // 상태 코드별 오류 메시지 처리
        if (!response.ok) {
            if (response.status === 429) {
                throw new Error("오늘 AI 영양사 호출 횟수를 모두 소진하였습니다.");
            }

            if (response.status === 400) {
                throw new Error("식단 정보를 분석할 수 없습니다. 식단 내용을 확인한 뒤 다시 시도해주세요.");
            }

            if (response.status === 404) {
                throw new Error("AI 분석 서버를 찾을 수 없습니다. 관리자에게 문의해주세요.");
            }

            if (response.status >= 500) {
                throw new Error("AI 분석 서버에 문제가 발생했습니다. 잠시 후 다시 시도해주세요.");
            }

            const errorDetail = data?.error?.message || data?.error || `알 수 없는 오류가 발생했습니다. 오류 코드: ${response.status}`;
            throw new Error(errorDetail);
        }

        if (data && data.candidates && data.candidates[0]) {
            let rawText = data.candidates[0].content.parts[0].text;
            
            // JSON 형식만 추출 (AI가 앞뒤에 설명을 붙일 경우 대비)
            const jsonMatch = rawText.match(/\{[\s\S]*\}/);
            const aiResponse = JSON.parse(jsonMatch ? jsonMatch[0] : rawText);

            // 알레르기 아이콘 매핑 로직
            visibleCards.forEach(card => {
                const oldIconGroup = card.querySelector('.allergy-icon-group');
                if (oldIconGroup) oldIconGroup.remove();

                const nameText = card.querySelector('.menu-name-text').innerText.trim();
                const matchingKey = Object.keys(aiResponse.allergy_map).find(key => 
                    nameText.includes(key) || key.includes(nameText)
                );

                const allergyDataList = matchingKey ? aiResponse.allergy_map[matchingKey] : [];

                if (allergyDataList.length > 0) {
                    const iconContainer = card.querySelector('.allergy-icon-container');

                    if (iconContainer) {
                        const group = document.createElement('div');
                        group.className = 'allergy-icon-group flex gap-1';

                        const fullAllergyInfo = allergyDataList
                            .map(item => `${item.emoji}:${item.name} (${item.code}번)`)
                            .join('\n');

                        allergyDataList.forEach(item => {
                            const icon = document.createElement('span');
                            icon.className = 'allergy-icon cursor-pointer bg-gray-100 rounded px-1 transition-transform active:scale-95';
                            icon.innerText = item.emoji;
                            
                            icon.onclick = (e) => {
                                e.stopPropagation();
                                alert(fullAllergyInfo);
                            };

                            group.appendChild(icon);
                        });

                        iconContainer.appendChild(group);
                    }
                }
            });

            // 결과 텍스트 출력
            outputDiv.innerHTML = aiResponse.summary ? aiResponse.summary.replace(/\n/g, '<br>') : "분석 완료";
        } else {
            throw new Error("AI가 분석 데이터를 보내지 못했습니다.");
        }
    } catch (error) {
        console.error("AI 호출 오류 상세:", error);
        outputDiv.innerHTML = error.message;
    }
}

function clearAIResults() {
    const outputDiv = document.getElementById('ai-output');

    if (outputDiv) {
        outputDiv.innerHTML = "✨ 분석 버튼을 누르면 AI 영양사가 분석을 시작합니다.";
    }

    document.querySelectorAll('.allergy-icon-group').forEach(group => group.remove());
}

window.addEventListener('DOMContentLoaded', () => {
    fetchRealtimeWeather();
});
