# batter_crawling.py
import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

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

    import re
    match = re.search(r'p_no=(\d+)', final_url)

    if match:
        player_id = match.group(1)
    else:
        print("Player ID not found in the final URL.")
        driver.quit()
        sys.exit() 

    driver.quit()
    return player_id

def crawling(player_id, name):
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
                    
                    pa_text = item.find('span').get_text(strip=True)
                    pa_value = pa_text.split()[-1] if "PA" in pa_text else None
                    pa_values.append(pa_value)
                
                if len(batting_averages) < 25:
                    batting_averages.extend([None] * (25 - len(batting_averages)))
                    pa_values.extend([None] * (25 - len(pa_values)))
                
                row = [title_text] + batting_averages[:25] + pa_values[:25]
                tables_data.append(row)
        
        columns = [element] + [f"{element}_{i}" for i in range(1, 26)] + [f"PA_{i}" for i in range(1, 26)]
        df = pd.DataFrame(tables_data, columns=columns)

        df.to_csv(f"{name}_zone_{element}.csv", index=False, encoding='utf-8-sig')
        print(f"{name}_zone_{element}.csv 파일이 저장되었습니다.")

def preprocessing(name):
    files = ['_zone_타율.csv', '_zone_ops.csv', '_zone_컨택율.csv', '_zone_스윙율.csv']
    index_list = ['타율 - ', 'OPS - ', 'Contact% - ', 'Swing% - '] 
    removing_index = ['너클볼', '우언', '주자없음', '주자있음', '득점권', '구종모름']
    count_index = ['초구', '스트라이크 > 볼', '볼 > 스트라이크', '스트라이크 = 볼']
    fast_ball_index = ['투심', '포심', '커터']
    droping_columns = ['PA_' + str(i+1) for i in range(25)]

    
    for i in range(4):
        df = pd.read_csv(name + files[i])
        df = df.drop(columns=droping_columns)

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
        
def main(name):
    if name != '김도영':
        player_id = getPlayerId(name)
    else:
        player_id = 15056
    crawling(player_id=player_id, name=name)
    preprocessing(name)

if __name__ == "__main__":
    player_name = sys.argv[1]
    main(player_name)