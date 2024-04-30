from dataclasses import dataclass
import json

import typing
from flask import Flask, render_template, jsonify, request, Response, redirect
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from karaoke.core.session import KaraokeSession, KaraokeSessionUser
from karaoke.core.user import User
from karaoke.core.song import Song
from karaoke.core.utils import get_any_unrated_song, create_karaoke_session
from karaoke.core.rating import UserSongRating, Rating
from typing import Optional, Any, Callable
import logging

if typing.TYPE_CHECKING:  # pragma: no cover
    from werkzeug.wrappers import Response as BaseResponse

LOCAL_DB = "sqlite:///karaoke.sqlite"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.WARN,
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def with_db_session(f: Callable) -> Callable:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        engine = create_engine(LOCAL_DB)
        with sessionmaker(bind=engine)() as session:
            return f(*args, **kwargs, session=session)

    wrapper.__name__ = f.__name__
    return wrapper


@dataclass
class RequestDbData:
    karaoke_session: Optional[KaraokeSession] = None
    user: Optional[User] = None
    song: Optional[Song] = None

    @classmethod
    def from_post_data(
        cls, data: dict[str, str], session: Session
    ) -> "RequestDbData":
        print(data)
        return cls(
            karaoke_session=cls.get_karaoke_session(
                data, "sessionId", session
            ),
            user=cls.get_user(data, "userId", session),
            song=cls.get_song(data, "songId", session),
        )

    @classmethod
    def from_url_params(
        cls, data: dict[str, str], session: Session
    ) -> "RequestDbData":
        return cls(
            karaoke_session=cls.get_karaoke_session(data, "s", session),
            user=cls.get_user(data, "u", session),
        )

    @staticmethod
    def get_karaoke_session(
        data: dict[str, str], key: str, session: Session
    ) -> Optional[KaraokeSession]:
        session_id: str = data.get(key, "")
        if session_id == "":
            return None

        return (
            session.query(KaraokeSession)
            .filter_by(display_id=session_id)
            .first()
        )

    @staticmethod
    def get_user(
        data: dict[str, str], key: str, session: Session
    ) -> Optional[User]:
        user_id: int = int(data.get(key, -1))
        if user_id == -1:
            return None

        return session.query(User).filter_by(id=user_id).first()

    @staticmethod
    def get_song(
        data: dict[str, str], key: str, session: Session
    ) -> Optional[Song]:
        song_id: int = int(data.get(key, -1))
        if song_id == -1:
            return None

        return session.query(Song).filter_by(id=song_id).first()


@app.route("/")
def main() -> str:
    return render_template("index.html")


@app.route("/users")
@with_db_session
def list_users(session: Session) -> str:
    users = session.query(User).all()
    return render_template("users.html", users=users)


@app.route("/users", methods=["POST"])
@with_db_session
def create_user(session: Session) -> "BaseResponse":
    user = User(name=request.form["name"])
    session.add(user)
    session.commit()
    return redirect("/users")


@app.route("/api/create-session", methods=["POST"])
@with_db_session
def create_session(session: Session) -> Response | str:
    data = json.loads(request.data)
    user_ids = data["user_ids"]
    karaoke_session = create_karaoke_session(user_ids, session)
    return jsonify({"session_id": karaoke_session.display_id})


@app.route("/generate-static-playlist", methods=["POST"])
@with_db_session
def generate_static_playlist(session: Session) -> Response | str:
    user_ids = json.loads(request.form.get("user_ids", "[]"))
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
                    .get(song.id, Rating.UNKNOWN)
                    .value
                    for user in users
                },
            }
        )

    return render_template(
        "playlist.html", songs=songs_with_stats, users=users
    )


