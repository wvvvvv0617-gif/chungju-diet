import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# =========================
# ⏰ 한국 시간
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
# 🌦️ OpenWeather
# =========================
def get_weather():
    try:
        API_KEY = "여기에_너_API_KEY"

        url = f"https://api.openweathermap.org/data/2.5/weather?q=Chungju,KR&appid={API_KEY}&units=metric&lang=kr"
        res = requests.get(url)
        data = res.json()

        # 기온
        temp = round(data["main"]["temp"])

        # 강수 확률 느낌으로 변환 (안정형)
        rain = 0

        # 비가 실제로 내리는 경우
        if "rain" in data and "1h" in data["rain"]:
            rain = min(int(data["rain"]["1h"] * 20), 100)

        # 눈도 고려 (겨울 대비)
        if "snow" in data and "1h" in data["snow"]:
            rain = min(int(data["snow"]["1h"] * 20), 100)

        # 날씨 상태 기반 보정 (비 안와도 흐리면 약간 줌)
        weather_main = data["weather"][0]["main"]
        if rain == 0:
            if weather_main in ["Clouds"]:
                rain = 20
            elif weather_main in ["Rain", "Drizzle", "Thunderstorm"]:
                rain = 60

        return {
            "temp": temp,
            "rain": rain
        }

    except Exception as e:
        print("❌ OpenWeather 오류:", e)
        return {
            "temp": 22,
            "rain": 0
        }

# =========================
# 🍱 영양 추정
# =========================
def estimate(text):
    if not text or len(text) < 5 or "식단 없음" in text:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0}
    return {"carbs": 72, "protein": 24, "fat": 14, "sugar": 5}

# =========================
# 🕷️ 식단 크롤링
# =========================
def crawl():
    target_date = get_target_date()
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"

    print(f"🔗 데이터 수집 중: {url}")

    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    meal_result = {}
    days_list = ["월", "화", "수", "목", "금"]

    for row in soup.find_all("tr"):
        cols = row.find_all(["td", "th"])
        if len(cols) < 4:
            continue

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

    print("🚀 데이터 갱신 완료!")

if __name__ == "__main__":
    crawl()
