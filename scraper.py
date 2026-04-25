import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_target_date():
    # 한국 시간(UTC+9) 기준 계산
    now = datetime.utcnow() + timedelta(hours=9)
    weekday = now.weekday()
    # 토요일(5), 일요일(6) 혹은 금요일 저녁이면 다음 주 월요일로 날짜 고정
    if weekday >= 4:
        target = now + timedelta(days=(7 - weekday) % 7 if (7 - weekday) % 7 != 0 else 7)
    else:
        target = now
    return target.strftime("%Y-%m-%d")

def estimate(text):
    if not text or len(text) < 5:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0}
    # 기본 영양소 (추후 로직 확장 가능)
    return {"carbs": 70, "protein": 25, "fat": 15, "sugar": 8}

def crawl():
    # 다음 주 월요일인 2026-04-27을 강제로 타겟팅하도록 URL 생성
    target_date = get_target_date()
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    
    print(f"🔗 타겟 날짜 주소 접속: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    result = {}
    rows = soup.find_all("tr")
    days_list = ["월", "화", "수", "목", "금"]

    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 4: continue
        
        header = cols[0].get_text(strip=True)
        for d in days_list:
            if d in header:
                menus = []
                for i in range(1, 4):
                    txt = " ".join(cols[i].get_text(" ", strip=True).split())
                    # '등록된' 글자가 있거나 빈 칸이면 식단 없음 처리
                    menus.append(txt if len(txt) > 3 and "등록된" not in txt else "식단 없음")
                
                result[d] = {
                    "breakfast": menus[0],
                    "lunch": menus[1],
                    "dinner": menus[2],
                    "nutrition": estimate(" ".join(menus))
                }
                print(f"✅ {d}요일 식단 갱신 완료!")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("🚀 모든 과정 완료!")

if __name__ == "__main__":
    crawl()
