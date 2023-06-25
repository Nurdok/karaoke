import datetime
import json

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


@app.route("/next-unrated-song")
def next_unrated_song() -> Response:
    user_id: int = int(request.args.get("u", -1))
    if user_id == -1:
        return Response(status=400)
    user: User = User.find_by_id(user_id)
    start: datetime.datetime = datetime.datetime.now()
    song: Optional[Song] = user.get_any_unrated_song()
    end: datetime.datetime = datetime.datetime.now()
    print(f"Time to get next unrated song: {end - start}")
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
    user: User = User.find_by_id(user_id)
    song: Song = Song.find_by_id(song_id)
    user.rate_song(song.id, Rating[rating])
    return Response(status=200)


@app.route("/rate")
def rate() -> Response | str:
    user_id: int = int(request.args.get("u", -1))
    if user_id == -1:
        return Response(status=400)
    user: User = User.find_by_id(user_id)
    return render_template("rate.html", user=user)


if __name__ == "__main__":
    app.run()
