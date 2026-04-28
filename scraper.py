import json
import requests
import random
import hashlib
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import unquote

# =========================
# ⏰ 한국 시간 (KST)
# =========================
def get_kst_now():
    return datetime.utcnow() + timedelta(hours=9)

def get_target_date():
    now = get_kst_now()
    weekday = now.weekday()
    hm = now.hour * 100 + now.minute
    
    # 금요일 오후 6시 30분 이후이거나 주말이면 다음주 월요일 식단 타겟팅
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
        url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        service_key = "e45e99f92f1e612fe4190678af2e64592c0fffa1eb08bb1291215d9c3ae01aae"
        
        now = get_kst_now()
        base_date = now.strftime("%Y%m%d")
        
        # API 발표 시각에 맞춘 base_time 설정
        hour = now.hour
        if hour < 2:
            base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
            base_time = "2300"
        elif hour < 5: base_time = "0200"
        elif hour < 8: base_time = "0500"
        elif hour < 11: base_time = "0800"
        elif hour < 14: base_time = "1100"
        elif hour < 17: base_time = "1400"
        elif hour < 20: base_time = "1700"
        elif hour < 23: base_time = "2000"
        else: base_time = "2300"

        params = {
            'serviceKey': unquote(service_key),
            'pageNo': '1',
            'numOfRows': '1000',
            'dataType': 'JSON',
            'baseDate': base_date,
            'baseTime': base_time,
            'nx': '77',  # 충주 목행동 인근 좌표
            'ny': '115'
        }

        res = requests.get(url, params=params, timeout=15)
        res.raise_for_status()
        data = res.json()

        if data['response']['header']['resultCode'] != '00':
            print(f"⚠️ API 결과 오류: {data['response']['header']['resultMsg']}")
            return {"temp": "N/A", "rain": "N/A"}

        items = data['response']['body']['items']['item']
        temp, pop = None, None
        target_fcst_time = now.strftime("%H00")

        for item in items:
            # 현재 시각 예보를 우선적으로 찾음
            if item['fcstTime'] == target_fcst_time:
                if item['category'] == 'TMP': temp = item['fcstValue']
                if item['category'] == 'POP': pop = item['fcstValue']
            if temp and pop: break
        
        # 현재 시각 데이터가 없으면 가장 빠른 데이터 사용
        if not temp:
            for item in items:
                if item['category'] == 'TMP': temp = item['fcstValue']
                if item['category'] == 'POP': pop = item['fcstValue']
                if temp: break

        return {"temp": temp, "rain": pop}
        
    except Exception as e:
        print(f"❌ 날씨 수집 오류: {e}")
        return {"temp": "N/A", "rain": "N/A"}

# =========================
# 🍱 영양소 추정 (기본 구조 유지)
# =========================
def estimate_nutrition(menu_str):
    return {"calories": 0, "carbs": 0, "protein": 0, "fat": 0, "sugar": 0}

# =========================
# 🕷️ 식단 크롤링 및 저장
# =========================
def crawl():
    target_date = get_target_date()
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    print(f"🔗 데이터 수집 시작: {url}")

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        meal_result = {}
        days_list = ["월", "화", "수", "목", "금"]

        for row in soup.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) < 4: continue
            header = cols[0].get_text(strip=True)

            for d in days_list:
                if d in header:
                    # 텍스트 정제 및 중복 공백 제거
                    b_menu = " ".join(cols[1].get_text(" ", strip=True).split())
                    l_menu = " ".join(cols[2].get_text(" ", strip=True).split())
                    d_menu = " ".join(cols[3].get_text(" ", strip=True).split())
                    
                    meal_result[d] = {
                        "breakfast": b_menu if len(b_menu) > 3 and "등록된" not in b_menu else "식단 없음",
                        "lunch": l_menu if len(l_menu) > 3 and "등록된" not in l_menu else "식단 없음",
                        "dinner": d_menu if len(d_menu) > 3 and "등록된" not in d_menu else "식단 없음",
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
        print(f"🚀 data.json 갱신 완료! (날씨: {weather['temp']}도)")

    except Exception as e:
        print(f"❌ 크롤링 중 오류 발생: {e}")

if __name__ == "__main__":
    crawl()
