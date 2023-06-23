from dataclasses import dataclass
from enum import Enum
import random
from typing import Optional, cast
import logging
from karaoke.storage import redis_api

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class Rating(Enum):
    DONT_KNOW = 0
    SING_ALONG = 1
    CAN_TAKE_THE_MIC = 2
    NEED_THE_MIC = 3


class Song:
    def __init__(self) -> None:
        self.id: int = -1
        self.title: str = ""
        self.artist: str = ""
        self.video_link: str = ""

    @classmethod
    def create(cls, title: str, artist: str, video_link: str) -> "Song":
        self: Song = cls()
        self.id = cls.generate_id()
        self.set_title(title)
        self.set_artist(artist)
        self.set_video_link(video_link)
        return self

    @classmethod
    def get_song_counter(cls) -> int:
        counter: Optional[int] = redis_api.get("song:id:counter")
        if counter is None:
            raise RuntimeError("Song counter not initialized.")
        return int(counter)

    @classmethod
    def generate_id(cls) -> int:
        return redis_api.incr("song:id:counter")

    @classmethod
    def get_song_title(cls, song_id: int) -> str:
        value = redis_api.get(f"song:{song_id}:title")
        if value is None:
            raise KeyError(f"Song with id {song_id} not found.")
        return value.decode("utf-8")

    @classmethod
    def get_song_artist(cls, song_id: int) -> str:
        value = redis_api.get(f"song:{song_id}:artist")
        if value is None:
            raise KeyError(f"Song with id {song_id} not found.")
        return value.decode("utf-8")

    @classmethod
    def get_song_video_link(cls, song_id: int) -> str:
        value = redis_api.get(f"song:{song_id}:video_link")
        if value is None:
            raise KeyError(f"Song with id {song_id} not found.")
        return value.decode("utf-8")

    @classmethod
    def find_by_id(cls, song_id: int) -> "Song":
        self = Song()
        self.id = song_id
        self.title = cls.get_song_title(song_id)
        self.artist = cls.get_song_artist(song_id)
        self.video_link = cls.get_song_video_link(song_id)
        return self

    @classmethod
    def get_all_songs(cls) -> list["Song"]:
        songs = []
        for song_id in range(cls.get_song_counter() + 1):
            try:
                songs.append(cls.find_by_id(song_id=song_id))
            except KeyError:
                pass
        return songs

    def set_title(self, title: str) -> None:
        self.title = title
        redis_api.set(f"song:{self.id}:title", title)

    def set_artist(self, artist: str) -> None:
        self.artist = artist
        redis_api.set(f"song:{self.id}:artist", artist)

    def set_video_link(self, video_link: str) -> None:
        self.video_link = video_link
        redis_api.set(f"song:{self.id}:video_link", video_link)

    def get_score(self, session: "Session") -> int:
        score = 0
        for user in session.users:
            for rating in user.song_ratings:
                user.get_rating_for_song(self)
                score += session.get_rating_score(rating.rating)
        return score


def format_song_list(songs: list[Song]) -> str:
    return ", ".join([f"{s.title}" for s in songs])


class User:
    def __init__(self) -> None:
        self.id: int = -1
        self.name: str = ""
        self.song_ratings: list[UserSongRating] = []

    @classmethod
    def create(cls, name: str) -> "User":
        user: User = cls()
        user.id = cls.generate_id()
        user.set_name(name)
        return user

    @classmethod
    def get_user_counter(cls) -> int:
        counter: Optional[int] = redis_api.get("user:id:counter")
        if counter is None:
            raise RuntimeError("User counter not initialized.")
        return int(counter)

    @classmethod
    def generate_id(cls) -> int:
        return redis_api.incr("user:id:counter")

    @classmethod
    def get_user_name(cls, user_id: int) -> str:
        value = redis_api.get(f"user:{user_id}:name")
        if value is None:
            raise KeyError(f"User with id {user_id} does not exist.")
        return cast(bytes, value).decode("utf-8")

    @classmethod
    def find_by_id(cls, user_id: int) -> "User":
        self = cls()
        self.id = user_id
        self.name = cls.get_user_name(user_id)
        return self

    @classmethod
    def get_all_users(cls) -> list["User"]:
        users = []
        for user_id in range(cls.get_user_counter() + 1):
            try:
                users.append(cls.find_by_id(user_id=user_id))
            except KeyError:
                pass
        return users

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"

    def set_name(self, name: str) -> None:
        self.name = name
        redis_api.set(f"user:{self.id}:name", name)

    def get_rated_songs(self) -> list[Song]:
        return [rating.song for rating in self.song_ratings]

    def get_rating_for_song(self, song: Song) -> Rating:
        for rating in self.song_ratings:
            if rating.song == song:
                return rating.rating
        return Rating.DONT_KNOW


