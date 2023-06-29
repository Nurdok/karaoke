from sqlalchemy import ForeignKey, String, select
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session
from enum import Enum
import random
import logging

from karaoke.core.base import Base
from karaoke.core.rating import UserSongRating, Rating
from karaoke.core.song import Song
from karaoke.core.user import User

logger = logging.getLogger(__name__)


class KaraokeSessionUser(Base):
    __tablename__ = "karaoke_session_user"

    karaoke_session_id: Mapped[str] = mapped_column(
        ForeignKey("karaoke_session.id"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user_account.id"), primary_key=True
    )
    user: Mapped[User] = relationship()
    score: Mapped[int] = mapped_column(default=0)

    def __repr__(self) -> str:
        return f"KaraokeSessionUser(karaoke_session_id={self.karaoke_session_id}, user_id={self.user_id}, score={self.score})"


class KaraokeSessionSong(Base):
    __tablename__ = "karaoke_session_song"

    karaoke_session_id: Mapped[str] = mapped_column(
        ForeignKey("karaoke_session.id"), primary_key=True
    )
    song_id: Mapped[int] = mapped_column(
        ForeignKey("song.id"), primary_key=True
    )
    song: Mapped[Song] = relationship()
    played: Mapped[bool] = mapped_column()


def generate_id() -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(random.choices(letters, k=4))


class KaraokeSession(Base):
    __tablename__ = "karaoke_session"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_id: Mapped[str] = mapped_column(
        String(4), nullable=True, unique=True
    )
    users: Mapped[list[KaraokeSessionUser]] = relationship()
    songs: Mapped[list[KaraokeSessionSong]] = relationship()

    def generate_display_id(self, session: Session) -> None:
        display_id = generate_id()
        all_sessions = session.query(KaraokeSession).all()
        all_display_ids = [ks.display_id for ks in all_sessions]
        while display_id in all_display_ids:
            display_id = generate_id()
        self.display_id = display_id

    def generate_song_queue(self, session: Session) -> None:
        user_ids = [user.user_id for user in self.users]

        songs = (
            session.query(Song)
            .where(
                Song.id.in_(
                    select(UserSongRating.song_id)
                    .select_from(UserSongRating)
                    .where(UserSongRating.user_id.in_(user_ids))
                )
            )
            .all()
        )

        for song in songs:
            kss = KaraokeSessionSong(
                karaoke_session_id=self.id, song_id=song.id, played=False
            )
            self.songs.append(kss)
            session.add(kss)

        session.commit()

    def prune_candidates_for_user(
        self, candidates: list[KaraokeSessionSong], user: User
    ) -> list[KaraokeSessionSong]:
        logger.info(f"Pruning {len(candidates)} candidates for {user.name}")
        logger.info(f"\t{user.name} has {len(user.ratings)} ratings")
        pruned_candidates: list[KaraokeSessionSong] = []
        user_ratings = {
            song_rating.song.id: song_rating.rating
            for song_rating in user.ratings
        }
        for rating in [
            Rating.NEED_THE_MIC,
            Rating.CAN_TAKE_THE_MIC,
            Rating.SING_ALONG,
        ]:
            logger.info(f"\tSearching for rating {rating}")
            for song in candidates:
                if user_ratings.get(song.song.id, Rating.DONT_KNOW) == rating:
                    logger.info(
                        f"\t\tMatched: {song.song.title} by {song.song.artist}"
                    )
                    pruned_candidates.append(song)

            if pruned_candidates:
                if len(pruned_candidates) == len(candidates):
                    logger.info(f"\tAll songs matched, not pruning.")
                return pruned_candidates
            else:
                logger.info(f"\t\tNo songs found with rating {rating}")

        # This user wouldn't benefit from any of the candidates, so we'll
        # just return the original list
        logger.info(
            f"\t{user.name} doesn't know any of the candidates, not pruning."
        )
        return candidates

    def get_rating_score(self, rating: Rating) -> int:
        return {
            Rating.DONT_KNOW: -1,
            Rating.SING_ALONG: 1,
            Rating.CAN_TAKE_THE_MIC: 2,
            Rating.NEED_THE_MIC: 5,
        }[rating]

    def get_combined_score(self, song: KaraokeSessionSong) -> int:
        score = 0
        for user in self.users:
            score += self.get_rating_score(
                {
                    rating.user: rating.rating for rating in song.song.ratings
                }.get(user.user, Rating.DONT_KNOW)
            )
        return score

    def get_next_song(self, session: Session) -> Optional[Song]:
        candidates: list[KaraokeSessionSong] = [
            song for song in self.songs if not song.played
        ]
        sorted_users: list[KaraokeSessionUser] = sorted(
            self.users, key=lambda user: user.score
        )

        logger.info(
            f"Getting next song from {len(candidates)} remaining unplayed songs"
        )

        if not candidates:
            return None

        for user in sorted_users:
            candidates = self.prune_candidates_for_user(candidates, user.user)
            if len(candidates) == 1:
                logger.info(f"Left with one candidate, stopping.")
                break
        else:
            logger.info(f"Pruned for all users, Found {len(candidates)}")

        if not candidates:
            raise RuntimeError("This should never happen")

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
        picked: KaraokeSessionSong = sorted_candidates[0]
        logger.info(f"Picked {picked.song.title}.")
        logger.info(f"Combined score: {self.get_combined_score(picked)}")
        picked.played = True

        song_ratings: dict[User, Rating] = {
            rating.user: rating.rating for rating in picked.song.ratings
        }

        for user in self.users:
            user.score += self.get_rating_score(
                song_ratings.get(user.user, Rating.DONT_KNOW)
            )

        session.commit()
        return picked.song
