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

    let currentMeal = "";

    try {
        const res = await fetch('data.json?v=' + Date.now());
        const menuData = await res.json();

        // 화면 텍스트에서 현재 선택된 요일을 인식
        const pageText = document.body.innerText;
        let targetDay = "";
        
        if (pageText.includes("월요일")) targetDay = "월";
        else if (pageText.includes("화요일")) targetDay = "화";
        else if (pageText.includes("수요일")) targetDay = "수";
        else if (pageText.includes("목요일")) targetDay = "목";
        else if (pageText.includes("금요일")) targetDay = "금";

        // 요일 인식 실패 시 오늘 요일 기준
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

    outputDiv.innerHTML = "✨ AI 영양사가 캠퍼스 식단을 분석 중입니다...";

    // ... (앞부분 생략)
    try {
        const response = await fetch('https://gemini-proxy.wvvvvv0617.workers.dev', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{
                    role: "user",
                    parts: [{
                        text: `당신은 충주캠퍼스 학생들을 위한 친절한 AI 영양사입니다. 
입력받은 식단 데이터를 바탕으로 다음 규칙에 맞춰 조언해 주세요:

1. 형식: 
   [오늘의 식단 요약]
   내용...
   
   [영양 밸런스 체크]
   내용...
   
   [현실적인 실천 팁]
   내용...

2. 주의사항:
   - 과일 섭취 같은 비현실적 조언은 금지입니다.
   - 서론 없이 바로 본론([오늘의 식단 요약] )으로 시작하세요.
   - 답변은 총 250자 내외로 상세하고 친절하게 작성하세요.
   - 문단 사이에는 빈 줄을 넣어 가독성을 높여주세요.

3. 실천 팁 참고:
   - 지방 과다: "저녁 먹고 운동장 한 바퀴 산책 어때요?"
   - 나트륨 과다: "매점에서 생수 한 병 사서 수분 보충하세요."
   - 단백질 부족: "매점에서 우유나 두유 한 팩 추천해요."
   - 탄수화물 과다: "오후 수업 졸음 주의! 매점 아메리카노 추천해요."

식단 데이터: ${currentMeal}`
                    }]
                }]
            })
        });

        const data = await response.json();

        if (data.candidates && data.candidates[0]?.content?.parts?.[0]?.text) {
            outputDiv.innerHTML = data.candidates[0].content.parts[0].text;
        } else if (data.error) {
            outputDiv.innerHTML = `❌ 오류: ${data.error.message}`;
        } else {
            outputDiv.innerHTML = "❌ AI가 답변을 생성하지 못했습니다. 다시 시도해주세요.";
        }
    } catch (error) {
        outputDiv.innerHTML = "❌ 연결 오류가 발생했습니다. 네트워크 상태를 확인해주세요.";
    }
}
