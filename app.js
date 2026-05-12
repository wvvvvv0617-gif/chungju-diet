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

        // 요일 인식 로직
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
                        text: `충주캠 학생들을 위한 AI 영양사로서 다음 식단을 딱 3문장으로 조언해 주세요.

[규칙]
1. [식단 요약], [영양 평가], [간단 팁]으로 나누어 한 문장씩 작성하세요.
2. 반드시 "~해요", "~보세요"와 같은 친절한 존댓말을 사용하세요.
3. 총 150자 내외로 아주 짧게 핵심만 전달하고 문장을 반드시 끝맺음하세요.

식단: ${currentMeal}`
                    }]
                }]
            })
        });

        const data = await response.json();

        if (data.candidates && data.candidates[0]?.content?.parts?.[0]?.text) {
            let aiText = data.candidates[0].content.parts[0].text;
            
            // 가독성을 해치는 마크다운 별표 제거
            aiText = aiText.replace(/\*\*/g, "").trim();

            // innerText 사용으로 줄바꿈 보존 및 텍스트 짤림 현상 방지
            outputDiv.innerText = aiText;

            // 스크린샷 null 에러 방지: 요소 존재 여부 확인 후 별점 렌더링
            if (typeof renderRatingSection === 'function') {
                try {
                    const ratingTarget = document.getElementById('ai-rating'); // 실제 별점 요소 ID 확인 필요
                    if (ratingTarget) renderRatingSection(aiText);
                } catch (e) {
                    console.warn("별점 표시 실패:", e);
                }
            }

        } else if (data.error) {
            outputDiv.innerHTML = `❌ 오류: ${data.error.message}`;
        } else {
            outputDiv.innerHTML = "❌ 답변 생성 실패. 다시 시도해주세요.";
        }
    } catch (error) {
        outputDiv.innerHTML = "❌ 연결 오류가 발생했습니다.";
    }
}
