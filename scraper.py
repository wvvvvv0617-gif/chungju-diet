import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

URL = "https://www.kopo.ac.kr/chungju/content.do?menu=2830"

def clean(text):
    return text.strip().replace("\n", ", ") if text else "정보 없음"

def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

def crawl():
    driver = get_driver()
    driver.get(URL)
    time.sleep(3)

    data = {}
    days = ["월","화","수","목","금"]

    try:
        table = driver.find_element(By.CSS_SELECTOR, ".t_type01 tbody")
        rows = table.find_elements(By.TAG_NAME, "tr")

        for i in range(5):
            cols = rows[i].find_elements(By.TAG_NAME, "td")

            breakfast = clean(cols[1].text)
            lunch = clean(cols[2].text)
            dinner = clean(cols[3].text)

            data[days[i]] = {
                "breakfast": breakfast,
                "lunch": lunch,
                "dinner": dinner,
                "nutrition": estimate(breakfast + lunch + dinner)
            }

    except Exception as e:
        print("크롤링 실패:", e)

    driver.quit()

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 🔥 간단 영양 추정 (실전용)
def estimate(text):
    carbs = 60
    protein = 15
    fat = 10
    sugar = 5

    keywords = {
        "meat": ["제육","고기","돈까스","닭","불고기"],
        "fry": ["튀김","가스","강정"],
        "rice": ["밥","덮밥","볶음밥"],
        "sugar": ["떡","디저트","주스","식혜"]
    }

    for k in keywords["meat"]:
        if k in text:
            protein += 10
            fat += 5

    for k in keywords["fry"]:
        if k in text:
            fat += 10

    for k in keywords["rice"]:
        if k in text:
            carbs += 15

    for k in keywords["sugar"]:
        if k in text:
            sugar += 10

    return {
        "carbs": max(0, carbs),
        "protein": max(0, protein),
        "fat": max(0, fat),
        "sugar": max(0, sugar)
    }

if __name__ == "__main__":
    crawl()
