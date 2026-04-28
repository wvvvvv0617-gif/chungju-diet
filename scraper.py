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
        
        # 1. 키 인코딩 문제 해결을 위해 두 가지 형태 준비
        raw_key = "e45e99f92f1e612fe4190678af2e64592c0fffa1eb08bb1291215d9c3ae01aae"
        service_key = unquote(raw_key) # 이미 인코딩된 경우를 대비해 디코딩 후 사용
        
        now = get_kst_now()
        base_date = now.strftime("%Y%m%d")
        
        hour = now.hour
        # API 발표 시간 기준 설정
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
            'serviceKey': service_key,
            'pageNo': '1',
            'numOfRows': '1000',
            'dataType': 'JSON',
            'baseDate': base_date, 
            'baseTime': base_time,
            'nx': '77', # 목행동
            'ny': '115'
        }
        
        res = requests.get(url, params=params, timeout=15)
        
        # 응답 내용 확인
        try:
            data = res.json()
        except:
            print(f"⚠️ JSON 변환 실패 (응답 내용): {res.text[:100]}")
            return {"temp": None, "rain": None}
        
        # 기상청 에러 체크
        header = data.get('response', {}).get('header', {})
        if header.get('resultCode') != '00':
            print(f"⚠️ API 오류: {header.get('resultCode')} - {header.get('resultMsg')}")
            # 만약 키 오류(SERVICE_KEY_IS_NOT_REGISTERED_ERROR)가 뜨면 raw_key를 그대로 써야 함
            if header.get('resultCode') == '30':
                 params['serviceKey'] = raw_key
                 res = requests.get(url, params=params, timeout=15)
                 data = res.json()
            else:
                return {"temp": None, "rain": None}

        items_data = data.get('response', {}).get('body', {}).get('items', {}).get('item', [])
        if not items_data:
            print("⚠️ 데이터를 찾을 수 없습니다. (baseDate/Time 확인 필요)")
            return {"temp": None, "rain": None}

        temp, pop = None, None
        # 현재 시간과 가장 가까운 예보 찾기
        target_fcst_time = now.strftime("%H00")

        for item in items_data:
            # 예보 시각이 일치하는 항목 찾기
            if item.get('fcstTime') == target_fcst_time:
                if item.get('category') == 'TMP':
                    temp = item.get('fcstValue')
                if item.get('category') == 'POP':
                    pop = item.get('fcstValue')
            
            if temp is not None and pop is not None:
                break
        
        # 만약 현재 시각 데이터가 없으면 리스트의 첫 번째 데이터라도 가져옴
        if temp is None and items_data:
            for item in items_data:
                if item.get('category') == 'TMP' and temp is None:
                    temp = item.get('fcstValue')
                if item.get('category') == 'POP' and pop is None:
                    pop = item.get('fcstValue')

        return {"temp": temp, "rain": pop}
    except Exception as e:
        print(f"❌ 날씨 수집 오류: {e}")
        return {"temp": None, "rain": None}

# 영양소 추정 함수 (기존 유지)
def estimate_nutrition(menu_str):
    return {"calories": 0, "carbs": 0, "protein": 0, "fat": 0, "sugar": 0}

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
        print(f"🚀 data.json 갱신 완료! (날씨: {weather['temp']}도, 강수: {weather['rain']}%)")
    except Exception as e:
        print(f"❌ 크롤링 중 오류 발생: {e}")

if __name__ == "__main__":
    crawl()
