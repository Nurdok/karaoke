import datetime
import json

import typing
from flask import Flask, render_template, jsonify, request, Response, redirect
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from karaoke.core.session import KaraokeSession
from karaoke.core.user import User
from karaoke.core.song import Song
from karaoke.core.utils import get_any_unrated_song, create_karaoke_session
from karaoke.core.rating import UserSongRating, Rating
from typing import Optional, Any, Callable
import logging

if typing.TYPE_CHECKING:  # pragma: no cover
    from werkzeug.wrappers import Response as BaseResponse

LOCAL_DB = "sqlite:///karaoke.sqlite"

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/")
def main() -> str:
    return render_template("index.html")


@app.route("/users")
def list_users() -> str:
    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        users = session.query(User).all()
    return render_template("users.html", users=users)


@app.route("/users", methods=["POST"])
def create_user() -> "BaseResponse":
    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        user = User(name=request.form["name"])
        session.add(user)
        session.commit()
        return redirect("/users")


@app.route("/api/create-session", methods=["POST"])
def create_session() -> Response | str:
    data = json.loads(request.data)
    user_ids = data["user_ids"]
    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        karaoke_session = create_karaoke_session(user_ids, session)
        return jsonify({"session_id": karaoke_session.display_id})


@app.route("/generate-static-playlist", methods=["POST"])
def generate_static_playlist() -> Response | str:
    print(request.form)
    user_ids = json.loads(request.form.get("user_ids", "[]"))
    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        karaoke_session = create_karaoke_session(user_ids, session)
        users: list[User] = [
            session_user.user for session_user in karaoke_session.users
        ]
        user_ratings: dict[int, dict[int, Rating]] = {
            user.id: {
                song_rating.song.id: song_rating.rating
                for song_rating in user.ratings
            }
            for user in users
        }

        def get_next_song() -> Optional[Song]:
            next_song = karaoke_session.get_next_song(session=session)
            if next_song is not None:
                karaoke_session.mark_current_song_as_played(session=session)
            return next_song

        songs: list[Song] = [s for s in iter(get_next_song, None)]
        songs_with_stats: list[dict[str, Any]] = []
        for song in songs:
            songs_with_stats.append(
                {
                    "id": song.id,
                    "title": song.title,
                    "artist": song.artist,
                    "ratings": {
                        user.name: user_ratings[user.id]
                        .get(song.id, Rating.DONT_KNOW)
                        .name
                        for user in users
                    },
                }
            )

        return render_template(
            "playlist.html", songs=songs_with_stats, users=users
        )


@app.route("/songs")
def list_songs() -> Response | str:
    user_id: int = int(request.args.get("u", -1))
    if user_id == -1:
        return Response(status=400)

    songs_with_ratings: list[dict[str, Any]] = []
    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        user: Optional[User] = (
            session.query(User).filter_by(id=user_id).first()
        )
        if user is None:
            return Response(status=400)
        songs: list[Song] = session.query(Song).all()
        for song in songs:
            user_rating: Optional[UserSongRating] = (
                session.query(UserSongRating)
                .filter_by(user_id=user_id, song_id=song.id)
                .first()
            )
            songs_with_ratings.append(
                {
                    "id": song.id,
                    "title": song.title,
                    "artist": song.artist,
                    "rating": (
                        user_rating.rating.value
                        if user_rating is not None
                        else None
                    ),
                }
            )
    return render_template("songs.html", songs=songs_with_ratings, user=user)


@app.route("/player")
def index() -> str:
    session_id: str = request.args.get("s", "")
    return render_template("player.html", session_id=session_id)


def get_video_link(song: Optional[Song]) -> str:
    if song is None:
        return "https://www.youtube.com/embed/T1XgFsitnQw"

    if not song.video_link.startswith("http"):
        return f"https://www.youtube.com/embed/{song.video_link}"

    return song.video_link


@app.route("/api/get-current-song")
def get_current_song() -> str:
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

        if (
            current_song := karaoke_session.get_current_song(session=session)
        ) is None:
            return ""

        return get_video_link(current_song.song)


@app.route("/api/mark-as-played-and-get-next")
def mark_as_played_and_get_next() -> str:
    def mark_song(
        karaoke_session: KaraokeSession, *, session: Session
    ) -> None:
        karaoke_session.mark_current_song_as_played(session=session)

    return next_video(mark_song)


@app.route("/api/snooze-and-get-next")
def snooze_and_get_next() -> str:
    def mark_song(
        karaoke_session: KaraokeSession, *, session: Session
    ) -> None:
        karaoke_session.snooze_current_song(session=session)

    return next_video(mark_song)


@app.route("/api/skip-and-get-next")
def skip_and_get_next() -> str:
    def mark_song(
        karaoke_session: KaraokeSession, *, session: Session
    ) -> None:
        karaoke_session.skip_current_song(session=session)

    return next_video(mark_song)


def next_video(mark_song: Callable) -> str:
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

        mark_song(karaoke_session, session=session)
        song: Optional[Song] = karaoke_session.get_next_song(session=session)

        return get_video_link(song)


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
        return jsonify({"song_id": -1})

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


@app.route("/start-session")
def start_session() -> Response | str:
    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        users = session.query(User).all()
    return render_template("start-session.html", users=users)


def start_server() -> None:
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    start_server()
