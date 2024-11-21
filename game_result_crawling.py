import requests
import csv
import os
import sys

def game_crawling(year, month):
    headers = {
        "referer": "https://heroesbaseball.co.kr/games/schedule/list1st.do",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }

    url = f"https://heroesbaseball.co.kr/games/schedule/getSports2iScheduleList.do?searchYear={year:04}&searchMonth={month:02}&flag=1"
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        games_list = data.get("scheduleList", [])

        if games_list:
            file_path = os.path.join(f"{month:02}월_키움_경기결과.csv")

            with open(file_path, mode="w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["날짜", "상대 팀", "상대 점수", "키움 점수"])
                
                for game in games_list:
                    gday = game.get("gday")
                    home_team = game.get("home")
                    away_team = game.get("visit")
                    home_score = game.get("hscore", 0)
                    away_score = game.get("vscore", 0)

                    # 키움 팀과 관련된 경기만 필터링
                    if home_team == "키움":
                        writer.writerow([f"{year:04}-{month:02}-{gday}", away_team, away_score, home_score])
                    elif away_team == "키움":
                        writer.writerow([f"{year:04}-{month:02}-{gday}", home_team, home_score, away_score])
                    
            print(f"{file_path} 파일로 저장 완료!")
        else:
            print(f"{year}년 {month}월 데이터가 없습니다.")
    else:
        print(f"API 요청 실패 ({month}월), 상태 코드: {response.status_code}")

def main(year, month):
    game_crawling(year, month)

if __name__ == "__main__":
    year = sys.argv[1]
    month = sys.argv[2]
    main(year, month)
