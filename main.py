from steam_web_api import Steam
from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN
import config
import requests
import time

from pprint import pprint
def main():
    games = get_playtime(["Bloodborne"], 0)

    if notion_db(games):
        print("Success")
    else:
        print("Failed")


#ゲームのプレイ時間を取得
def get_playtime(fillter=[], filter_time=0):
    KEY = config.steam_key
    uid = config.steam_id
    steam = Steam(KEY)
    games = []
    for game in steam.users.get_owned_games(uid)["games"]:
        name = game["name"]
        time = int(Decimal(int(game["playtime_forever"]) / 60).quantize(Decimal('0'), rounding=ROUND_HALF_UP))
        if time < filter_time:
            continue
        games.append((name, time))
    
    #特定のゲームを除外する
    for f in fillter:
        games = [game for game in games if f != game[0]]
    
    games.sort(key=lambda x: x[1], reverse=True)
    return games

def notion_db(data):
    KEY = config.ntn_key
    DBID = config.ntn_dbid
    DBURL = f"https://api.notion.com/v1/databases/{DBID}"
    PAGEURL = "https://api.notion.com/v1/pages"

    headers = {
        "Authorization":"Bearer "+KEY,
        "Notion-Version":"2022-06-28",
        "Content-Type":"application/json",
    }
    #データベースのテーブル情報を取得
    def get_db():
        r = requests.get(DBURL, headers=headers)
        data = r.json()
        return data
    
    def get_game_list_from_db():
        game_list = []
        pages = requests.post(DBURL+"/query", headers=headers).json().get("results")
        for page in pages:
            game_list.append((page["properties"]["Game"]["title"][0]["text"]["content"], page["id"]))
        return game_list
    
    def create_page(title, content):
        json_data = {
            "parent": {"database_id": DBID},
            "properties": {
                "Game": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                },
                "Play Time": {
                    "number": content
                }
            }
        }
        r = requests.post(PAGEURL, headers=headers, json=json_data)

    def update_page(page_id, content):
        json_data = {
            "parent": {"database_id": DBID},
            "properties": {
                "Play Time": {
                    "number": content
                }
            }
        }
        r = requests.patch(PAGEURL+"/"+page_id, headers=headers, json=json_data)
    
    game_list_from_db = get_game_list_from_db()

    create_game_list = []
    update_game_list = []
    try:
        for game in data:
            if game[0] not in [g[0] for g in game_list_from_db]:
                create_page(game[0], game[1])
                create_game_list.append(game[0])
            else:
                update_page([g[1] for g in game_list_from_db if g[0] == game[0]][0], game[1])
                update_game_list.append(game[0])
            time.sleep(3.0)
        
        print("Create: ", create_game_list)
        print("Update: ", update_game_list)
        return 1
    except:
        return 0

if __name__ == "__main__":
    main()
