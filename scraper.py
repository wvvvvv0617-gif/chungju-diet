import json
import requests
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
        rain_prob = data.get("clouds", {}).get("all", 0)
        if "rain" in data: rain_prob = 80
        return {"temp": temp, "rain": rain_prob}
    except:
        return {"temp": None, "rain": None}

# =========================
# 🍱 영양 성분 스마트 추정 (개선됨 + 칼로리 추가)
# =========================
def estimate_nutrition(menu_text):
    """
    메뉴 텍스트를 분석하여 영양 성분 및 칼로리를 추정합니다.
    """
    if not menu_text or "식단 없음" in menu_text or len(menu_text) < 3:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0, "calories": 0}

    # 기본 베이스값 (평균적인 한식 식단)
    base = {"carbs": 60, "protein": 20, "fat": 15, "sugar": 5}

    # 키워드별 가중치 설정
    if any(k in menu_text for k in ["고기", "제육", "불고기", "닭", "치킨", "생선", "계란", "돈가스", "함박"]):
        base["protein"] += 15
        base["fat"] += 10
        base["carbs"] -= 5
    
    if any(k in menu_text for k in ["비빔밥", "국수", "우동", "빵", "떡볶이", "덮밥", "볶음밥"]):
        base["carbs"] += 20
        base["sugar"] += 8
    
    if any(k in menu_text for k in ["샐러드", "나물", "무침", "요거트"]):
        base["carbs"] -= 10
        base["fat"] -= 5
        base["protein"] += 5

    # 수치 제한 (5~95 사이)
    for key in base:
        base[key] = max(5, min(95, base[key]))
        
    # 🔥 칼로리 계산 로직 추가 (탄수화물*4 + 단백질*4 + 지방*9)
    # 한 끼 식사 베이스 칼로리 약 300kcal + 영양소별 합산
    base["calories"] = (base["carbs"] * 4) + (base["protein"] * 4) + (base["fat"] * 9) + 200
        
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

        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

        print("🚀 data.json 갱신 완료!")

    except Exception as e:
        print(f"❌ 크롤링 중 오류 발생: {e}")

if __name__ == "__main__":
    crawl()
