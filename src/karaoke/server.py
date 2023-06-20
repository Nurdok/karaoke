from flask import Flask, render_template, jsonify, request
import random

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('player.html')

@app.route('/next_video')
def next_video():
    # Perform any necessary logic to determine the next video URL
    youtube_urls = [
        'https://www.youtube.com/embed/9bZkp7q19f0',
        'https://www.youtube.com/embed/RubBzkZzpUA',
        'https://www.youtube.com/embed/9bZkp7q19f0',
        'https://www.youtube.com/embed/9bZkp7q19f0',
        'https://www.youtube.com/embed/RubBzkZzpUA',
        'https://www.youtube.com/embed/RubBzkZzpUA',
    ]
    video_url = random.choice(youtube_urls)
    return video_url
    #return jsonify({'video_url': video_url})

if __name__ == '__main__':
    app.run()
