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
    mapping = {"1":"구사율", "6":"타율"}
    for key, element in mapping.items():
        url = f"https://statiz.sporki.com/player/?m=analysis&p_no={player_id}&pos=pitching&year=2024&si1=3&si2={key}"

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 각 표 데이터 저장을 위한 리스트
        tables_data = []

        # "box_item_3dan" 클래스 내부에서 모든 표 데이터 추출
        tables = soup.find_all('div', class_='box_item_3dan')
        for table in tables:
            # 각 표 안의 제목과 데이터 추출
            titles = table.find_all('div', class_='h_tit')
            item_containers = table.find_all('div', class_='item_con')
            
            # 각 제목에 대해 데이터 추출
            for title, item_container in zip(titles, item_containers):
                # 표 제목
                title_text = title.get_text(strip=True)
                
                # 타율 값과 PA 값을 저장할 리스트
                batting_averages = []
                pa_values = []
                
                # "info" 클래스 내의 타율 데이터 및 PA 수 추출
                items = item_container.find_all('div', class_='info')
                for item in items:
                    # 타율 수치 추출
                    avg = item.find('strong').get_text(strip=True)
                    batting_averages.append(avg)
                    
                    # PA 수 추출
                    pa_text = item.find('span').get_text(strip=True)
                    pa_value = pa_text.split()[-1] if "PA" in pa_text else None  # "PA 5"에서 숫자 부분만 추출
                    pa_values.append(pa_value)
                
                # 25개의 데이터가 맞는지 확인하고 부족하면 None으로 채움
                if len(batting_averages) < 25:
                    batting_averages.extend([None] * (25 - len(batting_averages)))
                    pa_values.extend([None] * (25 - len(pa_values)))
                
                # DataFrame에 저장할 행 생성
                row = [title_text] + batting_averages[:25] + pa_values[:25]  # 타율 제목 + 25개의 타율 값 + 25개의 PA 값
                tables_data.append(row)
        
        # DataFrame 생성
        columns = [element] + [f"{element}_{i}" for i in range(1, 26)] + [f"PA_{i}" for i in range(1, 26)]
        df = pd.DataFrame(tables_data, columns=columns)

        # CSV 파일로 저장
        df.to_csv(f"{name}_zone_{element}.csv", index=False, encoding='utf-8-sig')
        print(f"{name}_zone_{element}.csv 파일이 저장되었습니다.")

def preprocessing(playerName):
    index_list = ['구사율 - ', '타율 - ']
    removing_index = ['너클볼', '우언', '주자없음', '주자있음', '득점권', '양타', '구종모름']
    count_index = ['초구', '스트라이크 > 볼', '볼 > 스트라이크', '스트라이크 = 볼']
    fast_ball_index = ['투심', '포심', '커터', '싱커']
    droping_columns = ['PA_' + str(i+1) for i in range(25)]
    files = ['_zone_구사율.csv', '_zone_타율.csv']

    for i in range(2):
        # 파일 읽기
        df = pd.read_csv(playerName + files[i])
        df = df.drop(columns=droping_columns, errors='ignore')

        df.iloc[:, 0] = df.iloc[:, 0].apply(lambda x: x.replace(index_list[i], '') if index_list[i] in x else x)

        # 제거할 행 필터링 (첫 번째 열의 값이 `removing_index`에 포함된 경우)
        df = df[~df.iloc[:, 0].isin(removing_index)]

        # count 행을 합쳐서 하나의 행으로 만들기
        if all(row in df.iloc[:, 0].values for row in count_index):
            count_sum = df[df.iloc[:, 0].isin(count_index)].iloc[:, 1:].mean()
            count_sum = count_sum.round(3)
            count_sum_row = pd.DataFrame([['카운트'] + count_sum.tolist()], columns=df.columns)
            df = pd.concat([df, count_sum_row], ignore_index=True)
            df = df[~df.iloc[:, 0].isin(count_index)]

        existing_fast_ball = [row for row in fast_ball_index if row in df.iloc[:, 0].values]
        if existing_fast_ball:  # 존재하는 값이 하나라도 있다면
            # 기존 값으로 작업 진행
            fastball_sum = df[df.iloc[:, 0].isin(existing_fast_ball)].iloc[:, 1:].mean()
            fastball_sum = fastball_sum.round(3)
            fastball_sum_row = pd.DataFrame([['패스트볼'] + fastball_sum.tolist()], columns=df.columns)
            
            # 기존 데이터프레임에 추가
            df = pd.concat([df, fastball_sum_row], ignore_index=True)
            df = df[~df.iloc[:, 0].isin(existing_fast_ball)]  # 기존 행 삭제

        df.loc[df.iloc[:, 0] == '2S 이후', df.columns[0]] = '결정구'
        df.to_csv(playerName + files[i], index=False)

