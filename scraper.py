import json
import requests
import random
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urlencode

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
# 🌦️ 기상청 단기예보
# =========================
def get_weather():
    try:
        service_key = "e45e99f92f1e612fe4190678af2e64592c0fffa1eb08bb1291215d9c3ae01aae"
        base_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        
        now = get_kst_now()
        hour = now.hour
        
        base_times = [2, 5, 8, 11, 14, 17, 20, 23]
        base_time_hour = None
        
        for bt in reversed(base_times):
            if hour >= bt:
                base_time_hour = bt
                break
        
        if base_time_hour is None:
            base_time_hour = 23
            base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
        else:
            base_date = now.strftime("%Y%m%d")
        
        base_time = f"{base_time_hour:02d}00"
        
        params = {
            'serviceKey': service_key,
            'pageNo': '1',
            'numOfRows': '1000',
            'dataType': 'JSON',
            'baseDate': base_date,
            'baseTime': base_time,
            'nx': '77',
            'ny': '115'
        }
        
        print(f"🔗 기상청 API 요청: baseDate={base_date}, baseTime={base_time}")
        
        res = requests.get(base_url, params=params, timeout=15, verify=False)
        data = res.json()
        
        response_header = data.get('response', {}).get('header', {})
        result_code = response_header.get('resultCode', 'UNKNOWN')
        result_msg = response_header.get('resultMsg', 'Unknown Error')
        
        if result_code != '00':
            print(f"⚠️ 기상청 API 오류 [{result_code}]: {result_msg}")
            return {"temp": "N/A", "rain": "N/A"}
        
        items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        
        if not items:
            print("⚠️ 예보 데이터가 없습니다")
            return {"temp": "N/A", "rain": "N/A"}
        
        now_time = now.strftime("%H00")
        temp = None
        pop = None
        
        for item in items:
            fcst_time = item.get('fcstTime', '')
            category = item.get('category', '')
            value = item.get('fcstValue', '')
            
            if fcst_time == now_time:
                if category == 'TMP':
                    temp = value
                elif category == 'POP':
                    pop = value
        
        if temp is None or pop is None:
            for item in items:
                category = item.get('category', '')
                value = item.get('fcstValue', '')
                
                if temp is None and category == 'TMP':
                    temp = value
                elif pop is None and category == 'POP':
                    pop = value
                
                if temp is not None and pop is not None:
                    break
        
        temp = temp if temp else "N/A"
        pop = pop if pop else "N/A"
        
        print(f"✅ 기상청 데이터 수집 완료: 기온={temp}°C, 강수확률={pop}%")
        
        return {"temp": temp, "rain": pop}
        
    except Exception as e:
        print(f"❌ 기상청 API 오류: {e}")
        return {"temp": "N/A", "rain": "N/A"}

# =========================
# 🍱 영양 성분 스마트 추정
# =========================
def estimate_nutrition(menu_text):
    if not menu_text or "식단 없음" in menu_text or len(menu_text) < 3:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0, "calories": 0}

    seed_value = int(hashlib.md5(menu_text.encode()).hexdigest(), 16) % 10000
    random.seed(seed_value)

    base = {
        "carbs": 55 + random.randint(-3, 3),
        "protein": 20 + random.randint(-2, 2),
        "fat": 15 + random.randint(-2, 2),
        "sugar": 5 + random.randint(-1, 1)
    }

    if any(k in menu_text for k in ["고기", "제육", "불고기", "돈육", "닭", "치킨", "생선", "계란", "오리", "함박"]):
        base["protein"] += random.randint(15, 20)
        base["fat"] += random.randint(5, 10)
        base["carbs"] -= 5

    if any(k in menu_text for k in ["국수", "우동", "라면", "파스타", "빵", "떡볶이", "덮밥", "볶음밥"]):
        base["carbs"] += random.randint(15, 25)
        base["sugar"] += random.randint(5, 10)
    
    if any(k in menu_text for k in ["가스", "튀김", "전", "부침"]):
        base["fat"] += random.randint(10, 15)

    if any(k in menu_text for k in ["샐러드", "나물", "무침", "요거트", "채소"]):
        base["carbs"] -= 7
        base["protein"] += 3
        base["fat"] -= 3

    for key in base:
        base[key] = max(5, min(98, base[key]))
        
    base["calories"] = int((base["carbs"] * 4) + (base["protein"] * 4) + (base["fat"] * 9) + 280)
    
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

        print(f"🚀 data.json 갱신 완료! (날씨: {weather['temp']}°C, 강수확률: {weather['rain']}%)")

    except Exception as e:
        print(f"❌ 크롤링 중 오류 발생: {e}")

if __name__ == "__main__":
    crawl()
