import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_target_date():
    # 한국 시간 기준 (UTC+9)
    now = datetime.utcnow() + timedelta(hours=9)
    weekday = now.weekday()
    # 금요일 저녁 18시 이후부터 주말(토, 일) 전체는 '다음 주 월요일' 날짜를 타겟으로 고정
    if (weekday == 4 and now.hour >= 18) or weekday > 4:
        target = now + timedelta(days=(7 - weekday))
    else:
        target = now
    return target.strftime("%Y-%m-%d")

def estimate(text):
    if not text or len(text) < 5:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0}
    return {"carbs": 70, "protein": 25, "fat": 15, "sugar": 8}

def crawl():
    target_date = get_target_date()
    # URL에 직접 날짜를 넣어 해당 주차의 데이터를 강제로 호출 (홈페이지 버그 방지)
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    
    print(f"🔍 타겟 날짜: {target_date}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    table = soup.select_one(".t_type01") or soup.find("table")
    if not table:
        print("❌ 식단 테이블을 찾을 수 없습니다.")
        return

    result = {}
    rows = table.find_all("tr")
    # 요일 이름으로 데이터를 매칭
    days = ["월", "화", "수", "목", "금"]

    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 4: continue
        
        row_header = cols[0].get_text(strip=True)
        
        for d in days:
            if d in row_header: # '월' 또는 '월요일'이 포함된 행 찾기
                # 공백 및 줄바꿈 깔끔하게 정리
                br = " ".join(cols[1].get_text(" ", strip=True).split())
                lc = " ".join(cols[2].get_text(" ", strip=True).split())
                dn = " ".join(cols[3].get_text(" ", strip=True).split())
                
                def clean_text(t):
                    return t if "등록된" not in t and len(t) > 2 else "식단 없음"

                result[d] = {
                    "breakfast": clean_text(br),
                    "lunch": clean_text(lc),
                    "dinner": clean_text(dn),
                    "nutrition": estimate(br + lc + dn)
                }
                print(f"✅ {d}요일 데이터 매칭 성공")

    # 파일 저장
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print("🚀 data.json 저장 완료!")

if __name__ == "__main__":
    crawl()
