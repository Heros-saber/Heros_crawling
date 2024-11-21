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

def convert_date(date_str):
    match = re.match(r'(\d{4})년 (\d{2})월 (\d{2})일', date_str)
    if match:
        year = match.group(1)
        month = match.group(2)
        day = match.group(3)
        
        date_obj = datetime(year=int(year), month=int(month), day=int(day))
        return date_obj.strftime('%Y-%m-%d')
    else:
        raise ValueError("Invalid date format")


def convert_pos_num(pos):
    pos_num = {"P":1 , "C":2, "1B":"3", "2B":"4", "3B":"5", "SS":"6", "LF":"7", "CF":"8", "RF":"9", "DH":"10"}
    return pos_num[pos]

def convert_Batting_Throw(info):
    batt_dict = {'좌타':False, '우타':True}
    throw_dict = {'좌투':False, '우투':True}
    return throw_dict[info[0:2]], batt_dict[info[2:4]]

def crawling(player_id, playerName):
    columns = ["playerName", "playerBorn", "playerDraft", "playerPos", "playerBattingSide", "playerThrowSide"]
    url = f'https://statiz.sporki.com/player/?m=playerinfo&p_no={player_id}'

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    name = soup.find('div', class_='name').text.strip()

    position_info = [span.text.strip() for span in soup.find('div', class_='con').find_all('span')]

    man_info = {}
    for li in soup.find_all('li'):
        label = li.find('span')  
        if label:
            label_text = label.text.strip().replace(":", "") 
            value_text = li.get_text().replace(label_text, "").strip()
            man_info[label_text] = value_text

    throw, batt = convert_Batting_Throw(position_info[2])

    new_data = {
        "playerName": playerName,
        "playerBorn": convert_date(man_info.get('생년월일')),
        "playerDraft": man_info.get('신인지명'),
        "playerPos": convert_pos_num(position_info[1]),
        "playerBattingSide": batt,
        "playerThrowSide": throw
    }

    df = pd.DataFrame([new_data], columns=["playerName", "playerBorn", "playerDraft", "playerPos", "playerBattingSide", "playerThrowSide"])
    df.to_csv(f"{new_data['playerName']}_정보.csv", index=False)

def main(name):
    if name != '김도영':
        player_id = getPlayerId(name)
    else:
        player_id = 15056
        
    crawling(player_id=player_id, playerName=name)
    
if __name__ == "__main__":
    player_name = sys.argv[1]
    main(player_name)