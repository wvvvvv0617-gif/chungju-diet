// [1] 서비스 워커 등록 로직 (PWA 설치 버튼 활성화 필수 조건)
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

    // data.json에서 직접 식단 텍스트 추출 (주말/휴식화면에서도 동작)
    let currentMeal = "";

    try {
        const res = await fetch('data.json?v=' + Date.now());
        const menuData = await res.json();

        const now = new Date();
        const todayDay = now.getDay();
        const days = ["일", "월", "화", "수", "목", "금", "토"];

        // 주말이면 월요일, 평일이면 오늘 요일 기준
        let targetDay;
        if (todayDay === 0 || todayDay === 6) {
            targetDay = "월";
        } else {
            targetDay = days[todayDay];
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
                        text: `식단: ${currentMeal}. 이 식단을 영양학적으로 분석해서 100자 이내로 친절하고 짧게 조언해줘.`
                    }]
                }]
            })
        });

        const data = await response.json();
        console.log("Gemini 응답:", JSON.stringify(data));

        if (data.candidates && data.candidates[0]?.content?.parts?.[0]?.text) {
            outputDiv.innerHTML = data.candidates[0].content.parts[0].text;
        } else if (data.error) {
            console.error("API 에러:", data.error);
            outputDiv.innerHTML = `❌ 오류: ${data.error.message}`;
        } else {
            outputDiv.innerHTML = "❌ AI가 답변을 생성하지 못했습니다. 다시 시도해주세요.";
        }
    } catch (error) {
        console.error("AI 요청 에러:", error);
        outputDiv.innerHTML = "❌ 연결 오류가 발생했습니다. 네트워크 상태를 확인해주세요.";
    }
}
