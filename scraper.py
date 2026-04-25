import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

URL = "https://www.kopo.ac.kr/chungju/content.do?menu=2830"

def clean(text):
    return text.strip().replace("\n", ", ") if text else "정보 없음"

def crawl():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(URL)
    time.sleep(3)

    days = ["월","화","수","목","금"]
    result = {}

    try:
        table = driver.find_element(By.CSS_SELECTOR, ".t_type01 tbody")
        rows = table.find_elements(By.TAG_NAME, "tr")

        for i in range(5):
            cols = rows[i].find_elements(By.TAG_NAME, "td")

            result[days[i]] = {
                "breakfast": clean(cols[1].text),
                "lunch": clean(cols[2].text),
                "dinner": clean(cols[3].text),
                "nutrition": estimate(cols[1].text + cols[2].text + cols[3].text)
            }

    except Exception as e:
        print("크롤링 실패:", e)

    driver.quit()

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)


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
