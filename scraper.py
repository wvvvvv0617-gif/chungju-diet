import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_target_date():
    now = datetime.utcnow() + timedelta(hours=9)
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute
    # 금요일 18:30 이후부터 주말 동안은 다음 주 월요일 기준
    if (weekday == 4 and (hour > 18 or (hour == 18 and minute >= 30))) or weekday > 4:
        next_monday = now + timedelta(days=(7 - weekday))
        return next_monday.strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")

def estimate(text):
    if not text or "등록된" in text or len(text) < 5:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0}
    # 기본 영양소 설정
    carbs, protein, fat, sugar = 70, 25, 15, 8
    if any(k in text for k in ["고기", "제육", "닭", "돈까스", "햄", "계란"]):
        protein += 15
    if any(k in text for k in ["튀김", "볶음", "까스"]):
        fat += 10
    return {"carbs": carbs, "protein": protein, "fat": fat, "sugar": sugar}

def crawl():
    target_date = get_target_date()
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    
    print(f"🔍 타겟 날짜: {target_date}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    # 식단표 테이블 찾기
    table = soup.select_one(".t_type01") or soup.find("table")
    if not table:
        print("❌ 테이블을 찾을 수 없습니다.")
        return

    result = {}
    days = ["월", "화", "수", "목", "금"]
    rows = table.find_all("tr")

    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 4: continue
        
        # 첫 번째 칸에서 날짜/요일 정보 추출
        date_info = cols[0].get_text(strip=True)
        
        for day in days:
            if f"{day}요일" in date_info:
                # 메뉴 텍스트 추출 (불필요한 공백 제거)
                br = cols[1].get_text(" ", strip=True).replace(" 조식", "")
                lc = cols[2].get_text(" ", strip=True).replace(" 중식", "")
                dn = cols[3].get_text(" ", strip=True).replace(" 석식", "")
                
                # '등록된 식단이 없습니다' 문구 처리
                br = "정보 없음" if "등록된" in br or not br else br
                lc = "정보 없음" if "등록된" in lc or not lc else lc
                dn = "정보 없음" if "등록된" in dn or not dn else dn

                result[day] = {
                    "breakfast": br,
                    "lunch": lc,
                    "dinner": dn,
                    "nutrition": estimate(br + lc + dn)
                }
                print(f"✅ {day}요일 데이터 매칭 성공")

    # 최종 결과 저장
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("🚀 모든 과정 완료!")

if __name__ == "__main__":
    crawl()
