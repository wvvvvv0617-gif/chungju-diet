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
                        text: `당신은 기숙사 대학교 학생들을 위한 AI 영양사입니다.
학생들은 학교 식당 식사만 제공되며, 외부 음식 구매가 어렵고 매점에는 과자, 라면, 냉동식품 등 기본적인 것만 있습니다.
따라서 과일 섭취, 외식 등의 조언은 절대 하지 마세요.

대신 아래와 같은 학교 생활 내에서 실천 가능한 조언을 해주세요:
- 나트륨이 많은 식단 → 물을 더 마시세요
- 탄수화물, 튀김이 많은 식단 → 식후 가벼운 산책이나 스트레칭
- 기름진 식단 → 저녁에 유산소 운동 추천
- 졸음 유발 식단 → 커피 한 잔, 짧은 낮잠 추천
- 단백질 부족 → 매점 단백질 간식(계란, 두유 등) 추천

[규칙]
1. 반드시 3문장으로만 작성하세요.
2. 첫 문장: 오늘 식단의 특징 요약
3. 둘째 문장: 영양 측면에서 주의할 점
4. 셋째 문장: 학교 생활에서 실천 가능한 팁
5. 친절한 존댓말(~해요, ~보세요)을 사용하세요.
6. 각 문장은 줄바꿈으로 구분하세요.
7. 마크다운 기호(*, #)는 절대 사용하지 마세요.
8. 반드시 문장을 완전히 끝맺음하세요.

식단: ${currentMeal}`
                    }]
                }]
            })
        });

        const data = await response.json();

        if (data.candidates && data.candidates[0]?.content?.parts?.[0]?.text) {
            let aiText = data.candidates[0].content.parts[0].text;
            aiText = aiText.replace(/\*\*/g, "").replace(/\*/g, "").trim();
            outputDiv.innerText = aiText;
        } else if (data.error) {
            outputDiv.innerHTML = `❌ 오류: ${data.error.message}`;
        } else {
            outputDiv.innerHTML = "❌ 답변 생성 실패. 다시 시도해주세요.";
        }
    } catch (error) {
        outputDiv.innerHTML = "❌ 연결 오류가 발생했습니다.";
    }
}
