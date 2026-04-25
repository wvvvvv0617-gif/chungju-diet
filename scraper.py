import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_target_date():
    # 현재 시각(한국 기준)에서 다음 주 월요일 날짜 계산
    now = datetime.utcnow() + timedelta(hours=9)
    weekday = now.weekday()
    # 주말에는 무조건 다음 주 월요일(4월 27일)을 타겟팅
    days_until_monday = (7 - weekday) % 7
    if days_until_monday == 0: days_until_monday = 7
    target = now + timedelta(days=days_until_monday)
    return target.strftime("%Y-%m-%d")

def estimate(text):
    if not text or len(text) < 5:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0}
    return {"carbs": 70, "protein": 25, "fat": 15, "sugar": 8}

def crawl():
    # 1. URL 고정 (보내주신 메뉴 번호 2830 사용)
    url = "https://www.kopo.ac.kr/chungju/content.do?menu=2830"
    
    print(f"🔗 접속 시도 URL: {url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"❌ 접속 실패: {e}")
        return

    soup = BeautifulSoup(res.text, "html.parser")
    result = {}
    days_map = {"월": "월요일", "화": "화요일", "수": "수요일", "목": "목요일", "금": "금요일"}

    # 2. 식단표의 각 행을 찾습니다. 
    # 학교 사이트 특성상 클래스명이 없어도 모든 tr을 뒤져서 '월~금' 글자를 찾습니다.
    rows = soup.find_all("tr")
    print(f"📊 총 {len(rows)}개의 행을 분석 중...")

    for row in rows:
        cols = row.find_all(["td", "th"])
        if len(cols) < 4: continue
        
        # 첫 번째 칸에서 요일 정보를 찾습니다.
        header = cols[0].get_text(strip=True)
        
        for key in days_map:
            if key in header:
                # 조식, 중식, 석식 데이터를 가져옵니다.
                raw_menus = []
                for i in range(1, 4):
                    m = " ".join(cols[i].get_text(" ", strip=True).split())
                    # '등록된 식단이 없습니다' 또는 공백 처리
                    raw_menus.append(m if len(m) > 5 and "등록된" not in m else "식단 없음")
                
                result[key] = {
                    "breakfast": raw_menus[0],
                    "lunch": raw_menus[1],
                    "dinner": raw_menus[2],
                    "nutrition": estimate(" ".join(raw_menus))
                }
                print(f"✅ {key}요일 데이터 성공: {raw_menus[1][:10]}...")

    # 3. 데이터가 여전히 없다면 로그로 알림
    if not result:
        print("⚠️ 데이터를 하나도 찾지 못했습니다. 테이블 구조를 다시 확인해야 합니다.")
    else:
        print(f"🎉 총 {len(result)}일치 식단 데이터 수집 완료!")

    # 4. 파일 저장
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    crawl()
