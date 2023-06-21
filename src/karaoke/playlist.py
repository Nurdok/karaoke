from dataclasses import dataclass
from enum import Enum
import random
from typing import Optional
import logging

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


@dataclass
class Song:
    id: int
    title: str
    artist: str
    video_link: str

    def get_score(self, session: "Session") -> int:
        score = 0
        for user in session.users:
            for rating in user.ratings:
                user.get_rating_for_song(self)
                score += session.get_rating_scores[rating.rating]
        return score


def format_song_list(songs: list[Song]) -> str:
    return ", ".join([f"{s.title}" for s in songs])


class User:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.song_ratings: list[UserSongRating] = []

    def __str__(self):
        return f"{self.name} ({self.id})"

    def get_rated_songs(self) -> list[Song]:
        return [rating.song for rating in self.song_ratings]

    def get_rating_for_song(self, song: Song) -> int:
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
    def __init__(self, users: list[User], id: Optional[str]):
        self.id = id
        self.users = users
        self.unplayed_songs = self.get_all_songs()
        self.user_scores = {user: 0 for user in users}

    @classmethod
    def create(cls, users: list[User]) -> "Session":
        return cls(users, cls.generate_id())

    @staticmethod
    def generate_id() -> int:
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        exists: bool = True
        while exists:
            new_id: str = "".join(random.choices(letters, k=4))
            exists = redis_api.exists(f"session:id={new_id}")
        return new_id

    def get_rating_scores(self) -> dict[Rating, int]:
        return {
            Rating.DONT_KNOW: -1,
            Rating.SING_ALONG: 1,
            Rating.CAN_TAKE_THE_MIC: 2,
            Rating.NEED_THE_MIC: 5,
        }

    def get_all_songs(self) -> list[Song]:
        all_songs: dict[int, Song] = {}
        for user in self.users:
            for song in user.get_rated_songs():
                all_songs[song.id] = song
        return list(all_songs.values())

    def get_combined_score(self, song: Song) -> int:
        score = 0
        for user in self.users:
            score += self.get_rating_scores()[user.get_rating_for_song(song)]
        return score

    def prune_candidates_for_user(self, candidates: list[Song], user: User) -> list[Song]:
        logger.info(f"Pruning candidates for {user.name}")
        pruned_candidates: list[Song] = []
        for rating in [Rating.NEED_THE_MIC, Rating.CAN_TAKE_THE_MIC, Rating.SING_ALONG]:
            if pruned_candidates:
                logger.info(f"Pruned candidates: {format_song_list(pruned_candidates)}")
                return pruned_candidates
            for song in candidates:
                if user.get_rating_for_song(song) == rating:
                    pruned_candidates.append(song)

        # This user wouldn't benefit from any of the candidates, so we'll
        # just return the original list
        logger.info(f"Pruning is not possible for {user.name}, not pruning.")
        return candidates

    def get_next_song(self) -> Optional[Song]:
        user_scores_str = ", ".join([f"{u.name}: {s}" for u, s in self.user_scores.items()])
        logger.info(f"Current user scores: {user_scores_str}")

        candidates = self.unplayed_songs
        sorted_users = sorted(self.users, key=lambda u: self.user_scores[u])
        for user in sorted_users:
            candidates = self.prune_candidates_for_user(candidates, user)
            if len(candidates) == 1:
                break
        logger.info(f"Found {len(candidates)} candidates: {format_song_list(candidates)}")

        if not candidates:
            return None

        candidates.sort(key=lambda s: self.get_combined_score(s), reverse=True)
        max_score = self.get_combined_score(candidates[0])
        candidates = [s for s in candidates if self.get_combined_score(s) == max_score]
        #picked: Song = random.choice(candidates)
        picked: Song = candidates[0]  # Not random for testing
        logger.info(f"Picked {picked.title}.")
        logger.info(f"Combined score: {self.get_combined_score(picked)}")
        self.unplayed_songs.remove(picked)
        for user in self.users:
            self.user_scores[user] += self.get_rating_scores()[user.get_rating_for_song(picked)]
        return picked

















