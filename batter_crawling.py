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
        player_id = -1

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
    batt_dict = {'좌타':False, '우타':True, '양타':True}
    throw_dict = {'좌투':False, '우투':True, '양투':True}
    return throw_dict[info[0:2]], batt_dict[info[2:4]]

def player_info_crawling(player_id, playerName):
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
    df.to_csv(f"{new_data['playerName']}_info.csv", index=False)

def player_zone_crawling(player_id, name):
    mapping = {"4":"스윙율", "5":"컨택율", "6":"타율", "9":"ops"}
    for key, element in mapping.items():
        url = f"https://statiz.sporki.com/player/?m=analysis&p_no={player_id}&pos=batting&year=2024&si1=3&si2={key}"

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        tables_data = []
        tables = soup.find_all('div', class_='box_item_3dan')
        for table in tables:
            titles = table.find_all('div', class_='h_tit')
            item_containers = table.find_all('div', class_='item_con')

            for title, item_container in zip(titles, item_containers):
                title_text = title.get_text(strip=True)
                batting_averages = []
                pa_values = []

                items = item_container.find_all('div', class_='info')
                for item in items:
                    avg = item.find('strong').get_text(strip=True)
                    batting_averages.append(avg)
                
                if len(batting_averages) < 25:
                    batting_averages.extend([None] * (25 - len(batting_averages)))
                
                row = [title_text] + batting_averages[:25]
                tables_data.append(row)
    
        columns = [element] + [f"{element}_{i}" for i in range(1, 26)]
        df = pd.DataFrame(tables_data, columns=columns)

        df.to_csv(f"{name}_zone_{element}.csv", index=False, encoding='utf-8-sig')
        print(f"{name}_zone_{element}.csv 파일이 저장되었습니다.")

def preprocessing(name):
    files = ['_zone_타율.csv', '_zone_ops.csv', '_zone_컨택율.csv', '_zone_스윙율.csv']
    index_list = ['타율 - ', 'OPS - ', 'Contact% - ', 'Swing% - '] 
    removing_index = ['너클볼', '우언', '주자없음', '주자있음', '득점권', '구종모름']
    count_index = ['초구', '스트라이크 > 볼', '볼 > 스트라이크', '스트라이크 = 볼']
    fast_ball_index = ['투심', '포심', '커터', '싱커']

    
    for i in range(4):
        df = pd.read_csv(name + files[i])

        df.iloc[:, 0] = df.iloc[:, 0].apply(lambda x: x.replace(index_list[i], '') if index_list[i] in x else x)

        removing_rows = [index for index in removing_index]
        df = df[~df.iloc[:, 0].isin(removing_rows)]

        count_rows = [index for index in count_index]
        if all(row in df.iloc[:, 0].values for row in count_rows):
            count_sum = df[df.iloc[:, 0].isin(count_rows)].iloc[:, 1:].mean()
            count_sum = count_sum.round(3)
            count_sum_row = pd.DataFrame([['카운트'] + count_sum.tolist()], columns=df.columns)
            df = pd.concat([df, count_sum_row], ignore_index=True)
            df = df[~df.iloc[:, 0].isin(count_rows)]

        existing_fast_ball = [row for row in fast_ball_index if row in df.iloc[:, 0].values]
        if existing_fast_ball:
            fastball_sum = df[df.iloc[:, 0].isin(existing_fast_ball)].iloc[:, 1:].mean()
            fastball_sum = fastball_sum.round(3)
            fastball_sum_row = pd.DataFrame([['패스트볼'] + fastball_sum.tolist()], columns=df.columns)

            df = pd.concat([df, fastball_sum_row], ignore_index=True)
            df = df[~df.iloc[:, 0].isin(existing_fast_ball)] 

        df.loc[df.iloc[:, 0] == '2S 이후', df.columns[0]] = '결정구'
        df.to_csv(name + files[i], index=False)

