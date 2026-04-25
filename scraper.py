import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_target_date():
    now = datetime.utcnow() + timedelta(hours=9)
    weekday = now.weekday()
    # 금요일 18:30 이후부터 주말 동안은 무조건 다음 주 월요일 기준
    if (weekday == 4 and now.hour >= 18) or weekday > 4:
        next_monday = now + timedelta(days=(7 - weekday))
        return next_monday.strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")

def estimate(text):
    if not text or len(text) < 5:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0}
    return {"carbs": 70, "protein": 25, "fat": 15, "sugar": 8}

def crawl():
    target_date = get_target_date()
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    
    print(f"🔍 접속 URL: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    # 모든 테이블 행(tr)을 다 가져와서 검사
    rows = soup.find_all("tr")
    result = {}
    days = ["월", "화", "수", "목", "금"]

    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 4: continue
        
        row_text = cols[0].get_text(strip=True)
        
        # 요일 찾기 (더 유연하게 검색)
        for day in days:
            if day in row_text:
                br = cols[1].get_text(" ", strip=True)
                lc = cols[2].get_text(" ", strip=True)
                dn = cols[3].get_text(" ", strip=True)
                
                # '등록된' 글자가 포함되면 무시
                br_final = br if "등록된" not in br and len(br) > 1 else "식단 없음"
                lc_final = lc if "등록된" not in lc and len(lc) > 1 else "식단 없음"
                dn_final = dn if "등록된" not in dn and len(dn) > 1 else "식단 없음"

                result[day] = {
                    "breakfast": br_final,
                    "lunch": lc_final,
                    "dinner": dn_final,
                    "nutrition": estimate(br_final + lc_final + dn_final)
                }
                print(f"✅ {day}요일 식단 저장 성공!")

    # 만약 하나도 못 찾았다면 비상용 더미 데이터라도 생성 (테스트 확인용)
    if not result:
        print("⚠️ 식단을 찾지 못해 테스트용 데이터를 생성합니다.")
        result["월"] = {"breakfast": "데이터 확인 필요", "lunch": "데이터 확인 필요", "dinner": "데이터 확인 필요", "nutrition": estimate("")}

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    crawl()
