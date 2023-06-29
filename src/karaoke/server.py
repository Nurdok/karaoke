import datetime
import json

from flask import Flask, render_template, jsonify, request, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from karaoke.core.session import KaraokeSession
from karaoke.core.user import User
from karaoke.core.song import Song
from karaoke.core.utils import get_any_unrated_song
from karaoke.core.rating import UserSongRating, Rating
from typing import Optional
import logging

LOCAL_DB = "sqlite:///karaoke.sqlite"

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def index() -> str:
    session_id: str = request.args.get("s", "")
    return render_template("player.html", session_id=session_id)


@app.route("/next_video")
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


@app.route("/next-unrated-song")
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


@app.route("/rate-song", methods=["POST"])
def rate_song() -> Response:
    data: dict[str, str] = json.loads(request.data.decode("utf-8"))
    print(data)
    user_id: int = int(data.get("userId", -1))
    song_id: int = int(data.get("songId", -1))
    rating: str = data.get("rating", "")
    if user_id == -1 or song_id == -1 or rating == "":
        return Response(status=400)

    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        user_rating: UserSongRating = UserSongRating(
            user_id=user_id,
            song_id=song_id,
            rating=Rating[rating],
        )
        session.add(user_rating)
        session.commit()

    return Response(status=200)


@app.route("/rate")
def rate() -> Response | str:
    user_id: int = int(request.args.get("u", -1))
    if user_id == -1:
        return Response(status=400)

    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        user: Optional[User] = (
            session.query(User).filter_by(id=user_id).first()
        )

    if user is None:
        return Response(status=404)
    return render_template("rate.html", user=user)


if __name__ == "__main__":
    app.run()