def player_stat_crawling(player_id, playerName):
    url = f"https://statiz.sporki.com/player/?m=year&p_no={player_id}" 
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    rows = table.find("tbody").find_all("tr")

    data = []
    columns = ["year", "h_avg", "obp", "slg", "ops", "wrc_plus", "h", "2b", "3b", "hr", "rbi", "sb", "bb", "so", "pa", "ab", "war"]
    basic_mapping = { "year": 0, "h_avg": 26, "obp": 27, "slg": 28, "ops": 29,"wrc_plus": 31, "h": 11, "2b": 12, "3b": 13,
                     "hr": 14,"rbi": 16, "sb": 17, "bb": 19, "hp": 20, "ib": 21, "so": 22, "pa": 7, "ab": 9, "war": 32}

    for row in rows:
        cells = row.find_all("td")
        if len(cells) > 0:
            if not cells[0].text.strip().isdigit():
                year = "-"
                index_mapping = {key: value-1 for (key, value) in basic_mapping.items()}
            else:
                index_mapping = basic_mapping.copy()
                year = cells[0].text.strip()
            
            h_avg = float(cells[index_mapping["h_avg"]].text.strip()) if cells[index_mapping["h_avg"]].text.strip() else 0.0
            obp = float(cells[index_mapping["obp"]].text.strip()) if cells[index_mapping["obp"]].text.strip() else 0.0
            slg = float(cells[index_mapping["slg"]].text.strip()) if cells[index_mapping["slg"]].text.strip() else 0.0
            ops = float(cells[index_mapping["ops"]].text.strip()) if cells[index_mapping["ops"]].text.strip() else 0.0
            wrc_plus = float(cells[index_mapping["wrc_plus"]].text.strip()) if cells[index_mapping["wrc_plus"]].text.strip() else 0.0
            h = int(cells[index_mapping["h"]].text.strip()) if cells[index_mapping["h"]].text.strip() else 0
            two_b = int(cells[index_mapping["2b"]].text.strip()) if cells[index_mapping["2b"]].text.strip() else 0
            three_b = int(cells[index_mapping["3b"]].text.strip()) if cells[index_mapping["3b"]].text.strip() else 0
            hr = int(cells[index_mapping["hr"]].text.strip()) if cells[index_mapping["hr"]].text.strip() else 0
            rbi = int(cells[index_mapping["rbi"]].text.strip()) if cells[index_mapping["rbi"]].text.strip() else 0
            sb = int(cells[index_mapping["sb"]].text.strip()) if cells[index_mapping["sb"]].text.strip() else 0
            bb = int(cells[index_mapping["bb"]].text.strip()) if cells[index_mapping["bb"]].text.strip() else 0
            hp = int(cells[index_mapping["hp"]].text.strip()) if cells[index_mapping["hp"]].text.strip() else 0
            ib = int(cells[index_mapping["ib"]].text.strip()) if cells[index_mapping["ib"]].text.strip() else 0
            so = int(cells[index_mapping["so"]].text.strip()) if cells[index_mapping["so"]].text.strip() else 0
            pa = int(cells[index_mapping["pa"]].text.strip()) if cells[index_mapping["pa"]].text.strip() else 0
            ab = int(cells[index_mapping["ab"]].text.strip()) if cells[index_mapping["ab"]].text.strip() else 0
            war = float(cells[index_mapping["war"]].text.strip()) if cells[index_mapping["war"]].text.strip() else 0.0

            bb = bb + hp + ib

            data.append([year, h_avg, obp, slg, ops, wrc_plus, h, two_b, three_b, hr, rbi, sb, bb, so, pa, ab, war])

    df = pd.DataFrame(data, columns=columns)
    df.to_csv(f"{playerName}_stats.csv", index=False)

def main(name):
    id_mapping = {"고영우":16128, "김재현":10870, "김병휘":14577, "박주홍":14580, "박수종":15132, "장재영":14784, "원성준":16136}
    if name in id_mapping.keys():
        player_id = id_mapping[name]
    else:
        player_id = getPlayerId(name)
    
    if(player_id != -1):
        player_info_crawling(player_id=player_id, playerName=name)
        player_stat_crawling(player_id=player_id, playerName=name)
        player_zone_crawling(player_id=player_id, name=name)
        preprocessing(name=name)
    else:
        print("선수를 찾을 수 없습니다.")

if __name__ == "__main__":
    player_name = sys.argv[1]
    main(player_name)

