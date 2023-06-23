from karaoke.playlist import *
from unittest.mock import patch, MagicMock


@patch("karaoke.playlist.redis_api")
def test_get_next_song(mock_redis: MagicMock) -> None:
    ids = range(100)
    mock_redis.incr.side_effect = ids

    users: list[User] = [
        amir := User.create("Amir"),
        haim := User.create("Haim"),
        daniel := User.create("Daniel"),
        twaik := User.create("Twaik"),
    ]

    songs: list[Song] = [
        Song.create(
            "Non-stop",
            "Cast of Hamilton",
            "https://www.youtube.com/watch?v=6_35a7sn6ds",
        ),
        Song.create(
            "My Shot",
            "Cast of Hamilton",
            "https://www.youtube.com/watch?v=PEHKBckBODQ",
        ),
        Song.create(
            "Unicorn",
            "Noa Kirel",
            "https://www.youtube.com/watch?v=6_35a7sn6ds",
        ),
        Song.create(
            "Weird Korean song",
            "Korean guy",
            "https://www.youtube.com/watch?v=PEHKBckBODQ",
        ),
        Song.create(
            "Seven Rings",
            "Ariana Grande",
            "https://www.youtube.com/watch?v=RubBzkZzpUA",
        ),
        Song.create(
            "Started from the Bottom",
            "Drake",
            "https://www.youtube.com/watch?v=RubBzkZzpUA",
        ),
    ]

    amir.song_ratings = [
        UserSongRating(songs[0], Rating.NEED_THE_MIC, False, False),
        UserSongRating(songs[1], Rating.NEED_THE_MIC, False, False),
        UserSongRating(songs[2], Rating.SING_ALONG, False, False),
        UserSongRating(songs[3], Rating.DONT_KNOW, False, False),
        UserSongRating(songs[4], Rating.DONT_KNOW, False, False),
        UserSongRating(songs[4], Rating.SING_ALONG, False, False),
    ]

    haim.song_ratings = [
        UserSongRating(songs[0], Rating.SING_ALONG, False, False),
        UserSongRating(songs[1], Rating.SING_ALONG, False, False),
        UserSongRating(songs[2], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[3], Rating.SING_ALONG, False, False),
        UserSongRating(songs[4], Rating.NEED_THE_MIC, False, False),
        UserSongRating(songs[5], Rating.SING_ALONG, False, False),
    ]

    daniel.song_ratings = [
        UserSongRating(songs[0], Rating.SING_ALONG, False, False),
        UserSongRating(songs[1], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[2], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[3], Rating.DONT_KNOW, False, False),
        UserSongRating(songs[4], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[5], Rating.NEED_THE_MIC, False, False),
    ]

    twaik.song_ratings = [
        UserSongRating(songs[0], Rating.SING_ALONG, False, False),
        UserSongRating(songs[1], Rating.SING_ALONG, False, False),
        UserSongRating(songs[2], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[3], Rating.NEED_THE_MIC, True, False),
        UserSongRating(songs[4], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[5], Rating.DONT_KNOW, False, False),
    ]

    mock_redis.exists.return_value = 0
    session: Session = Session.create(users)

    playlist: list[Song] = []
    while (song := session.get_next_song()) is not None:
        playlist.append(song)

    assert playlist == [
        songs[1],
        songs[4],
        songs[3],
        songs[0],
        songs[5],
        songs[2],
    ]
