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
    prev_weather = {"temp": "N/A", "rain": "N/A"}
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            old_data = json.load(f)
            old_w = old_data.get("weather", {})
            if old_w.get("temp") != "N/A": prev_weather["temp"] = old_w.get("temp")
            if old_w.get("rain") != "N/A": prev_weather["rain"] = old_w.get("rain")
    except:
        pass

    try:
        # 터미널에서 성공한 디코딩된 서비스 키 사용
        service_key = "e45e99f92f1e612fe4190678af2e64592c0fffa1eb08bb1291215d9c3ae01aae"
        base_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        
        now = get_kst_now()
        # 데이터 안정성을 위해 현재로부터 약 1시간 전 기준의 가장 가까운 base_time 선택
        target_dt = now - timedelta(minutes=40) 
        
        base_times = [2, 5, 8, 11, 14, 17, 20, 23]
        base_time_hour = 2
        for bt in reversed(base_times):
            if target_dt.hour >= bt:
                base_time_hour = bt
                break
        
        # 터미널 성공 사례와 동일하게 언더바(_) 형식의 파라미터 우선 사용
        base_date = target_dt.strftime("%Y%m%d")
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
        
        print(f"🔗 기상청 API 요청: {base_date} / {base_time}")
        
        # 1차 시도 (언더바 파라미터)
        res = requests.get(base_url, params=params, timeout=15, verify=False)
        data = res.json()
        
        # 만약 APPLICATION_ERROR가 나면 표준 파라미터(대소문자)로 2차 시도
        if data.get('response', {}).get('header', {}).get('resultCode') != '00':
            print("🔄 1차 시도 실패, 파라미터 형식을 변경하여 재시도합니다.")
            params['baseDate'] = params.pop('base_date')
            params['baseTime'] = params.pop('base_time')
            res = requests.get(base_url, params=params, timeout=15, verify=False)
            data = res.json()

        items = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        
        if not items:
            print("⚠️ 예보 데이터가 없습니다.")
            return prev_weather
        
        now_hour_str = now.strftime("%H") + "00"
        temp, pop = None, None
        
        # 현재 시각 데이터 매칭
        for item in items:
            if item.get('fcstTime') == now_hour_str:
                if item.get('category') == 'TMP': temp = item.get('fcstValue')
                elif item.get('category') == 'POP': pop = item.get('fcstValue')
        
        # 데이터 부족 시 첫 번째 예보 활용
        if temp is None or pop is None:
            for item in items:
                if temp is None and item.get('category') == 'TMP': temp = item.get('fcstValue')
                if pop is None and item.get('category') == 'POP': pop = item.get('fcstValue')
                if temp and pop: break
            
        final_temp = temp if temp is not None else prev_weather["temp"]
        final_pop = pop if pop is not None else prev_weather["rain"]
        
        print(f"✅ 기상청 데이터 수집 완료: 기온={final_temp}°C, 강수확률={final_pop}%")
        return {"temp": final_temp, "rain": final_pop}
        
    except Exception as e:
        print(f"❌ 기상청 API 오류: {e}")
        return prev_weather

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
