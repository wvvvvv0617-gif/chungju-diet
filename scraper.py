import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_target_date():
    now = datetime.utcnow() + timedelta(hours=9)
    weekday = now.weekday()
    # 금요일 18:30 이후부터 주말 동안은 다음 주 월요일 기준
    if (weekday == 4 and now.hour >= 18) or weekday > 4:
        next_monday = now + timedelta(days=(7 - weekday))
        return next_monday.strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")

def estimate(text):
    if not text or "등록된" in text or len(text) < 5:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0}
    return {"carbs": 70, "protein": 25, "fat": 15, "sugar": 8}

def crawl():
    target_date = get_target_date()
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    
    print(f"🔍 타겟 날짜: {target_date}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    # 테이블 찾기
    table = soup.select_one(".t_type01") or soup.find("table")
    if not table:
        print("❌ 테이블을 찾을 수 없습니다.")
        return

    result = {}
    days_map = {"월": "월요일", "화": "화요일", "수": "수요일", "목": "목요일", "금": "금요일"}
    rows = table.find_all("tr")

    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 4: continue
        
        row_text = cols[0].get_text(strip=True)
        
        for key, full_name in days_map.items():
            if key in row_text: # '월' 또는 '월요일' 또는 '2026-04-27 월요일' 모두 대응
                br = cols[1].get_text(" ", strip=True)
                lc = cols[2].get_text(" ", strip=True)
                dn = cols[3].get_text(" ", strip=True)
                
                result[key] = {
                    "breakfast": br if br and "등록된" not in br else "식단 없음",
                    "lunch": lc if lc and "등록된" not in lc else "식단 없음",
                    "dinner": dn if dn and "등록된" not in dn else "식단 없음",
                    "nutrition": estimate(br + lc + dn)
                }
                print(f"✅ {key}요일 추출 성공: {lc[:10]}...")

    # 만약 결과가 비어있다면 (비상용)
    if not result:
        print("⚠️ 검색 결과가 없어 빈 데이터를 생성하지 않습니다. 코드를 다시 점검하세요.")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    crawl()
