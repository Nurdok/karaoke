from flask import Flask, render_template, jsonify, request
from karaoke.playlist import Session, Song
from typing import Optional

app = Flask(__name__)


@app.route("/")
def index() -> str:
    session_id: str = request.args.get("s", "")
    return render_template("player.html", session_id=session_id)


@app.route("/next_video")
def next_video() -> str:
    session_id: str = request.args.get("s", "")
    session: Session = Session.find_by_id(session_id)
    song: Optional[Song] = session.get_next_song()
    if song is None:
        return ""
    return song.video_link
    # return jsonify({'video_url': video_url})


if __name__ == "__main__":
    app.run()
