from dataclasses import dataclass
from enum import Enum
import random
from typing import Optional, cast, Collection
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
        self._title: str = ""
        self._artist: str = ""
        self._video_link: str = ""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Song):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def create(cls, title: str, artist: str, video_link: str) -> "Song":
        all_songs = cls.get_all_songs()
        for song in all_songs:
            if song.title == title and song.artist == artist:
                logger.info("Song already exists, returning existing song.")
                return song

        self: Song = cls()
        self.id = cls.generate_id()
        self._title = title
        self._artist = artist
        self._video_link = video_link

        redis_api.hset(
            self.get_song_redis_key(self.id),
            mapping={
                "title": title,
                "artist": artist,
                "video_link": video_link,
            },
        )
        logger.info(f"Created song {self.id}: {self.title}")
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
    def get_song_redis_key(cls, song_id: int) -> str:
        return f"song:id={song_id}"

    @classmethod
    def find_by_id(cls, song_id: int) -> "Song":
        self = Song()
        self.id = song_id
        song_data: dict[bytes, bytes] = redis_api.hgetall(
            cls.get_song_redis_key(song_id)
        )

        if not song_data:
            raise KeyError(f"Song {song_id} not found.")

        logger.info(f"Found song {song_id}: {song_data}")

        def decode(b: bytes) -> str:
            return b.decode("utf-8")

        self._title = decode(song_data[b"title"])
        self._artist = decode(song_data[b"artist"])
        self._video_link = decode(song_data[b"video_link"])
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

    @property
    def title(self) -> str:
        return self._title

    @property
    def artist(self) -> str:
        return self._artist

    @property
    def video_link(self) -> str:
        return self._video_link

    def get_score(self, session: "Session") -> int:
        score = 0
        for user in session.users:
            for rating in user.song_ratings:
                user.get_rating_for_song(self.id)
                score += session.get_rating_score(rating.rating)
        return score


def format_song_list(songs: Collection[Song]) -> str:
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
        for song_id in redis_api.smembers(f"user:{user_id}:song:rated"):
            song_id = int(song_id)
            raw_rating = redis_api.get(f"user:{user_id}:song:{song_id}:rating")
            if raw_rating is None:
                raise RuntimeError(
                    f"User {user_id} rated song {song_id} but rating not found."
                )
            self.song_ratings.append(
                UserSongRating(
                    song_id=song_id,
                    rating=Rating(int(raw_rating)),
                    will_sing_alone=False,
                    avoid_early=False,
                )
            )
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

    def get_rated_song_ids(self) -> list[int]:
        return [rating.song_id for rating in self.song_ratings]

    def get_any_unrated_song(self) -> Optional[Song]:
        song_count = Song.get_song_counter()
        if song_count > len(self.get_rated_song_ids()):
            for song_id in range(1, Song.get_song_counter() + 1):
                if song_id not in self.get_rated_song_ids():
                    return Song.find_by_id(song_id)
        else:
            return None

        raise RuntimeError("No unrated songs left, but counters don't match.")

    def get_rating_for_song(self, song_id: int) -> Rating:
        for rating in self.song_ratings:
            if rating.song_id == song_id:
                return rating.rating
        return Rating.DONT_KNOW

    def rate_song(self, song_id: int, rating: Rating) -> None:
        redis_api.set(f"user:{self.id}:song:{song_id}:rating", rating.value)
        redis_api.sadd(f"user:{self.id}:song:rated", song_id)
        # redis_api.set(f"user:{self.id}:song:{song.id}:will_sing_alone", False)
        # redis_api.set(f"user:{self.id}:song:{song.id}:avoid_early", False)

        for user_rating in self.song_ratings:
            if user_rating.song_id == song_id:
                user_rating.rating = rating
                return

        self.song_ratings.append(
            UserSongRating(
                song_id=song_id,
                rating=rating,
                will_sing_alone=False,
                avoid_early=False,
            )
        )