def player_stat_crawling(player_id, playerName):
    url = f"https://statiz.sporki.com/player/?m=year&p_no={player_id}"  # 실제 URL로 변경
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # 데이터 추출
    table = soup.find("table")
    rows = table.find("tbody").find_all("tr")

    data = []
    columns = ["year", "games", "win", "lose", "saves", "hold", "ip", "era", "er", "tbf", "h", "2b", "3b", "hr", "bb", "so", "whip", "war"]
    basic_mapping = {"year":0, "games":4, "win":10, "lose":11, "save":12, "hold":13, "ip":14, "er":15, "tbf":18, "h":19,
                     "two_b":20, "three_b":21, "hr":22, "bb":23, "hp":24, "ib":25, "so":26, "era":30, "whip":34, "war":35}
    for row in rows:
        cells = row.find_all("td")
        if len(cells) > 0:
            if not cells[0].text.strip().isdigit():
                year = "-"
                index_mapping = {key: value-1 for (key, value) in basic_mapping.items()}
            else:
                index_mapping = basic_mapping.copy()
                year = cells[0].text.strip()
            
            # 필요한 값들을 문자열에서 실수로 변환
            games = int(cells[index_mapping["games"]].text.strip()) if cells[index_mapping["games"]].text.strip() else 0
            win = int(cells[index_mapping["win"]].text.strip()) if cells[index_mapping["win"]].text.strip() else 0
            lose = int(cells[index_mapping["lose"]].text.strip()) if cells[index_mapping["lose"]].text.strip() else 0
            save = int(cells[index_mapping["save"]].text.strip()) if cells[index_mapping["save"]].text.strip() else 0
            hold = int(cells[index_mapping["hold"]].text.strip()) if cells[index_mapping["hold"]].text.strip() else 0
            ip = float(cells[index_mapping["ip"]].text.strip()) if cells[index_mapping["ip"]].text.strip() else 0.0
            er = int(cells[index_mapping["er"]].text.strip()) if cells[index_mapping["er"]].text.strip() else 0
            tbf = int(cells[index_mapping["tbf"]].text.strip()) if cells[index_mapping["tbf"]].text.strip() else 0
            h = int(cells[index_mapping["h"]].text.strip()) if cells[index_mapping["h"]].text.strip() else 0
            two_b = int(cells[index_mapping["two_b"]].text.strip()) if cells[index_mapping["two_b"]].text.strip() else 0
            three_b = int(cells[index_mapping["three_b"]].text.strip()) if cells[index_mapping["three_b"]].text.strip() else 0
            hr = int(cells[index_mapping["hr"]].text.strip()) if cells[index_mapping["hr"]].text.strip() else 0
            bb = int(cells[index_mapping["bb"]].text.strip()) if cells[index_mapping["bb"]].text.strip() else 0
            hp = int(cells[index_mapping["hp"]].text.strip()) if cells[index_mapping["hp"]].text.strip() else 0
            ib = int(cells[index_mapping["ib"]].text.strip()) if cells[index_mapping["ib"]].text.strip() else 0
            so = int(cells[index_mapping["so"]].text.strip()) if cells[index_mapping["so"]].text.strip() else 0
            era = float(cells[index_mapping["era"]].text.strip()) if cells[index_mapping["era"]].text.strip() else 0.0
            whip = float(cells[index_mapping["whip"]].text.strip()) if cells[index_mapping["whip"]].text.strip() else 0.0
            war = float(cells[index_mapping["war"]].text.strip()) if cells[index_mapping["war"]].text.strip() else 0.0

            bb = bb + hp + ib

            data.append([year, games, win, lose, save, hold, ip, era, er, tbf, h, two_b, three_b, hr, bb, so, whip, war])

    df = pd.DataFrame(data, columns=columns)
    df.to_csv(f"{playerName}_stats.csv", index=False)

def main(name):
    id_mapping = {"김연주":16127, "김윤하":16123, "박범준":16133, "조상우":11126, "김성민":12918}
    if name in id_mapping.keys():
        player_id = id_mapping[name]
    else:
        player_id = getPlayerId(name)
    
    if(player_id != -1):
        player_info_crawling(player_id=player_id, playerName=name)
        player_stat_crawling(player_id=player_id, playerName=name)
        player_zone_crawling(player_id=player_id, name=name)
        preprocessing(playerName=name)
    else:
        print("선수를 찾을 수 없습니다.")

if __name__ == "__main__":
    player_name = sys.argv[1]
    main(player_name)
