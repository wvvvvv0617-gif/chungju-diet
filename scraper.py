import json

def crawl():

    data = {
        "월": {
            "breakfast": "아침 메뉴",
            "lunch": "점심 메뉴",
            "dinner": "저녁 메뉴",
            "nutrition": {
                "carbs": 70,
                "protein": 20,
                "fat": 15,
                "sugar": 5
            }
        },
        "화": {
            "breakfast": "아침 메뉴",
            "lunch": "점심 메뉴",
            "dinner": "저녁 메뉴",
            "nutrition": {
                "carbs": 65,
                "protein": 22,
                "fat": 14,
                "sugar": 4
            }
        }
    }

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    crawl()
