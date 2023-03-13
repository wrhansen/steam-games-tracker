import logging
import os
import sys
from typing import List

import requests

from data_objects import Achievement, Game, Page

STEAM_API_KEY = os.environ["STEAM_API_KEY"]
STEAM_ID = os.environ["STEAM_ID"]
NOTION_API_KEY = os.environ["NOTION_API_KEY"]
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
NOTION_VERSION = "2022-06-28"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("")


def fetch_steam_games_data() -> List[Game]:
    logger.info("Fetching Game Data From Steam...")
    # Get Games Data
    response = requests.get(
        "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/",
        params={"key": STEAM_API_KEY, "steamid": STEAM_ID, "include_appinfo": "1"},
    )
    games_data = response.json()

    logger.info(f"Found {games_data['response']['game_count']} games.")

    games: List[Game] = []

    for game_dict in games_data["response"]["games"]:
        game = Game(**game_dict)
        games.append(game)
        # Only lookup games that I have played
        if game.playtime_forever > 0:
            logger.info(f"Looking up info for game with appid {game.appid}...")
            response = requests.get(
                "http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/",
                params={
                    "key": STEAM_API_KEY,
                    "steamid": STEAM_ID,
                    "appid": game.appid,
                },
            )
            game_achievements = response.json()
            if game_achievements["playerstats"]["success"] is False:
                logger.info(f"No info for game {game.appid}")
                continue

            game.name = game_achievements["playerstats"]["gameName"]
            if "achievements" not in game_achievements["playerstats"]:
                logger.info(f"{game.name} does not have achievements.")
                continue

            achievments_array = game_achievements["playerstats"]["achievements"]
            for achievement_dict in achievments_array:
                achievement = Achievement(**achievement_dict)
                game.achievements.append(achievement)
    return games


def get_notion_page_data():
    page_data = []
    start_cursor = None
    while True:
        data = {"page_size": 100}
        if start_cursor:
            data["start_cursor"] = start_cursor
        response = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query",
            json=data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Notion-Version": NOTION_VERSION,
                "Authorization": f"Bearer {NOTION_API_KEY}",
            },
        )
        response_data = response.json()
        page_data.extend(response_data["results"])

        if response_data["next_cursor"]:
            start_cursor = response_data["next_cursor"]
        else:
            break
    return page_data


def create_notion_pages(games: List[Game]):
    for game in games:
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers={
                "Accept": "application/json",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
                "Authorization": f"Bearer {NOTION_API_KEY}",
            },
            json={
                "parent": {"database_id": NOTION_DATABASE_ID},
                "properties": {
                    "Name": {
                        "title": [
                            {
                                "type": "text",
                                "text": {"content": game.name, "link": None},
                            }
                        ]
                    },
                    "appid": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": str(game.appid), "link": None},
                            }
                        ]
                    },
                    "Achievements Completed": {
                        "number": game.successful_achievements()
                    },
                    "Total Achievements": {"number": game.total_achievements()},
                    "Last Played": {
                        "date": {"start": game.rtime_last_played.isoformat()}
                    },
                    "Perfect Game": {"checkbox": game.has_perfect_achievements()},
                    "Was Perfect": {"checkbox": False},
                },
                "icon": {"type": "external", "external": {"url": game.img_icon_url}},
                "cover": {"type": "external", "external": {"url": game.header_logo}},
            },
        )
        response_data = response.json()
        if response_data.get("object") == "error":
            logger.error(f"Error creating page. Response: {response_data}")

    logger.info(f"created {len(games)} pages")


def update_notion_pages(pages: List[Page]):
    for page in pages:
        response = requests.patch(
            f"https://api.notion.com/v1/pages/{page.page_id}",
            headers={
                "Accept": "application/json",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
                "Authorization": f"Bearer {NOTION_API_KEY}",
            },
            json={
                "properties": {
                    "Name": {
                        "title": [
                            {
                                "type": "text",
                                "text": {"content": page.name, "link": None},
                            }
                        ]
                    },
                    "appid": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {"content": str(page.appid), "link": None},
                            }
                        ]
                    },
                    "Achievements Completed": {"number": page.achievements_completed},
                    "Total Achievements": {"number": page.total_achievements},
                    "Last Played": {"date": {"start": page.last_played.isoformat()}},
                    "Perfect Game": {"checkbox": page.perfect_game},
                    "Was Perfect": {"checkbox": page.was_perfect},
                },
                "icon": {"type": "external", "external": {"url": page.icon}},
                "cover": {"type": "external", "external": {"url": page.cover}},
            },
        )
        response_data = response.json()
        if response_data.get("object") == "error":
            logger.error(f"Error updating page. Response: {response_data}")
    logger.info(f"updated {len(pages)} pages")


def sync_notion_library(games: List[Game]):
    page_data = get_notion_page_data()
    notion_games = []
    for page in page_data:
        page = Page.from_notion_page(page)
        notion_games.append(page)

    game_dict = {game.appid: game for game in games}
    pages_dict = {page.appid: page for page in notion_games}

    updates = []
    new: List[Game] = []
    for game_appid, game in game_dict.items():
        if game_appid not in pages_dict.keys():
            if game.valid():
                new.append(game)
            continue

        page = pages_dict[game_appid]
        update = False

        if page.name != game.name:
            update = True
            page.name = game.name
        if page.last_played.isoformat() != game.rtime_last_played.isoformat():
            update = True
            page.last_played = game.rtime_last_played
        if page.achievements_completed != game.successful_achievements():
            update = True
            page.achievements_completed = game.successful_achievements()
        if page.perfect_game != game.has_perfect_achievements():
            update = True
            page.perfect_game = game.has_perfect_achievements()
        if page.total_achievements != game.total_achievements():
            update = True
            if page.perfect_game is True:
                page.perfect_game = False
                page.was_perfect = True
        if update:
            page.icon = game.img_icon_url
            page.cover = game.header_logo
            updates.append(page)

    if new:
        logger.info(f"{len(new)} new pages to create.")
        create_notion_pages(new)
    if updates:
        logger.info(f"{len(updates)} pages to update.")
        update_notion_pages(updates)
    if not new and not updates:
        logger.info("Nothing to sync.")


def main(args):
    games = fetch_steam_games_data()
    for game in games:
        logger.info(game.get_status())

    sync_notion_library(games)
    logger.info("Sync Complete")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
