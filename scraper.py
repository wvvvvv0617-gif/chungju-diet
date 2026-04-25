import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_target_date():
    # 한국 시간 기준 (UTC+9)
    now = datetime.utcnow() + timedelta(hours=9)
    weekday = now.weekday()
    # 금요일 저녁 6시 이후부터 주말 동안은 무조건 '다음 주 월요일' 날짜를 타겟으로 잡음
    if (weekday == 4 and now.hour >= 18) or weekday > 4:
        target = now + timedelta(days=(7 - weekday))
    else:
        target = now
    return target.strftime("%Y-%m-%d")

def estimate(text):
    if not text or len(text) < 5:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0}
    # 기본 영양소 설정
    return {"carbs": 70, "protein": 25, "fat": 15, "sugar": 8}

def crawl():
    target_date = get_target_date()
    # URL에 직접 날짜를 넣어 해당 주차의 데이터를 강제로 호출
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    
    print(f"🔍 타겟 날짜: {target_date}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    table = soup.select_one(".t_type01") or soup.find("table")
    if not table:
        return

    result = {}
    rows = table.find_all("tr")
    days_map = {"월": "월요일", "화": "화요일", "수": "수요일", "목": "목요일", "금": "금요일"}

    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 4: continue
        
        row_text = cols[0].get_text(strip=True)
        
        for key in days_map:
            # 행의 날짜 정보에 우리가 찾는 'target_date'의 일부라도 포함되어 있는지 확인
            # 예: '2026-04-27 월요일'에 '월'이 있는지 확인
            if key in row_text:
                # 텍스트 추출 시 불필요한 공백과 줄바꿈 정제
                br = " ".join(cols[1].get_text(" ", strip=True).split())
                lc = " ".join(cols[2].get_text(" ", strip=True).split())
                dn = " ".join(cols[3].get_text(" ", strip=True).split())
                
                # '등록된' 혹은 너무 짧은 텍스트 제외
                def clean(t):
                    return t if "등록된" not in t and len(t) > 2 else "식단 없음"

                result[key] = {
                    "breakfast": clean(br),
                    "lunch": clean(lc),
                    "dinner": clean(dn),
                    "nutrition": estimate(br + lc + dn)
                }
                print(f"✅ {key}요일 데이터 성공: {clean(br)[:10]}...")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("🚀 data.json 저장 완료")

if __name__ == "__main__":
    crawl()
