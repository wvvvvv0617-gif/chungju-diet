import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.kopo.ac.kr/chungju/content.do?menu=2830"

def crawl():

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(URL, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    tables = soup.find_all("table")

    if not tables:
        print("❌ 테이블 없음")
        return

    table = tables[0]
    rows = table.find_all("tr")

    days = ["월","화","수","목","금"]
    result = {}

    for i in range(min(5, len(rows))):

        cols = rows[i].find_all("td")

        if len(cols) < 4:
            continue

        result[days[i]] = {
            "breakfast": cols[1].get_text(strip=True),
            "lunch": cols[2].get_text(strip=True),
            "dinner": cols[3].get_text(strip=True),
            "nutrition": estimate(cols[1].get_text()+cols[2].get_text()+cols[3].get_text())
        }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("✅ data.json 업데이트 완료")


def estimate(text):

    carbs = 60
    protein = 15
    fat = 10
    sugar = 5

    if "고기" in text or "제육" in text:
        protein += 10
        fat += 5

    if "튀김" in text:
        fat += 10

    if "밥" in text:
        carbs += 10

    if "떡" in text:
        sugar += 10

    return {
        "carbs": carbs,
        "protein": protein,
        "fat": fat,
        "sugar": sugar
    }

if __name__ == "__main__":
    crawl()
