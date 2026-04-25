import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# =========================
# ⏰ 한국 시간 (KST)
# =========================
def get_kst_now():
    # UTC 기준 시간에 9시간을 더해 한국 시간을 계산합니다.
    return datetime.utcnow() + timedelta(hours=9)

def get_target_date():
    now = get_kst_now()
    weekday = now.weekday()
    hm = now.hour * 100 + now.minute

    # 금요일 저녁 6시 30분 이후거나 주말이면 다음 주 월요일 식단을 타겟으로 잡습니다.
    if (weekday == 4 and hm >= 1830) or weekday >= 5:
        days_to_monday = (7 - weekday) % 7 or 7
        target = now + timedelta(days=days_to_monday)
    else:
        target = now

    return target.strftime("%Y-%m-%d")

# =========================
# 🌦️ OpenWeather (개선됨)
# =========================
def get_weather():
    try:
        # 발급받으신 API KEY를 여기에 입력하세요.
        API_KEY = "324c1ff82e3f995801bf309914bdf245"

        # 도시 이름(Chungju) 대신 좌표를 사용하면 더 정확한 지역 데이터를 가져옵니다.
        # lat=36.991, lon=127.926 (충주 폴리텍 대학 인근 좌표)
        url = f"https://api.openweathermap.org/data/2.5/weather?lat=36.991&lon=127.926&appid={API_KEY}&units=metric&lang=kr"
        
        res = requests.get(url, timeout=10)
        data = res.json()

        if res.status_code != 200 or "main" not in data:
            print(f"❌ 날씨 API 실패 (상태코드 {res.status_code}):", data.get("message"))
            # [정직한 UI] 실패 시 거짓 데이터를 주지 않고 None을 반환합니다.
            return {"temp": None, "rain": None}

        # 기온 데이터 (소수점 반올림)
        temp = round(data["main"]["temp"])

        # 강수 데이터 추출 로직
        # 1. 실제 비/눈이 내리는 경우 (OpenWeather는 1시간 내 강수량을 mm 단위로 제공)
        rain_val = 0
        if "rain" in data and "1h" in data["rain"]:
            rain_val = data["rain"]["1h"]
        elif "snow" in data and "1h" in data["snow"]:
            rain_val = data["snow"]["1h"]

        # 2. 강수 확률/상태 결정
        # 비가 실제로 오면 확률을 높게 표시하고, 아니면 구름 양(clouds)을 활용합니다.
        if rain_val > 0:
            rain_prob = 80  # 실제 비가 오면 최소 80%로 표시
        else:
            # 비가 안 오면 구름의 양(0~100)을 강수 확률 대신 보여주는 것이 가장 유사합니다.
            rain_prob = data.get("clouds", {}).get("all", 0)

        print(f"🌤️ 수집 완료: {temp}°C / 강수(구름) {rain_prob}%")
        return {"temp": temp, "rain": rain_prob}

    except Exception as e:
        print("❌ OpenWeather 오류:", e)
        return {"temp": None, "rain": None}

# =========================
# 🍱 영양 성분 추정
# =========================
def estimate(text):
    if not text or len(text) < 5 or "식단 없음" in text:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0, "kcal": 0}

    # 현재는 고정값을 반환하지만, 추후 메뉴 키워드에 따른 로직을 추가할 수 있습니다.
    return {"carbs": 72, "protein": 24, "fat": 14, "sugar": 5, "kcal": 800}

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
            if len(cols) < 4:
                continue

            header = cols[0].get_text(strip=True)

            for d in days_list:
                if d in header:
                    menus = []
                    for i in range(1, 4):
                        txt = " ".join(cols[i].get_text(" ", strip=True).split())
                        # 메뉴 데이터 정제
                        menus.append(txt if len(txt) > 3 and "등록된" not in txt else "식단 없음")

                    meal_result[d] = {
                        "breakfast": menus[0],
                        "lunch": menus[1],
                        "dinner": menus[2],
                        "nutrition": estimate(" ".join(menus))
                    }

        # 날씨 데이터 가져오기
        weather = get_weather()

        final_data = {
            "weather": {
                "temp": weather["temp"],
                "rain": weather["rain"],
                "last_update": get_kst_now().strftime("%Y-%m-%d %H:%M")
            },
            "meals": meal_result
        }

        # JSON 파일 저장
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=2)

        print("🚀 data.json 갱신 완료!")

    except Exception as e:
        print(f"❌ 크롤링 중 오류 발생: {e}")

if __name__ == "__main__":
    crawl()
