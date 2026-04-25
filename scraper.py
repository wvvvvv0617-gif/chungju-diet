import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

def get_target_date():
    # 현재 KST(한국 표준시) 기준 시간 구하기
    # GitHub Actions는 기본적으로 UTC 기준이므로 9시간을 더해줍니다.
    now = datetime.utcnow() + timedelta(hours=9)
    
    # 요일 (0:월, 1:화, 2:수, 3:목, 4:금, 5:토, 6:일)
    weekday = now.weekday()
    hour = now.hour
    minute = now.minute

    # 금요일(4) 18:30 이후이거나 토요일(5), 일요일(6)인 경우
    if (weekday == 4 and (hour > 18 or (hour == 18 and minute >= 30))) or weekday > 4:
        # 다음 주 월요일 날짜 계산 (현재 요일에서 7-weekday 만큼 더하면 다음주 월요일)
        next_monday = now + timedelta(days=(7 - weekday))
        return next_monday.strftime("%Y-%m-%d")
    
    # 그 외 평일에는 오늘 날짜 기준
    return now.strftime("%Y-%m-%d")

def crawl():
    target_date = get_target_date()
    # 날짜 파라미터를 추가하여 다음 주 식단을 강제로 불러올 수 있게 합니다.
    url = f"https://www.kopo.ac.kr/chungju/content.do?menu=2830&search_day={target_date}"
    
    print(f"인식된 기준 날짜: {target_date}")
    print(f"접속 URL: {url}")

    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    tables = soup.find_all("table")
    if not tables:
        print("❌ 식단 테이블을 찾을 수 없습니다.")
        return

    table = tables[0]
    rows = table.find_all("tr")
    
    days = ["월", "화", "수", "목", "금"]
    result = {}

    # 첫 번째 행은 제목(요일, 조식 등)이므로 rows[1:] 사용
    data_rows = rows[1:]

    for i in range(min(5, len(data_rows))):
        cols = data_rows[i].find_all(["td", "th"])
        if len(cols) < 4: continue

        result[days[i]] = {
            "breakfast": cols[1].get_text(separator="\n", strip=True),
            "lunch": cols[2].get_text(separator="\n", strip=True),
            "dinner": cols[3].get_text(separator="\n", strip=True),
        }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("✅ data.json 업데이트 완료")

if __name__ == "__main__":
    crawl()
