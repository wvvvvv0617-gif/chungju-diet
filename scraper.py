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
# 🌦️ 기상청 단기예보 (날씨 수집)
# =========================
def get_weather():
    try:
        # 기상청 단기예보 API 설정
        url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        # 여기에 발급받으신 서비스키를 입력하세요 (Decoding 키 권장)
        service_key = "e45e99f92f1e612fe4190678af2e64592c0fffa1eb08bb1291215d9c3ae01aae" 
        
        now = get_kst_now()
        base_date = now.strftime("%Y%m%d")
        
        # 기상청 발표 시간 기준 (단기예보는 0200부터 3시간 간격 발표)
        # 현재 시간 기준 가장 최근 발표 시각 계산
        hour = now.hour
        if hour < 3: base_time = "0200"
        elif hour < 6: base_time = "0500"
        elif hour < 9: base_time = "0800"
        elif hour < 12: base_time = "1100"
        elif hour < 15: base_time = "1400"
        elif hour < 18: base_time = "1700"
        elif hour < 21: base_time = "2000"
        else: base_time = "2300"

        params = {
            'serviceKey': service_key,
            'pageNo': '1',
            'numOfRows': '1000',
            'dataType': 'JSON',
            'base_date': base_date,
            'base_time': base_time,
            'nx': '76', # 충주캠퍼스 격자 X
            'ny': '114' # 충주캠퍼스 격자 Y
        }

        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        if data['response']['header']['resultCode'] != '00':
            return {"temp": None, "rain": None}

        items = data['response']['body']['items']['item']
        
        temp = None
        pop = None # 강수확률

        for item in items:
            # TMP: 1시간 기온, POP: 강수확률
            # 가장 빠른 예보 시각(fcstTime)의 데이터를 가져옵니다.
            if item['category'] == 'TMP' and temp is None:
                temp = item['fcstValue']
            if item['category'] == 'POP' and pop is None:
                pop = item['fcstValue']
            
            if temp and pop: break

        return {"temp": int(temp) if temp else None, "rain": int(pop) if pop else None}
    except Exception as e:
        print(f"❌ 날씨 수집 오류: {e}")
        return {"temp": None, "rain": None}

# =========================
# 🍱 영양 성분 스마트 추정 (일관성 + 다양성 최적화)
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

        print("🚀 data.json 갱신 완료! (기상청 API 적용)")

    except Exception as e:
        print(f"❌ 크롤링 중 오류 발생: {e}")

if __name__ == "__main__":
    crawl()
