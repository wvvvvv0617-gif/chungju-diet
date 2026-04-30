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

def get_weather(existing_weather):
    # 기본적으로 기존 데이터를 유지하도록 설정
    final_weather = existing_weather.copy()

    try:
        service_key = os.getenv("KMA_API_KEY")
        if not service_key:
            print("⚠️ API KEY가 설정되지 않았습니다.")
            return final_weather

        base_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        now = get_kst_now()

        # ✅ 안정적인 base_time 계산
        base_times = [2, 5, 8, 11, 14, 17, 20, 23]
        base_time_hour = None

        for bt in reversed(base_times):
            if now.hour >= bt:
                base_time_hour = bt
                break

        if base_time_hour is None:
            base_time_hour = 23
            now_bt = now - timedelta(days=1)
        else:
            now_bt = now

        base_date = now_bt.strftime("%Y%m%d")
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

        if not data.get('response') or data['response']['header'].get('resultCode') != '00':
            print("❌ API 응답 오류 (기존 데이터 유지)")
            return final_weather

        items = data['response']['body']['items']['item']
        
        # 현재 시간과 가장 가까운 예보 찾기
        target_date = now.strftime("%Y%m%d")
        target_time = f"{now.hour:02d}00"

        temp, pop = None, None
        for item in items:
            item_date = item.get('fcstDate')
            item_time = item.get('fcstTime')

            # 현재 시간 이후의 데이터 중 첫 번째 TMP와 POP를 가져옴
            if item_date > target_date or (item_date == target_date and item_time >= target_time):
                if item.get('category') == 'TMP' and temp is None:
                    temp = item.get('fcstValue')
                elif item.get('category') == 'POP' and pop is None:
                    pop = item.get('fcstValue')

            if temp is not None and pop is not None:
                break

        if temp: final_weather["temp"] = temp
        if pop: final_weather["rain"] = pop
        final_weather["last_update"] = now.strftime("%Y-%m-%d %H:%M")

        print(f"✅ 날씨 갱신 완료: {final_weather['temp']}°C / {final_weather['rain']}%")
        return final_weather

    except Exception as e:
        print(f"❌ 날씨 오류: {e}")
        return final_weather

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
# 🚀 메인 실행부
# =========================

def main():
    # 1. 기존 데이터 읽기 (파일이 없으면 기본값 생성)
    data_path = "data.json"
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            try:
                final_data = json.load(f)
            except:
                final_data = {"weather": {}, "meals": {}}
    else:
        final_data = {"weather": {}, "meals": {}}

    # 2. 식단 크롤링 (실패해도 기존 식단 유지)
    target_date = get_target_date()
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    print(f"📡 식단 크롤링: {url}")

    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        meal_result = {}
        days_list = ["월", "화", "수", "목", "금"]
        found_any = False

        for row in soup.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) < 4: continue
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
                    found_any = True
        
        if found_any:
            final_data["meals"] = meal_result
            print("🍱 식단 데이터 갱신 성공")
    except Exception as e:
        print(f"❌ 식단 크롤링 실패 (기존 데이터 보존): {e}")

    # 3. 날씨 업데이트 (실패해도 기존 날씨 유지)
    final_data["weather"] = get_weather(final_data.get("weather", {"temp": "N/A", "rain": "N/A"}))

    # 4. 최종 데이터 저장
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print("🚀 모든 작업이 완료되었습니다!")

if __name__ == "__main__":
    main()
