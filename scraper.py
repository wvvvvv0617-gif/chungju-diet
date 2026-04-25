import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_target_date():
    # 현재 KST(한국 표준시) 기준 시간 구하기
    # GitHub Actions는 UTC 기준이므로 9시간을 더합니다.
    now = datetime.utcnow() + timedelta(hours=9)
    
    # 요일 (0:월, 1:화, 2:수, 3:목, 4:금, 5:토, 6:일)
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute

    # 조건: 금요일(4) 18:30 이후이거나 토요일(5), 일요일(6)인 경우
    if (weekday == 4 and (hour > 18 or (hour == 18 and minute >= 30))) or weekday > 4:
        # 다음 주 월요일 날짜 계산
        next_monday = now + timedelta(days=(7 - weekday))
        return next_monday.strftime("%Y-%m-%d")
    
    # 그 외 평일에는 오늘 날짜 기준
    return now.strftime("%Y-%m-%d")

def estimate(text):
    """메뉴 텍스트를 분석하여 영양 성분을 추정합니다."""
    carbs, protein, fat, sugar = 65, 20, 15, 5 # 기본값
    
    if not text or "등록된 식단이 없습니다" in text:
        return {"carbs": 0, "protein": 0, "fat": 0, "sugar": 0}

    if "고기" in text or "제육" in text or "돈까스" in text or "치킨" in text:
        protein += 15
        fat += 10
    if "튀김" in text or "볶음" in text:
        fat += 10
    if "밥" in text or "비빔밥" in text:
        carbs += 10
    if "떡" in text or "빵" in text:
        sugar += 10

    return {
        "carbs": carbs,
        "protein": protein,
        "fat": fat,
        "sugar": sugar
    }

def crawl():
    target_date = get_target_date()
    # 특정 날짜가 포함된 주차의 식단을 가져오는 URL
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    
    print(f"🕒 기준 날짜: {target_date}")
    print(f"🔗 접속 URL: {url}")

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        tables = soup.find_all("table")
        if not tables:
            print("❌ 식단 테이블을 찾을 수 없습니다.")
            return

        table = tables[0]
        rows = table.find_all("tr")
        
        days = ["월", "화", "수", "목", "금"]
        result = {}

        # 첫 번째 행(Header)을 제외하고 월~금 데이터 순회
        data_rows = rows[1:]

        for i in range(min(5, len(data_rows))):
            cols = data_rows[i].find_all(["td", "th"])
            if len(cols) < 4: continue

            # 각 끼니별 텍스트 추출
            br = cols[1].get_text(separator=" ", strip=True)
            lc = cols[2].get_text(separator=" ", strip=True)
            dn = cols[3].get_text(separator=" ", strip=True)

            # 영양 성분 계산 (세 끼 합산 기준)
            combined_text = br + lc + dn
            nutri = estimate(combined_text)

            result[days[i]] = {
                "breakfast": br if br else "등록된 식단이 없습니다",
                "lunch": lc if lc else "등록된 식단이 없습니다",
                "dinner": dn if dn else "등록된 식단이 없습니다",
                "nutrition": nutri
            }

        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        print("✅ data.json 업데이트 및 영양 성분 계산 완료")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    crawl()