@dataclass
class UserSongRating:
    song_id: int
    rating: Rating
    will_sing_alone: bool
    avoid_early: bool


class Session:
    def __init__(self) -> None:
        self.id: str = ""
        self.users: list[User] = []
        self.unplayed_song_ids: set[int] = set()
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
        self.unplayed_song_ids = self.get_all_song_ids()
        for song_id in self.unplayed_song_ids:
            redis_api.sadd(f"session:id={self.id}:unplayed_songs", song_id)
        self.user_scores = {user: 0 for user in users}
        for user in users:
            redis_api.set(f"session:id={self.id}:user_scores:{user.id}", 0)

    @classmethod
    def find_by_id(cls, session_id: str) -> "Session":
        self: Session = cls()
        self.id = session_id
        self.users = [
            User.find_by_id(int(user_id))
            for user_id in redis_api.smembers(f"session:id={self.id}:users")
        ]
        self.unplayed_song_ids = cast(
            set[int],
            redis_api.smembers(f"session:id={self.id}:unplayed_songs"),
        )
        self.user_scores = {
            user: int(
                cast(
                    str,
                    redis_api.get(
                        f"session:id={self.id}:user_scores:{user.id}"
                    ),
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

    def get_all_song_ids(self) -> set[int]:
        all_song_ids: set[int] = set()
        for user in self.users:
            all_song_ids.update(user.get_rated_song_ids())
        return all_song_ids

    def get_combined_score(self, song_id: int) -> int:
        score = 0
        for user in self.users:
            score += self.get_rating_score(user.get_rating_for_song(song_id))
        return score

    def prune_candidates_for_user(
        self, candidates: set[int], user: User
    ) -> set[int]:
        logger.info(f"Pruning candidates for {user.name}")
        logger.info(f"{user.name} has {len(user.song_ratings)} ratings")
        pruned_candidates: set[int] = set()
        for rating in [
            Rating.NEED_THE_MIC,
            Rating.CAN_TAKE_THE_MIC,
            Rating.SING_ALONG,
        ]:
            logger.info(f"Pruning for rating {rating}")
            for song_id in candidates:
                logger.info(f"Checking song {song_id}")
                if user.get_rating_for_song(song_id) == rating:
                    logger.info(
                        f"{user.name} has rating {rating} for {song_id}"
                    )
                    pruned_candidates.add(song_id)

            if pruned_candidates:
                return pruned_candidates

        # This user wouldn't benefit from any of the candidates, so we'll
        # just return the original list
        logger.info(f"Pruning is not possible for {user.name}, not pruning.")
        return candidates

    def get_next_song(self) -> Optional[Song]:
        user_scores_str = ", ".join(
            [f"{u.name}: {s}" for u, s in self.user_scores.items()]
        )
        logger.info(f"Current user scores: {user_scores_str}")

        candidates = self.unplayed_song_ids
        sorted_users = sorted(self.users, key=lambda u: self.user_scores[u])
        for user in sorted_users:
            candidates = self.prune_candidates_for_user(candidates, user)
            if len(candidates) == 1:
                break
        logger.info(f"Found {len(candidates)} candidates.")

        if not candidates:
            return None

        sorted_candidates = list(candidates)
        sorted_candidates.sort(
            key=lambda s: self.get_combined_score(s), reverse=True
        )
        max_score = self.get_combined_score(sorted_candidates[0])
        sorted_candidates = [
            s
            for s in sorted_candidates
            if self.get_combined_score(s) == max_score
        ]
        picked: Song = Song.find_by_id(sorted_candidates[0])
        logger.info(f"Picked {picked.title}.")
        logger.info(f"Combined score: {self.get_combined_score(picked.id)}")
        self.unplayed_song_ids.remove(picked.id)
        redis_api.srem(f"session:id={self.id}:unplayed_songs", picked.id)
        for user in self.users:
            self.user_scores[user] += self.get_rating_score(
                user.get_rating_for_song(picked.id)
            )
        return picked
