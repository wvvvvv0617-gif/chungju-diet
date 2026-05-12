// [1] 서비스 워커 등록 로직
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./service-worker.js')
            .then(reg => console.log('서비스 워커 등록 성공:', reg.scope))
            .catch(err => console.log('서비스 워커 등록 실패:', err));
    });
}

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

        const meals = menuData.meals ? menuData.meals[targetDay] : null;

        if (meals) {
            const allMenus = [
                meals.breakfast || "",
                meals.lunch || "",
                meals.dinner || ""
            ].filter(m => m && m !== "식단 없음" && m.length > 3);

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
                    role: "user",
                    parts: [{
                        text: `기숙사 대학생을 위한 AI 영양사로서 오늘 식단을 분석해줘. 외부 음식 구매가 어려우니 과일, 외식 추천은 하지 마. 나트륨이 많으면 물 많이 마시기, 튀김이 많으면 산책, 졸음 유발 식단이면 커피 추천처럼 학교 생활에서 실천 가능한 팁을 줘. 반드시 3문장으로 끝내고 각 문장은 줄바꿈으로 구분해. 마크다운 기호는 사용하지 마. 반드시 문장을 완전히 끝맺음해.

식단: ${currentMeal}`
                    }]
                }]
            })
        });

        const data = await response.json();

        if (data.candidates && data.candidates[0]?.content?.parts?.[0]?.text) {
            let aiText = data.candidates[0].content.parts[0].text;
            aiText = aiText.replace(/\*\*/g, "").replace(/\*/g, "").trim();
            outputDiv.innerHTML = aiText.replace(/\n/g, '<br>');
        } else if (data.error) {
            outputDiv.innerHTML = `❌ 오류: ${data.error.message}`;
        } else {
            outputDiv.innerHTML = "❌ 답변 생성 실패. 다시 시도해주세요.";
        }
    } catch (error) {
        outputDiv.innerHTML = "❌ 연결 오류가 발생했습니다.";
    }
}
