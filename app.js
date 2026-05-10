// [1] 서비스 워커 등록 로직 (PWA 설치 버튼 활성화 필수 조건)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./service-worker.js')
            .then(reg => console.log('서비스 워커 등록 성공:', reg.scope))
            .catch(err => console.log('서비스 워커 등록 실패:', err));
    });
}

// [2] 데이터 로드 및 화면 표시 로직
fetch(`data.json?v=${new Date().getTime()}`)
    .then(res => res.json())
    .then(data => {
        const result = getMeal(data);

        // 데이터가 없을 경우를 대비해 '정보 없음' 처리를 강화했습니다.
        document.getElementById("meal").innerText =
            result.data || "식단 정보가 없습니다.";

        document.getElementById("carb").innerText = result.nutrition?.carbs ?? 0;
        document.getElementById("protein").innerText = result.nutrition?.protein ?? 0;
        document.getElementById("fat").innerText = result.nutrition?.fat ?? 0;
        document.getElementById("sugar").innerText = result.nutrition?.sugar ?? 0;
    })
    .catch(err => {
        document.getElementById("meal").innerText = "데이터 로드 실패";
        console.error(err);
    });

// [3] 시간대별 식단 선택 함수
function getMeal(data) {
    const now = new Date();
    const day = now.getDay();
    const time = now.getHours() * 60 + now.getMinutes();

    const LUNCH = 13 * 60 + 30;
    const DINNER = 18 * 60 + 30;

    const days = ["일", "월", "화", "수", "목", "금", "토"];

    // 금요일 저녁 → 월요일 식단 미리 보기
    if (day === 5 && time >= DINNER) {
        return {
            data: data["월"]?.breakfast,
            nutrition: data["월"]?.nutrition
        };
    }

    // 주말 → 월요일 식단 미리 보기
    if (day === 6 || day === 0) {
        return {
            data: data["월"]?.breakfast,
            nutrition: data["월"]?.nutrition
        };
    }

    const d = days[day];

    if (time >= DINNER) return { data: data[d]?.dinner, nutrition: data[d]?.nutrition };
    if (time >= LUNCH) return { data: data[d]?.lunch, nutrition: data[d]?.nutrition };

    return { data: data[d]?.breakfast, nutrition: data[d]?.nutrition };
}

// [4] AI 영양사 조언 기능 (최종 완성 버전)
async function askAI() {
    const outputDiv = document.getElementById('ai-output');
    
    if (!outputDiv) {
        console.error("ai-output 요소를 찾을 수 없습니다.");
        return;
    }

    // [중요 수정] 화면에 나열된 모든 메뉴 리스트(쌀밥, 국 등)를 한꺼번에 읽어옵니다.
    const menuElements = document.querySelectorAll('li span, .menu-item'); 
    let currentMeal = Array.from(menuElements).map(el => el.innerText.trim()).filter(text => text.length > 0).join(', ');

    // 식단 정보가 제대로 로드되지 않았을 때의 처리
    if (!currentMeal || currentMeal.length < 5) {
        outputDiv.innerHTML = "❌ 분석할 식단 정보가 아직 로드되지 않았습니다. 잠시 후 다시 시도해주세요.";
        return;
    }

    const apiKey = 'AIzaSyC7ogfiYSF1GXCCBltcyNXP9TgrBe-E-SI'; 
    outputDiv.innerHTML = "✨ AI 영양사가 식단을 분석 중입니다...";

    try {
        const response = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                contents: [{
                    parts: [{
                        text: `식단: ${currentMeal}. 이 식단을 영양학적으로 분석해서 100자 이내로 친절하고 짧게 조언해줘.`
                    }]
                }]
            })
        });

        const data = await response.json();
        
        if (data.candidates && data.candidates[0].content.parts[0].text) {
            outputDiv.innerHTML = data.candidates[0].content.parts[0].text;
        } else {
            outputDiv.innerHTML = "❌ AI가 답변을 생성하지 못했습니다. 다시 시도해주세요.";
        }
    } catch (error) {
        console.error("AI 요청 에러:", error);
        outputDiv.innerHTML = "❌ 연결 오류가 발생했습니다. 네트워크 상태를 확인해주세요.";
    }
}
