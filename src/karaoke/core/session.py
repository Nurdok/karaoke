from sqlalchemy import (
    ForeignKey,
    String,
    select,
    func,
    text,
    case,
)
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session
import random
import logging

from karaoke.core.base import Base
from karaoke.core.rating import UserSongRating, Rating
from karaoke.core.song import Song
from karaoke.core.user import User

logger = logging.getLogger(__name__)

# Number of songs to hold off when snoozing a song.
SNOOZE_TTL = 5

from time import perf_counter
from time import sleep
from contextlib import contextmanager

@contextmanager
def catchtime() -> float:
    t1 = t2 = perf_counter()
    yield lambda: t2 - t1
    t2 = perf_counter()

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
    stepped_out: Mapped[bool] = mapped_column(default=False)

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
    current_song: Mapped[bool] = mapped_column(default=False)
    snooze_ttl: Mapped[int] = mapped_column(default=0)


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

        songs_ids_query = (
            select(
                UserSongRating.song_id,
                func.count("*").label("know_this_song_count"),
                func.count(
                    case(
                        (UserSongRating.rating == Rating.CAN_TAKE_THE_MIC, 1),
                        (UserSongRating.rating == Rating.NEED_THE_MIC, 1),
                        else_=None,
                    )
                ).label("can_take_the_mic_count"),
            )
            .select_from(UserSongRating)
            .where(UserSongRating.user_id.in_(user_ids))
            .where(UserSongRating.rating != Rating.DONT_KNOW)
            .group_by(UserSongRating.song_id)
            .having(
                text("know_this_song_count > 1")
            )  # At least 2 people know it
            .having(
                text("can_take_the_mic_count > 0")
            )  # At least 1 person can sing it
            .subquery()
        )

        logger.info(f"{session.query(songs_ids_query).all()=}")
        song_ids = (row[0] for row in session.query(songs_ids_query).all())

        for song_id in song_ids:
            kss = KaraokeSessionSong(
                karaoke_session_id=self.id, song_id=song_id, played=False
            )
            self.songs.append(kss)
            session.add(kss)

        session.commit()
        self.snooze_top_songs(10)
        self.snooze_obscure_songs(know_count_threshold=len(user_ids) // 2)
        session.commit()

    def snooze_top_songs(self, n):
        """Snooze the top `n` songs for a more balanced session."""
        sorted_candidates = list(self.songs)
        sorted_candidates.sort(
            key=lambda s: self.get_combined_score(s), reverse=True
        )
        for index, song in enumerate(reversed(sorted_candidates[:n])):
            song.snooze_ttl = random.randrange(5, 20 - index)

    def snooze_obscure_songs(self, know_count_threshold):
        """Snooze songs that only a few people know."""

        for song in self.songs:
            know_count = 0
            for rating in song.song.ratings:
                if rating.rating not in (Rating.DONT_KNOW, Rating.UNKNOWN):
                    know_count += 1
            if know_count < know_count_threshold:
                song.snooze_ttl = random.randrange(10, 20)

    def get_played_songs_count(self):
        return len([song for song in self.songs if song.played])

    def prune_candidates_for_user(
        self,
        candidates: list[KaraokeSessionSong],
        user: KaraokeSessionUser,
    ) -> list[KaraokeSessionSong]:
        logger.info(
            f"Pruning {len(candidates)} candidates for {user.user.name}"
        )
        logger.info(f"\t{user.user.name} has {len(user.user.ratings)} ratings")
        pruned_candidates: list[KaraokeSessionSong] = []
        user_ratings = {
            song_rating.song.id: song_rating.rating
            for song_rating in user.user.ratings
        }
        rating_order = [
            Rating.NEED_THE_MIC,
            Rating.CAN_TAKE_THE_MIC,
            Rating.SING_ALONG,
            Rating.DONT_KNOW,
        ]
        # For users who stepped out, we want to choose songs they don't know.
        if user.stepped_out:
            rating_order.reverse()

        for rating in rating_order:
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
            f"\t{user.user.name} doesn't know any of the candidates, not pruning."
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

    def mark_current_song_as_played(self, *, session: Session) -> None:
        if (current_song := self.get_current_song(session=session)) is None:
            return
        current_song.played = True
        current_song.current_song = False

        # Update user scores.
        song_ratings: dict[User, Rating] = {
            rating.user: rating.rating for rating in current_song.song.ratings
        }

        for user in self.users:
            user.score += self.get_rating_score(
                song_ratings.get(user.user, Rating.DONT_KNOW)
            )

        # Decrement snooze TTL by 1 for all snoozed songs.
        snoozed_songs = (
            session.query(KaraokeSessionSong)
            .filter(KaraokeSessionSong.snooze_ttl > 0)
            .all()
        )

        for snoozed_song in snoozed_songs:
            snoozed_song.snooze_ttl -= 1

        session.commit()

    def get_current_song(
        self, *, session: Session
    ) -> Optional[KaraokeSessionSong]:
        current_song = (
            session.query(KaraokeSessionSong)
            .filter(KaraokeSessionSong.karaoke_session_id == self.id)
            .filter(KaraokeSessionSong.current_song == True)
            .one_or_none()
        )
        return current_song

    def skip_current_song(self, session: Session) -> None:
        if (current_song := self.get_current_song(session=session)) is None:
            return
        current_song.played = True
        current_song.current_song = False
        session.commit()

    def snooze_current_song(self, *, session: Session) -> None:
        if (current_song := self.get_current_song(session=session)) is None:
            return
        current_song.current_song = False
        current_song.snooze_ttl = SNOOZE_TTL
        session.commit()

    def get_next_song(self, *, session: Session) -> Optional[Song]:
        if self.get_current_song(session=session) is not None:
            logger.info(f"Current song is still playing.")
            return None

        candidates: list[KaraokeSessionSong] = [
            song
            for song in self.songs
            if not song.played
            if not song.snooze_ttl
        ]

        stepped_out_users: list[KaraokeSessionUser] = []
        present_users: list[KaraokeSessionUser] = []

        for user in self.users:
            if user.stepped_out:
                stepped_out_users.append(user)
            else:
                present_users.append(user)

        # Shuffle the present users before sorting so that we don't always pick
        # the user with the lowest ID in the case of a tie (`sorted` is
        # stable).
        random.shuffle(present_users)
        sorted_present_users: list[KaraokeSessionUser] = sorted(
            present_users, key=lambda user: user.score
        )

        sorted_users = stepped_out_users + sorted_present_users

        logger.info(
            f"Getting next song from {len(candidates)} remaining unplayed songs"
        )

        if not candidates:
            return None

        for user in sorted_users:
            candidates = self.prune_candidates_for_user(candidates, user)
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
        logger.warn(f"Picked song from {len(sorted_candidates)} candidates")
        logger.info(f"Picked {picked.song.title}.")
        logger.info(f"Combined score: {self.get_combined_score(picked)}")
        picked.current_song = True
        session.commit()
        return picked.song
