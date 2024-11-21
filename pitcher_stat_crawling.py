import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import re
from datetime import datetime

def getPlayerId(name):
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # 브라우저 UI를 띄우지 않음
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox") 

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    url = f"https://statiz.sporki.com/player/?m=search&s={name}"

    driver.get(url)

    final_url = driver.current_url
    print("Final URL after redirection:", final_url)

    
    match = re.search(r'p_no=(\d+)', final_url)

    if match:
        player_id = match.group(1)
    else:
        print("Player ID not found in the final URL.")
        driver.quit()
        sys.exit()

    driver.quit()
    return player_id

def crawling(player_id, playerName):
    url = f"https://statiz.sporki.com/player/?m=year&p_no={player_id}"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table")
    rows = table.find("tbody").find_all("tr")

    data = []
    columns = ["year", "games", "win", "lose", "saves", "hold", "ip", "era", "er", "tbf", "h", "2b", "3b", "hr", "bb", "so", "whip", "war"]

    for row in rows:
        cells = row.find_all("td")
        if len(cells) > 0:
            year = cells[0].text.strip()

            games = int(cells[4].text.strip()) if cells[4].text.strip() else 0
            win = int(cells[10].text.strip()) if cells[10].text.strip() else 0
            lose = int(cells[11].text.strip()) if cells[11].text.strip() else 0
            save = int(cells[12].text.strip()) if cells[12].text.strip() else 0
            hold = int(cells[13].text.strip()) if cells[13].text.strip() else 0
            ip = float(cells[14].text.strip()) if cells[14].text.strip() else 0.0
            er = int(cells[15].text.strip()) if cells[15].text.strip() else 0
            tbf = int(cells[18].text.strip()) if cells[18].text.strip() else 0
            h = int(cells[19].text.strip()) if cells[19].text.strip() else 0
            two_b = int(cells[20].text.strip()) if cells[20].text.strip() else 0
            three_b = int(cells[21].text.strip()) if cells[21].text.strip() else 0
            hr = int(cells[22].text.strip()) if cells[22].text.strip() else 0
            bb = int(cells[23].text.strip()) if cells[23].text.strip() else 0
            hp = int(cells[24].text.strip()) if cells[24].text.strip() else 0
            ib = int(cells[25].text.strip()) if cells[25].text.strip() else 0
            so = int(cells[26].text.strip()) if cells[26].text.strip() else 0
            era = float(cells[30].text.strip()) if cells[30].text.strip() else 0.0
            whip = float(cells[-2].text.strip()) if cells[-2].text.strip() else 0
            war = float(cells[-1].text.strip()) if cells[-1].text.strip() else 0.0

            bb = bb + hp + ib

            data.append([year, games, win, lose, save, hold, ip, era, er, tbf, h, two_b, three_b, hr, bb, so, whip, war])

    df = pd.DataFrame(data, columns=columns)


    df.to_csv(f"{playerName}_stats.csv", index=False)

def main(name):
    player_id = getPlayerId(name)
    crawling(player_id=player_id, playerName=name)
    
if __name__ == "__main__":
    player_name = sys.argv[1]
    main(player_name)