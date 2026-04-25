import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_target_date():
    """한국 시간 기준, 주말이나 금요일 저녁이면 다음 주 식단 페이지를 타겟팅합니다."""
    now = datetime.utcnow() + timedelta(hours=9)
    weekday = now.weekday()
    hour_minute = now.hour * 100 + now.minute

    # 금요일 18:30 이후이거나 토/일요일인 경우 다음 주 월요일 날짜 반환
    if (weekday == 4 and hour_minute >= 1830) or weekday >= 5:
        days_to_monday = (7 - weekday) % 7
        if days_to_monday == 0: days_to_monday = 7
        target = now + timedelta(days=days_to_monday)
    else:
        target = now
    return target.strftime("%Y-%m-%d")

def get_chungju_weather():
    """네이버에서 충주시 실시간 기온을 가져옵니다."""
    try:
        url = "https://search.naver.com/search.naver?query=충주시+날씨"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")
        # 현재 온도 숫자만 추출
        temp = soup.select_one('.temperature_text strong').text.replace('현재 온도', '').replace('°', '').strip()
        return temp
    except Exception as e:
        print(f"❌ 날씨 크롤링 에러: {e}")
        return "22"

def estimate(text):
    if not text or len(text) < 5 or "식단 없음" in text:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0}
    return {"carbs": 72, "protein": 24, "fat": 14, "sugar": 5}

def crawl():
    target_date = get_target_date()
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    
    print(f"🔗 데이터 수집 중: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    meal_result = {}
    rows = soup.find_all("tr")
    days_list = ["월", "화", "수", "목", "금"]

    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 4: continue
        
        header = cols[0].get_text(strip=True)
        for d in days_list:
            if d in header:
                menus = []
                for i in range(1, 4):
                    txt = " ".join(cols[i].get_text(" ", strip=True).split())
                    menus.append(txt if len(txt) > 3 and "등록된" not in txt else "식단 없음")
                
                meal_result[d] = {
                    "breakfast": menus[0],
                    "lunch": menus[1],
                    "dinner": menus[2],
                    "nutrition": estimate(" ".join(menus))
                }
                print(f"✅ {d}요일 데이터 수집 완료")

    # 최종 결과물 구조화
    final_data = {
        "weather": {
            "temp": get_chungju_weather(),
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M")
        },
        "meals": meal_result
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print("🚀 모든 데이터 갱신 완료!")

if __name__ == "__main__":
    crawl()
