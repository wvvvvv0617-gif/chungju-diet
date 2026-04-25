import json
import requests
from bs4 import BeautifulSoup

URL = "https://www.kopo.ac.kr/chungju/content.do?menu=2830"

def crawl():

    res = requests.get(URL)
    soup = BeautifulSoup(res.text, "html.parser")

    table = soup.select_one(".t_type01 tbody")
    rows = table.find_all("tr")

    days = ["월","화","수","목","금"]
    result = {}

    for i in range(5):
        cols = rows[i].find_all("td")

        breakfast = cols[1].get_text(strip=True)
        lunch = cols[2].get_text(strip=True)
        dinner = cols[3].get_text(strip=True)

        result[days[i]] = {
            "breakfast": breakfast,
            "lunch": lunch,
            "dinner": dinner,
            "nutrition": estimate(breakfast + lunch + dinner)
        }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


def estimate(text):
    carbs = 60
    protein = 15
    fat = 10
    sugar = 5

    if "고기" in text:
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