@app.route("/songs")
@with_db_session
def list_songs(session: Session) -> Response | str:
    data = RequestDbData.from_url_params(request.args, session=session)
    if (user := data.user) is None:
        return Response(status=400)

    songs_with_ratings: list[dict[str, Any]] = []
    songs: list[Song] = session.query(Song).all()
    for song in songs:
        user_rating: Optional[UserSongRating] = (
            session.query(UserSongRating)
            .filter_by(user_id=user.id, song_id=song.id)
            .first()
        )
        songs_with_ratings.append(
            {
                "id": song.id,
                "title": song.title,
                "artist": song.artist,
                "video_link": song.get_video_link(embed_yt_videos=False),
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


def no_more_songs() -> str:
    return json.dumps(
        {
            "id": -1,
            "status": "NO_MORE_SONGS",
            "title": "No more songs in queue",
        }
    )


def no_song_playing() -> str:
    return json.dumps(
        {
            "id": -1,
            "status": "NO_SONG_IS_CURRENTLY_PLAYING",
            "title": "No song playing",
        }
    )


def jsonify_song(song: Song, embed_yt_videos: bool) -> str:
    ratings = [
        {
            "user_id": rating.user_id,
            "user_name": rating.user.name,
            "rating": rating.rating,
        }
        for rating in song.ratings
    ]
    return json.dumps(
        {
            "status": "OK",
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "video_link": song.get_video_link(embed_yt_videos=embed_yt_videos),
            "ratings": ratings,
        }
    )


@app.route("/api/get-current-song")
@with_db_session
def get_current_song(session: Session) -> str:
    data = RequestDbData.from_url_params(request.args, session=session)
    if (karaoke_session := data.karaoke_session) is None:
        return Response(status=400)

    if (
        current_song := karaoke_session.get_current_song(session=session)
    ) is None:
        return no_song_playing()

    return jsonify_song(current_song.song, embed_yt_videos=False)


@app.route("/api/get-current-scores")
@with_db_session
def get_current_scores(session: Session) -> str:
    data = RequestDbData.from_url_params(request.args, session=session)
    if (karaoke_session := data.karaoke_session) is None:
        return Response(status=400)

    scores: list[dict[str, Any]] = []
    for user in karaoke_session.users:
        scores.append(
            {
                "user_id": user.user_id,
                "user_name": user.user.name,
                "user_stepped_out": user.stepped_out,
                "score": user.score,
            }
        )

    return json.dumps(scores)


@app.route("/api/mark-as-played-and-get-next")
def mark_as_played_and_get_next() -> str:
    def mark_song(
        karaoke_session: KaraokeSession, *, session: Session
    ) -> None:
        karaoke_session.mark_current_song_as_played(session=session)

    return next_video(mark_song, embed_yt_videos=True)


@app.route("/next")
def mark_as_played_and_redirect_to_next() -> str | Response:
    def mark_song(
        karaoke_session: KaraokeSession, *, session: Session
    ) -> None:
        karaoke_session.mark_current_song_as_played(session=session)

    next_video(mark_song, embed_yt_videos=False)
    session_id: str = request.args.get("s", "")
    return render_template("splash.html", session_id=session_id)


@app.route("/api/snooze-and-get-next")
def snooze_and_get_next() -> str:
    def mark_song(
        karaoke_session: KaraokeSession, *, session: Session
    ) -> None:
        karaoke_session.snooze_current_song(session=session)

    return next_video(mark_song, embed_yt_videos=True)


@app.route("/snooze")
def snooze() -> "BaseResponse":
    def mark_song(
        karaoke_session: KaraokeSession, *, session: Session
    ) -> None:
        karaoke_session.snooze_current_song(session=session)

    return redirect(
        json.loads(next_video(mark_song, embed_yt_videos=False)).get(
            "video_link"
        )
    )


@app.route("/api/skip-and-get-next")
def skip_and_get_next() -> str:
    def mark_song(
        karaoke_session: KaraokeSession, *, session: Session
    ) -> None:
        karaoke_session.skip_current_song(session=session)

    embed: bool = request.args.get("embed", True)
    if embed in (0, "0", "false", "False"):
        embed = False
    return next_video(mark_song, embed_yt_videos=embed)


@app.route("/skip")
def skip() -> "BaseResponse":
    def mark_song(
        karaoke_session: KaraokeSession, *, session: Session
    ) -> None:
        karaoke_session.skip_current_song(session=session)

    return redirect(
        json.loads(next_video(mark_song, embed_yt_videos=False)).get(
            "video_link"
        )
    )


@with_db_session
def next_video(
    mark_song: Callable, embed_yt_videos: bool, session: Session
) -> str:
    data = RequestDbData.from_url_params(request.args, session=session)
    if (karaoke_session := data.karaoke_session) is None:
        return Response(status=400)

    mark_song(karaoke_session, session=session)
    session.commit()
    song: Optional[Song] = karaoke_session.get_next_song(session=session)
    session.commit()
    if song is None:
        return no_more_songs()

    return jsonify_song(song, embed_yt_videos=embed_yt_videos)


@app.route("/api/next-unrated-song")
@with_db_session
def next_unrated_song(session: Session) -> Response:
    data = RequestDbData.from_url_params(request.args, session=session)
    if (user := data.user) is None:
        return Response(status=400)

    song: Optional[Song] = get_any_unrated_song(
        user_id=user.id, session=session
    )

    if song is None:
        return jsonify({"song_id": -1})

    return jsonify(
        {
            "song_id": song.id,
            "song_title": song.title,
            "song_artist": song.artist,
            "video_link": song.get_video_link(embed_yt_videos=True),
        }
    )


@with_db_session
def set_step_out(
    data: dict[str, str], step_out: bool, session: Session
) -> Response:
    data = RequestDbData.from_post_data(data, session=session)

    if (karaoke_session := data.karaoke_session) is None:
        return Response(status=400)

    if (user := data.user) is None:
        return Response(status=400)

    user: Optional[KaraokeSessionUser] = (
        session.query(KaraokeSessionUser)
        .filter_by(user_id=user.id)
        .filter_by(karaoke_session_id=karaoke_session.id)
        .first()
    )
    if user is None:
        return Response(status=400)

    user.stepped_out = step_out
    session.commit()
    return Response(status=200)


@app.route("/api/step-out", methods=["POST"])
def step_out() -> Response:
    data: dict[str, str] = json.loads(request.data.decode("utf-8"))
    return set_step_out(data, True)


@app.route("/api/step-back", methods=["POST"])
def step_back() -> Response:
    data: dict[str, str] = json.loads(request.data.decode("utf-8"))
    return set_step_out(data, False)


@app.route("/api/join-session", methods=["POST"])
@with_db_session
def join_session(session: Session) -> Response:
    data = RequestDbData.from_post_data(
        json.loads(request.data.decode("utf-8")), session=session
    )

    if (karaoke_session := data.karaoke_session) is None:
        return Response(status=400)

    if (user := data.user) is None:
        return Response(status=400)

    karaoke_session.add_user_to_session(user_id=user.id, session=session)
    return Response(status=200)


@app.route("/api/leave-session", methods=["POST"])
@with_db_session
def leave_session(session: Session) -> Response:
    data = RequestDbData.from_post_data(
        json.loads(request.data.decode("utf-8")), session=session
    )

    if (karaoke_session := data.karaoke_session) is None:
        return Response(status=400)

    if (user := data.user) is None:
        return Response(status=400)

    karaoke_session.remove_user_from_session(user_id=user.id, session=session)
    return Response(status=200)


@app.route("/api/rate-song", methods=["POST"])
@with_db_session
def rate_song(session: Session) -> Response:
    raw_data: dict[str, str] = json.loads(request.data.decode("utf-8"))
    data = RequestDbData.from_post_data(raw_data, session=session)
    if (user := data.user) is None or (song := data.song) is None:
        return Response(status=400)

    rating_str: str = raw_data.get("rating", "")
    rating: Rating = Rating[rating_str]

    # Delete any existing rating
    user.rate_song(song, rating, session=session)
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


@app.route("/api/edit-song", methods=["POST"])
def edit_song_api() -> Response:
    data: dict[str, str] = json.loads(request.data.decode("utf-8"))
    song_id: int = int(data.get("song_id", -1))
    artist: Optional[str] = data.get("artist", None)
    title: Optional[str] = data.get("title", None)
    video_link: Optional[str] = data.get("video_link", None)

    print(f"Editing song: {song_id} - {artist} - {title} - {video_link}")

    if None in (artist, title, video_link):
        return Response(status=400)

    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        song: Optional[Song] = (
            session.query(Song).filter_by(id=song_id).first()
        )
        if song is None:
            return Response(status=400)

        song.artist = artist
        song.title = title
        song.video_link = video_link
        session.commit()

    return Response(status=200)


@app.route("/api/delete-song", methods=["POST"])
def delete_song_api() -> Response:
    data: dict[str, str] = json.loads(request.data.decode("utf-8"))
    song_id: int = int(data.get("song_id", -1))

    print(f"Deleting song: {song_id}")

    if song_id == -1:
        return Response(status=400)

    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        session.delete(session.query(Song).filter_by(id=song_id).first())
        session.commit()

    return Response(status=200)


@app.route("/start-session")
def start_session() -> Response | str:
    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        users = session.query(User).all()
    return render_template("start-session.html", users=users)


@app.route("/companion")
def companion() -> Response | str:
    session_id: str = request.args.get("s", "")
    return render_template("companion.html", session_id=session_id)


@app.route("/reset-ratings")
def reset_ratings() -> Response | str:
    user_id: int = int(request.args.get("u", -1))
    if user_id == -1:
        return Response(status=400)

    engine = create_engine(LOCAL_DB)
    with sessionmaker(bind=engine)() as session:
        session.query(UserSongRating).filter_by(user_id=user_id).delete()
        session.commit()

    return redirect("/rate")


def start_server() -> None:
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    start_server()
