import datetime
import json

from flask import Flask, render_template, jsonify, request, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from karaoke.core.session import KaraokeSession
from karaoke.core.user import User
from karaoke.core.song import Song
from karaoke.core.utils import get_any_unrated_song, create_karaoke_session
from karaoke.core.rating import UserSongRating, Rating
from typing import Optional
import logging

LOCAL_DB = "sqlite:///karaoke.sqlite"

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def main() -> str:
    return render_template("index.html")


@app.route("/users")
def users() -> str:
    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        users = session.query(User).all()
    return render_template("users.html", users=users)


@app.route("/api/create_session", methods=["POST"])
def create_session() -> Response:
    data = json.loads(request.data)
    user_ids = data["user_ids"]
    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        karaoke_session = create_karaoke_session(user_ids, session)
    return jsonify({"session_id": karaoke_session.id})


@app.route("/player")
def index() -> str:
    session_id: str = request.args.get("s", "")
    return render_template("player.html", session_id=session_id)


@app.route("/api/next_video")
def next_video() -> str:
    session_id: str = request.args.get("s", "")
    logger.info(f"Getting next video for session {session_id}")

    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        karaoke_session = (
            session.query(KaraokeSession)
            .filter_by(display_id=session_id)
            .first()
        )
        if karaoke_session is None:
            return ""

        song: Optional[Song] = karaoke_session.get_next_song(session)
        if song is None:
            return "https://www.youtube.com/embed/T1XgFsitnQw"

        if not song.video_link.startswith("http"):
            return f"https://www.youtube.com/embed/{song.video_link}"

        return song.video_link


@app.route("/api/next-unrated-song")
def next_unrated_song() -> Response:
    user_id: int = int(request.args.get("u", -1))
    if user_id == -1:
        return Response(status=400)

    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        song: Optional[Song] = get_any_unrated_song(
            user_id=user_id, session=session
        )

    if song is None:
        return Response(status=404)

    return jsonify(
        {
            "song_id": song.id,
            "song_title": song.title,
            "song_artist": song.artist,
        }
    )


@app.route("/api/rate-song", methods=["POST"])
def rate_song() -> Response:
    data: dict[str, str] = json.loads(request.data.decode("utf-8"))
    user_id: int = int(data.get("userId", -1))
    song_id: int = int(data.get("songId", -1))
    rating_str: str = data.get("rating", "")
    if user_id == -1 or song_id == -1 or rating_str == "":
        return Response(status=400)

    rating: Rating = Rating[rating_str]
    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        if rating == Rating.UNKNOWN:
            session.query(UserSongRating).filter_by(
                user_id=user_id, song_id=song_id
            ).delete()
        else:
            user_rating: UserSongRating = UserSongRating(
                user_id=user_id,
                song_id=song_id,
                rating=rating,
            )
            session.add(user_rating)
        session.commit()
    return Response(status=200)


@app.route("/rate")
def rate() -> Response | str:
    return render_template("rate.html")


@app.route("/add-song")
def add_song() -> Response | str:
    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        artists = [
            result[0] for result in session.query(Song.artist).distinct().all()
        ]

    return render_template("add-song.html", artists=artists)


@app.route("/api/add-song", methods=["POST"])
def add_song_api() -> Response:
    data: dict[str, str] = json.loads(request.data.decode("utf-8"))
    artist: Optional[str] = data.get("artist", None)
    title: Optional[str] = data.get("title", None)
    video_link: Optional[str] = data.get("video_link", None)

    print(f"Adding song: {artist} - {title} - {video_link}")

    if None in (artist, title, video_link):
        return Response(status=400)

    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        song: Song = Song(
            artist=artist,
            title=title,
            video_link=video_link,
        )
        session.add(song)
        session.commit()

    return Response(status=200)


if __name__ == "__main__":
    app.run(host="0.0.0.0")
