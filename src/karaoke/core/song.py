import logging

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String

from karaoke.core.base import Base
from typing import TYPE_CHECKING

import pytube
import pytube.extract

if TYPE_CHECKING:
    from karaoke.core.rating import UserSongRating


class Song(Base):
    __tablename__ = "song"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(100))
    artist: Mapped[str] = mapped_column(String(100))
    video_link: Mapped[str] = mapped_column(String(500))
    ratings: Mapped[list["UserSongRating"]] = relationship(
        back_populates="song",
        cascade="all, delete, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"Song(id={self.id}, "
            f"title={self.title}, "
            f"artist={self.artist}, "
            f"video_link={self.video_link})"
        )

    def get_video_link(self, embed_yt_videos: bool = False) -> str:
        return get_video_link(self.video_link, embed_yt_videos=embed_yt_videos)


def is_youtube_url(url: str) -> bool:
    return "youtube.com" in url or "youtu.be" in url


def is_http(url: str) -> bool:
    return "http" in url


def get_video_link(url: str, embed_yt_videos: bool = False) -> str:
    if (is_http(url) or "." in url) and not is_youtube_url(url):
        return url

    video_id: str = (
        pytube.extract.video_id(url) if is_youtube_url(url) else url
    )

    yt: pytube.YouTube = pytube.YouTube.from_id(video_id)
    return yt.embed_url if embed_yt_videos else yt.watch_url
