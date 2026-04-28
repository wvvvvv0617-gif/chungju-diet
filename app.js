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
