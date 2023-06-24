from flask import Flask, render_template, jsonify, request, Response
from karaoke.playlist import Session, Song, User, Rating
from typing import Optional
import logging

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
    session: Session = Session.find_by_id(session_id)
    logger.info(f"Session user scores: {session.user_scores}")
    song: Optional[Song] = session.get_next_song()
    if song is None:
        return "https://www.youtube.com/embed/T1XgFsitnQw"
    return song.video_link
    # return jsonify({'video_url': video_url})


@app.route("/next_song")
def next_song() -> Response:
    user_id: int = int(request.args.get("u", -1))
    if user_id == -1:
        return Response(status=400)
    user: User = User.find_by_id(user_id)
    songs: list[Song] = user.get_unrated_songs()
    if songs:
        song = songs[0]
        return jsonify(
            {
                "song_id": song.id,
                "song_title": song.title,
                "song_artist": song.artist,
            }
        )

    return Response(status=404)


@app.route("/rate_song", methods=["POST"])
def rate_song() -> Response:
    user_id: int = int(request.form.get("u", -1))
    song_id: int = int(request.form.get("s", -1))
    rating: str = request.form.get("r", "")
    if user_id == -1 or song_id == -1 or rating == "":
        return Response(status=400)
    user: User = User.find_by_id(user_id)
    song: Song = Song.find_by_id(song_id)
    user.rate_song(song, Rating[rating])
    return Response(status=200)


@app.route("/rate")
def rate() -> str:
    user_id: int = int(request.form.get("u", -1))
    return render_template("rate.html", user_id=user_id)


if __name__ == "__main__":
    app.run()