@dataclass
class UserSongRating:
    song: Song
    rating: Rating
    will_sing_alone: bool
    avoid_early: bool


class Session:
    def __init__(self) -> None:
        self.id: str = ""
        self.users: list[User] = []
        self.unplayed_songs: list[Song] = []
        self.user_scores: dict[User, int] = {}

    @classmethod
    def create(cls, users: list[User]) -> "Session":
        self: Session = cls()
        self.id = cls.generate_id()
        self.set_users(users)
        return self

    def set_users(self, users: list[User]) -> None:
        self.users = users
        for user in users:
            redis_api.sadd(f"session:id={self.id}:users", user.id)
        self.unplayed_songs = self.get_all_songs()
        for song in self.unplayed_songs:
            redis_api.sadd(f"session:id={self.id}:unplayed_songs", song.id)
        self.user_scores = {user: 0 for user in users}
        for user in users:
            redis_api.set(f"session:id={self.id}:user_scores:{user.id}", 0)

    @classmethod
    def find_by_id(cls, session_id: str) -> "Session":
        self: Session = cls()
        self.id = session_id
        self.users = [
            User.find_by_id(int(user_id))
            for user_id in redis_api.smembers(f"session:id={id}:users")
        ]
        self.unplayed_songs = [
            Song.find_by_id(int(song_id))
            for song_id in redis_api.smembers(
                f"session:id={id}:unplayed_songs"
            )
        ]
        self.user_scores = {
            user: int(
                cast(
                    str,
                    redis_api.get(f"session:id={id}:user_scores:{user.id}"),
                )
            )
            for user in self.users
        }
        return self

    @staticmethod
    def generate_id() -> str:
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        exists: bool = True
        new_id: str = ""
        while exists:
            new_id = "".join(random.choices(letters, k=4))
            exists = bool(redis_api.exists(f"session:id={new_id}"))
        return new_id

    def get_rating_score(self, rating: Rating) -> int:
        return {
            Rating.DONT_KNOW: -1,
            Rating.SING_ALONG: 1,
            Rating.CAN_TAKE_THE_MIC: 2,
            Rating.NEED_THE_MIC: 5,
        }[rating]

    def get_all_songs(self) -> list[Song]:
        all_songs: dict[int, Song] = {}
        for user in self.users:
            for song in user.get_rated_songs():
                all_songs[song.id] = song
        return list(all_songs.values())

    def get_combined_score(self, song: Song) -> int:
        score = 0
        for user in self.users:
            score += self.get_rating_score(user.get_rating_for_song(song))
        return score

    def prune_candidates_for_user(
        self, candidates: list[Song], user: User
    ) -> list[Song]:
        logger.info(f"Pruning candidates for {user.name}")
        pruned_candidates: list[Song] = []
        for rating in [
            Rating.NEED_THE_MIC,
            Rating.CAN_TAKE_THE_MIC,
            Rating.SING_ALONG,
        ]:
            if pruned_candidates:
                logger.info(
                    f"Pruned candidates: {format_song_list(pruned_candidates)}"
                )
                return pruned_candidates
            for song in candidates:
                if user.get_rating_for_song(song) == rating:
                    pruned_candidates.append(song)

        # This user wouldn't benefit from any of the candidates, so we'll
        # just return the original list
        logger.info(f"Pruning is not possible for {user.name}, not pruning.")
        return candidates

    def get_next_song(self) -> Optional[Song]:
        user_scores_str = ", ".join(
            [f"{u.name}: {s}" for u, s in self.user_scores.items()]
        )
        logger.info(f"Current user scores: {user_scores_str}")

        candidates = self.unplayed_songs
        sorted_users = sorted(self.users, key=lambda u: self.user_scores[u])
        for user in sorted_users:
            candidates = self.prune_candidates_for_user(candidates, user)
            if len(candidates) == 1:
                break
        logger.info(
            f"Found {len(candidates)} candidates: {format_song_list(candidates)}"
        )

        if not candidates:
            return None

        candidates.sort(key=lambda s: self.get_combined_score(s), reverse=True)
        max_score = self.get_combined_score(candidates[0])
        candidates = [
            s for s in candidates if self.get_combined_score(s) == max_score
        ]
        # picked: Song = random.choice(candidates)
        picked: Song = candidates[0]  # Not random for testing
        logger.info(f"Picked {picked.title}.")
        logger.info(f"Combined score: {self.get_combined_score(picked)}")
        self.unplayed_songs.remove(picked)
        for user in self.users:
            self.user_scores[user] += self.get_rating_score(
                user.get_rating_for_song(picked)
            )
        return picked
