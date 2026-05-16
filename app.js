// [1] 서비스 워커 등록 로직
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./service-worker.js')
            .then(reg => console.log('서비스 워커 등록 성공:', reg.scope))
            .catch(err => console.log('서비스 워커 등록 실패:', err));
    });
}

// [2] 기상청 실시간 날씨 가져오기 기능
const WEATHER_API_KEY = "__KMA_API_KEY__"; // 기상청에서 발급받은 서비스키(Decoding/Encoding 중 맞는 것 사용)
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

// [4] AI 영양사 조언 기능
async function askAI() {
    const outputDiv = document.getElementById('ai-output');

    if (!outputDiv) {
        console.error("ai-output 요소를 찾을 수 없습니다.");
        return;
    }

    let currentMeal = "";

    try {
        const res = await fetch('data.json?v=' + Date.now());
        const menuData = await res.json();

        const pageText = document.body.innerText;
        let targetDay = "";

        // 현재 화면에 표시된 요일을 텍스트에서 추출
        if (pageText.includes("월요일")) targetDay = "월";
        else if (pageText.includes("화요일")) targetDay = "화";
        else if (pageText.includes("수요일")) targetDay = "수";
        else if (pageText.includes("목요일")) targetDay = "목";
        else if (pageText.includes("금요일")) targetDay = "금";

        if (!targetDay) {
            const now = new Date();
            const todayDay = now.getDay();
            const days = ["일", "월", "화", "수", "목", "금", "토"];
            targetDay = (todayDay === 0 || todayDay === 6) ? "월" : days[todayDay];
        }

        const mealData = menuData.mealsByDate ? 
            menuData.mealsByDate[new Date().toISOString().split('T')[0]] : 
            (menuData.meals ? menuData.meals[targetDay] : null);

        if (mealData) {
            const allMenus = [
                mealData.breakfast || "",
                mealData.lunch || "",
                mealData.dinner || ""
            ].filter(m => m && m.length > 3 && !m.includes("식단 없음"));

            currentMeal = allMenus.join(', ');
        }
    } catch (e) {
        console.error("식단 데이터 로드 실패:", e);
    }

    if (!currentMeal || currentMeal.length < 5) {
        outputDiv.innerHTML = "❌ 분석할 식단 정보가 없습니다.";
        return;
    }

    outputDiv.innerHTML = "✨ AI 영양사가 식단을 분석 중입니다...";

    try {
        const response = await fetch('https://gemini-proxy.wvvvvv0617.workers.dev', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: `기숙사 대학생을 위한 AI 영양사로서 오늘 식단을 분석해줘. 외부 음식 구매가 어려우니 과일, 외식 추천은 하지 마. 나트륨이 많으면 물 많이 마시기, 튀김이 많으면 산책, 졸음 유발 식단이면 커피 추천처럼 학교 생활에서 실천 가능한 팁을 줘. 반드시 3문장으로 끝내고 각 문장은 줄바꿈으로 구분해. 마크다운 기호는 사용하지 마. 반드시 문장을 완전히 끝맺음해.\n\n식단: ${currentMeal}`
                    }]
                }]
            })
        });

        const data = await response.json();
        const aiPart = data.candidates?.[0]?.content?.parts?.[0]?.text;

        if (aiPart) {
            let aiText = aiPart.replace(/\*\*/g, "").replace(/\*/g, "").trim();
            outputDiv.innerHTML = aiText.replace(/\n/g, '<br>');
            outputDiv.style.textAlign = 'left';
        } else {
            outputDiv.innerHTML = "❌ 답변 생성 실패. 다시 시도해주세요.";
        }
    } catch (error) {
        console.error("연결 오류:", error);
        outputDiv.innerHTML = "❌ 연결 오류가 발생했습니다.";
    }
}
