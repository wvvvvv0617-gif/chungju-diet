import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_target_date():
    now = datetime.utcnow() + timedelta(hours=9)
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute

    # 금요일 18:30 이후 ~ 일요일까지는 다음 주 월요일 기준
    if (weekday == 4 and (hour > 18 or (hour == 18 and minute >= 30))) or weekday > 4:
        next_monday = now + timedelta(days=(7 - weekday))
        return next_monday.strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")

def estimate(text):
    if not text or "등록된" in text or len(text) < 2:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0}
    
    # 기본 칼로리 베이스
    carbs, protein, fat, sugar = 65, 20, 15, 5
    if any(keyword in text for keyword in ["고기", "제육", "돈까스", "치킨", "계란"]):
        protein += 15
        fat += 5
    if any(keyword in text for keyword in ["튀김", "까스", "전"]):
        fat += 10
    return {"carbs": carbs, "protein": protein, "fat": fat, "sugar": sugar}

def crawl():
    target_date = get_target_date()
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    
    print(f"🔍 확인 날짜: {target_date}")
    headers = {"User-Agent": "Mozilla/5.0"}
    
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    # '식단표'라는 글자가 포함된 테이블을 찾거나 첫 번째 테이블 선택
    table = soup.find("table", {"class": "t_type01"}) or soup.find("table")
    
    if not table:
        print("❌ 테이블을 찾지 못했습니다.")
        return

    result = {}
    days = ["월", "화", "수", "목", "금"]
    rows = table.find_all("tr")

    # 실제 데이터 행 추출 (보통 첫 행은 요일/조식/중식 등 제목)
    for i, row in enumerate(rows):
        cols = row.find_all(["td", "th"])
        if len(cols) < 4: continue
        
        # 첫 번째 열에 '월', '화' 등의 글자가 있는지 확인 (요일 행 찾기)
        row_text = cols[0].get_text()
        found_day = None
        for d in days:
            if d in row_text:
                found_day = d
                break
        
        if found_day:
            br = cols[1].get_text(" ", strip=True)
            lc = cols[2].get_text(" ", strip=True)
            dn = cols[3].get_text(" ", strip=True)
            
            result[found_day] = {
                "breakfast": br if br else "식단 없음",
                "lunch": lc if lc else "식단 없음",
                "dinner": dn if dn else "식단 없음",
                "nutrition": estimate(br + lc + dn)
            }

    # 만약 결과가 비어있다면 강제로 월~금 틀이라도 생성
    if not result:
        print("⚠️ 데이터를 찾지 못해 빈 틀을 생성합니다.")
        for d in days:
            result[d] = {"breakfast": "정보 없음", "lunch": "정보 없음", "dinner": "정보 없음", "nutrition": estimate("")}

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("✅ data.json 저장 완료")

if __name__ == "__main__":
    crawl()
