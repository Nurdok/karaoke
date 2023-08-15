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
        back_populates="song"
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


def get_video_link(url, embed_yt_videos: bool = False) -> str:
    video_id: str

    if "http" not in url:
        # Assume this is a YouTube video ID
        video_id = url
    else:
        try:
            video_id = pytube.extract.video_id(url)
        except BaseException:
            # This is probably not a YouTube video, so just return the link
            return url

    yt: pytube.YouTube = pytube.YouTube.from_id(video_id)
    return yt.embed_url if embed_yt_videos else yt.watch_url
