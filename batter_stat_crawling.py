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
    columns = ["year", "h_avg", "obp", "slg", "ops", "wrc_plus", "h", "2b", "3b", "hr", "rbi", "sb", "bb", "so", "pa", "ab", "war"]

    for row in rows:
        cells = row.find_all("td")
        if len(cells) > 0:
            year = cells[0].text.strip()
            
            avg = float(cells[26].text.strip()) if cells[26].text.strip() else 0.0
            obp = float(cells[27].text.strip()) if cells[27].text.strip() else 0.0
            slg = float(cells[28].text.strip()) if cells[28].text.strip() else 0.0
            ops = float(cells[29].text.strip()) if cells[29].text.strip() else 0.0
            wrc_plus = float(cells[31].text.strip()) if cells[31].text.strip() else 0.0
            h = int(cells[11].text.strip()) if cells[11].text.strip() else 0
            two_b = int(cells[12].text.strip()) if cells[12].text.strip() else 0
            three_b = int(cells[13].text.strip()) if cells[13].text.strip() else 0
            hr = int(cells[14].text.strip()) if cells[14].text.strip() else 0
            rbi = int(cells[16].text.strip()) if cells[16].text.strip() else 0
            sb = int(cells[17].text.strip()) if cells[17].text.strip() else 0
            bb = int(cells[19].text.strip()) if cells[19].text.strip() else 0
            hp = int(cells[20].text.strip()) if cells[20].text.strip() else 0
            ib = int(cells[21].text.strip()) if cells[21].text.strip() else 0
            so = int(cells[22].text.strip()) if cells[22].text.strip() else 0
            pa = int(cells[7].text.strip()) if cells[7].text.strip() else 0
            ab = int(cells[9].text.strip()) if cells[9].text.strip() else 0
            war = float(cells[-1].text.strip()) if cells[-1].text.strip() else 0.0

            # bb, hp, ib를 더하고 bb로만 남기기
            bb = bb + hp + ib
            
            data.append([year, avg, obp, slg, ops, wrc_plus, h, two_b, three_b, hr, rbi, sb, bb, so, pa, ab, war])

    df = pd.DataFrame(data, columns=columns)
    df.to_csv(f"{playerName}_stats.csv", index=False)

def main(name):
    if name != '김도영':
        player_id = getPlayerId(name)
    else:
        player_id = 15056
        
    crawling(player_id=player_id, playerName=name)
    
if __name__ == "__main__":
    player_name = sys.argv[1]
    main(player_name)