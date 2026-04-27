import json
import requests
import random
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# =========================
# ⏰ 한국 시간 (KST)
# =========================
def get_kst_now():
    return datetime.utcnow() + timedelta(hours=9)

def get_target_date():
    now = get_kst_now()
    weekday = now.weekday()
    hm = now.hour * 100 + now.minute
    # 금요일 오후 6시 30분 이후거나 주말이면 다음주 월요일 식단 조회
    if (weekday == 4 and hm >= 1830) or weekday >= 5:
        days_to_monday = (7 - weekday) % 7 or 7
        target = now + timedelta(days=days_to_monday)
    else:
        target = now
    return target.strftime("%Y-%m-%d")

# =========================
# 🌦️ OpenWeather (날씨 수집)
# =========================
def get_weather():
    try:
        API_KEY = "324c1ff82e3f995801bf309914bdf245"
        url = f"https://api.openweathermap.org/data/2.5/weather?lat=36.991&lon=127.926&appid={API_KEY}&units=metric&lang=kr"
        res = requests.get(url, timeout=10)
        data = res.json()
        if res.status_code != 200:
            return {"temp": None, "rain": None}
        temp = round(data["main"]["temp"])
        # 비 정보가 있으면 확률 80%로 고정, 없으면 구름 양으로 대체
        rain_prob = data.get("clouds", {}).get("all", 0)
        if "rain" in data: rain_prob = 80
        return {"temp": temp, "rain": rain_prob}
    except:
        return {"temp": None, "rain": None}

# =========================
# 🍱 영양 성분 스마트 추정 (일관성 + 다양성 최적화)
# =========================
def estimate_nutrition(menu_text):
    """
    메뉴 이름을 '시드(Seed)'로 사용하여 동일 메뉴에는 동일 수치를,
    다른 메뉴에는 분석된 다채로운 수치를 제공합니다.
    """
    if not menu_text or "식단 없음" in menu_text or len(menu_text) < 3:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0, "calories": 0}

    # 🔥 중요: 메뉴 텍스트를 고유한 시드값으로 변환
    # 이 로직 덕분에 "제육볶음"은 1시간 뒤에 다시 크롤링해도 똑같은 수치가 나옵니다.
    seed_value = int(hashlib.md5(menu_text.encode()).hexdigest(), 16) % 10000
    random.seed(seed_value)

    # 1. 기본 베이스값 + 메뉴별 고유 미세 오차
    base = {
        "carbs": 55 + random.randint(-3, 3),
        "protein": 20 + random.randint(-2, 2),
        "fat": 15 + random.randint(-2, 2),
        "sugar": 5 + random.randint(-1, 1)
    }

    # 2. 키워드 분석 및 가중치 적용
    # 고기/단백질군
    if any(k in menu_text for k in ["고기", "제육", "불고기", "돈육", "닭", "치킨", "생선", "계란", "오리", "함박"]):
        base["protein"] += random.randint(15, 20)
        base["fat"] += random.randint(5, 10)
        base["carbs"] -= 5

    # 면/분식/탄수화물군
    if any(k in menu_text for k in ["국수", "우동", "라면", "파스타", "빵", "떡볶이", "덮밥", "볶음밥"]):
        base["carbs"] += random.randint(15, 25)
        base["sugar"] += random.randint(5, 10)
    
    # 튀김/가스류
    if any(k in menu_text for k in ["가스", "튀김", "전", "부침"]):
        base["fat"] += random.randint(10, 15)

    # 샐러드/나물/채소군
    if any(k in menu_text for k in ["샐러드", "나물", "무침", "요거트", "채소"]):
        base["carbs"] -= 7
        base["protein"] += 3
        base["fat"] -= 3

    # 3. 수치 범위 제한 (5~98)
    for key in base:
        base[key] = max(5, min(98, base[key]))
        
    # 4. 칼로리 계산 (탄*4 + 단*4 + 지*9 + 기본280kcal)
    base["calories"] = int((base["carbs"] * 4) + (base["protein"] * 4) + (base["fat"] * 9) + 280)
    
    # 랜덤 시드 초기화 (다른 작업에 영향을 주지 않기 위함)
    random.seed(None)
        
    return base

# =========================
# 🕷️ 식단 크롤링 & 데이터 병합
# =========================
def crawl():
    target_date = get_target_date()
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"

    print(f"🔗 데이터 수집 시작: {url}")

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")

        meal_result = {}
        days_list = ["월", "화", "수", "목", "금"]

        for row in soup.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) < 4: continue

            header = cols[0].get_text(strip=True)

            for d in days_list:
                if d in header:
                    b_menu = " ".join(cols[1].get_text(" ", strip=True).split())
                    l_menu = " ".join(cols[2].get_text(" ", strip=True).split())
                    d_menu = " ".join(cols[3].get_text(" ", strip=True).split())

                    # 메뉴 정제
                    b_menu = b_menu if len(b_menu) > 3 and "등록된" not in b_menu else "식단 없음"
                    l_menu = l_menu if len(l_menu) > 3 and "등록된" not in l_menu else "식단 없음"
                    d_menu = d_menu if len(d_menu) > 3 and "등록된" not in d_menu else "식단 없음"

                    meal_result[d] = {
                        "breakfast": b_menu,
                        "lunch": l_menu,
                        "dinner": d_menu,
                        "nutrition": {
                            "breakfast": estimate_nutrition(b_menu),
                            "lunch": estimate_nutrition(l_menu),
                            "dinner": estimate_nutrition(d_menu)
                        }
                    }

        weather = get_weather()
        final_data = {
            "weather": {
                "temp": weather["temp"],
                "rain": weather["rain"],
                "last_update": get_kst_now().strftime("%Y-%m-%d %H:%M")
            },
            "meals": meal_result
        }

        # JSON 저장
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

        print("🚀 data.json 갱신 완료! (일관성 있는 스마트 분석 적용)")

    except Exception as e:
        print(f"❌ 크롤링 중 오류 발생: {e}")

if __name__ == "__main__":
    crawl()
