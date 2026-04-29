import json
import requests
import random
import hashlib
import os
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# =========================
# ⏰ 한국 시간 (KST)
# =========================

def get_kst_now():
    # 함수 내부로 4칸 들여쓰기
    return datetime.utcnow() + timedelta(hours=9)

def get_target_date():
    # 함수 내부로 4칸 들여쓰기
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
# 🌦️ 기상청 단기예보
# =========================

def get_weather():
    prev_weather = {"temp": "N/A", "rain": "N/A"}

    # 이전 값 백업
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            old_data = json.load(f)
            old_w = old_data.get("weather", {})
            if old_w.get("temp") != "N/A":
                prev_weather["temp"] = old_w.get("temp")
            if old_w.get("rain") != "N/A":
                prev_weather["rain"] = old_w.get("rain")
    except:
        pass

    try:
        service_key = os.getenv("KMA_API_KEY")
        base_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

        now = get_kst_now()

        # ✅ 안정적인 base_time 계산
        base_times = [2, 5, 8, 11, 14, 17, 20, 23]
        base_time_hour = None

        for bt in reversed(base_times):
            if now.hour >= bt:
                base_time_hour = bt
                break

        # 새벽이면 전날 23시 사용
        if base_time_hour is None:
            base_time_hour = 23
            now = now - timedelta(days=1)

        base_date = now.strftime("%Y%m%d")
        base_time = f"{base_time_hour:02d}00"

        params = {
            'serviceKey': service_key,
            'base_date': base_date,
            'base_time': base_time,
            'nx': '77',
            'ny': '115',
            'dataType': 'JSON',
            'numOfRows': '200'
        }

        print(f"🌤️ 날씨 요청: {base_date} {base_time}")

        res = requests.get(base_url, params=params, timeout=10)
        data = res.json()

        # ✅ 응답 체크 강화
        if not data.get('response'):
            return prev_weather

        header = data['response']['header']
        if header.get('resultCode') != '00':
            print("❌ API 응답 오류")
            return prev_weather

        items = data['response']['body']['items']['item']
        if not items:
            print("❌ 예보 데이터 없음")
            return prev_weather

        temp = None
        pop = None

        for item in items:
            if item.get('category') == 'TMP' and temp is None:
                temp = item.get('fcstValue')
            elif item.get('category') == 'POP' and pop is None:
                pop = item.get('fcstValue')

            if temp is not None and pop is not None:
                break

        final_temp = temp if temp else prev_weather["temp"]
        final_pop = pop if pop else prev_weather["rain"]

        print(f"✅ 날씨: {final_temp}°C / 강수 {final_pop}%")
        return {"temp": final_temp, "rain": final_pop}

    except Exception as e:
        print(f"❌ 날씨 오류: {e}")
        return prev_weather

# =========================
# 🍱 영양 성분 추정
# =========================

def estimate_nutrition(menu_text):
    if not menu_text or "식단 없음" in menu_text:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0, "calories": 0}

    seed_value = int(hashlib.md5(menu_text.encode()).hexdigest(), 16) % 10000
    random.seed(seed_value)

    base = {
        "carbs": 55 + random.randint(-3, 3),
        "protein": 20 + random.randint(-2, 2),
        "fat": 15 + random.randint(-2, 2),
        "sugar": 5 + random.randint(-1, 1)
    }

    if any(k in menu_text for k in ["고기","닭","돈육","생선","계란"]):
        base["protein"] += random.randint(15, 20)
        base["fat"] += random.randint(5, 10)

    if any(k in menu_text for k in ["국수","라면","밥","빵","떡"]):
        base["carbs"] += random.randint(15, 25)

    base["calories"] = int((base["carbs"]*4)+(base["protein"]*4)+(base["fat"]*9)+280)

    random.seed(None)
    return base

# =========================
# 🕷️ 크롤링
# =========================

def crawl():
    target_date = get_target_date()
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"

    print(f"📡 크롤링: {url}")

    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
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
                    b = cols[1].get_text(" ", strip=True)
                    l = cols[2].get_text(" ", strip=True)
                    dnr = cols[3].get_text(" ", strip=True)

                    meal_result[d] = {
                        "breakfast": b if len(b)>3 else "식단 없음",
                        "lunch": l if len(l)>3 else "식단 없음",
                        "dinner": dnr if len(dnr)>3 else "식단 없음",
                        "nutrition": {
                            "breakfast": estimate_nutrition(b),
                            "lunch": estimate_nutrition(l),
                            "dinner": estimate_nutrition(dnr)
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

        print("🚀 완료!")

    except Exception as e:
        print(f"❌ 오류: {e}")

if __name__ == "__main__":
    crawl()
