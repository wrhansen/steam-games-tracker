import datetime
import inspect
from dataclasses import dataclass, field

import pytz


@dataclass
class Achievement:
    apiname: str
    achieved: bool
    unlocktime: datetime.datetime

    def __post_init__(self):
        self.unlocktime = datetime.datetime.fromtimestamp(self.unlocktime)
        self.achieved = bool(self.achieved)


@dataclass
class Game:
    appid: str
    playtime_forever: int = 0
    playtime_windows_forever: int = 0
    playtime_mac_forever: int = 0
    playtime_linux_forever: int = 0
    playtime_2weeks: int = 0
    rtime_last_played: datetime.datetime = 0
    achievements: list[Achievement] = field(default_factory=list)
    name: str = ""
    img_icon_url: str = ""
    header_logo: str = ""
    has_community_visible_stats: bool = False
    content_descriptorids: list[int] = field(default_factory=list)
    has_leaderboards: bool = False

    @classmethod
    def from_dict(cls, **env):
        return cls(
            **{k: v for k, v in env.items() if k in inspect.signature(cls).parameters}
        )

    def __post_init__(self):
        self.rtime_last_played = datetime.datetime.fromtimestamp(
            self.rtime_last_played, tz=pytz.timezone("US/Eastern")
        ).replace(second=0, microsecond=0)
        self.appid = str(self.appid)
        if self.img_icon_url:
            self.img_icon_url = f"http://media.steampowered.com/steamcommunity/public/images/apps/{self.appid}/{self.img_icon_url}.jpg"
        self.header_logo = (
            f"https://steamcdn-a.akamaihd.net/steam/apps/{self.appid}/header.jpg"
        )

    def successful_achievements(self) -> int:
        return len(
            list(
                achievement
                for achievement in self.achievements
                if achievement.achieved is True
            )
        )

    def has_perfect_achievements(self) -> bool:
        return all(achievement.achieved is True for achievement in self.achievements)

    def total_achievements(self) -> int:
        return len(self.achievements)

    def get_status(self) -> str:
        successful = self.successful_achievements()
        total = self.total_achievements()
        if total == 0:
            return f"{self.name}: No Achievements"
        return f"{self.name}: {successful}/{total} ({successful/total * 100:.2f}%)"

    def valid(self) -> bool:
        return self.successful_achievements() > 0 and bool(self.name)


@dataclass
class Page:
    page_id: str
    appid: str
    name: str
    last_played: datetime.datetime
    achievements_completed: int
    last_edited_time: datetime.datetime
    total_achievements: int
    perfect_game: bool
    was_perfect: bool
    playtime: int = 0
    icon: str = ""
    cover: str = ""

    @classmethod
    def from_notion_page(cls, page_data):
        properties = page_data["properties"]

        cover = ""
        if page_data["cover"] is not None:
            cover = page_data["cover"]["external"]["url"]

        icon = ""
        if page_data["icon"] is not None:
            icon = page_data["icon"]["external"]["url"]

        return Page(
            page_id=page_data["id"],
            appid=str(properties["appid"]["rich_text"][0]["plain_text"]),
            name=properties["Name"]["title"][0]["plain_text"],
            last_played=datetime.datetime.fromisoformat(
                properties["Last Played"]["date"]["start"]
            ),
            achievements_completed=properties["Achievements Completed"]["number"],
            last_edited_time=datetime.datetime.fromisoformat(
                properties["Last edited time"]["last_edited_time"]
            ),
            total_achievements=properties["Total Achievements"]["number"],
            perfect_game=properties["Perfect Game"]["checkbox"],
            was_perfect=properties["Was Perfect"]["checkbox"],
            icon=icon,
            cover=cover,
            playtime=properties["Playtime Duration"]["number"],
        )
