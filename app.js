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
   - [오늘의 식단 요약] (한 줄 )
   - [영양 밸런스 체크] (지방, 단백질, 나트륨 위주 분석)
   - [현실적인 실천 팁] (실행 가능한 조언)

2. 주의사항:
   - 과일 섭취처럼 학교에서 지키기 어려운 조언은 절대 하지 마세요.
   - 매점에는 냉동식품, 커피, 간식만 있다는 점을 참고하세요.
   - 운동 조언은 학교 운동장 산책이나 체육관 활용 등 현실적인 내용을 포함하세요.
   - 말투는 친근하게 (~해요, ~어떨까요?) 작성하고, 3~4문장 정도로 핵심만 적어주세요.

3. 실천 팁 참고 예시:
   - 지방 과다: "오늘 먹은 기름진 메뉴는 저녁 먹고 운동장 한 바퀴 산책하며 가볍게 유산소 운동으로 날려버리는 거 어때요?"
   - 나트륨 과다: "국물 요리가 짭짤했으니 매점에서 생수 한 병 사서 수분을 충분히 보충해 주는 게 좋겠어요."
   - 단백질 부족: "성장기엔 단백질이 중요하니 매점에서 우유나 두유 한 팩으로 보충해 보는 건 어떨까요?"
   - 탄수화물 과다: "든든한 식사네요! 오후 수업 때 졸음이 올 수 있으니 매점 아메리카노 한 잔의 여유를 추천해요."

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
