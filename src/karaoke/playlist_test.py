from karaoke.playlist import *

def test_get_next_song():
    users: list[User] = [
        User(0, "Amir"),
        User(1, "Haim"),
        User(2, "Daniel"),
        User(3, "Twaik"),
    ]

    songs: list[Song] = [
        Song(0, "Non-stop", "Cast of Hamilton", "https://www.youtube.com/watch?v=6_35a7sn6ds"),
        Song(1, "My Shot", "Cast of Hamilton", "https://www.youtube.com/watch?v=PEHKBckBODQ"),
        Song(2, "Unicorn", "Noa Kirel", "https://www.youtube.com/watch?v=6_35a7sn6ds"),
        Song(3, "Weird Korean song", "Korean guy", "https://www.youtube.com/watch?v=PEHKBckBODQ"),
        Song(4, "Seven Rings", "Ariana Grande", "https://www.youtube.com/watch?v=RubBzkZzpUA"),
        Song(5, "Started from the Bottom", "Drake", "https://www.youtube.com/watch?v=RubBzkZzpUA"),
    ]

    users[0].song_ratings = [
        UserSongRating(songs[0], Rating.NEED_THE_MIC, False, False),
        UserSongRating(songs[1], Rating.NEED_THE_MIC, False, False),
        UserSongRating(songs[2], Rating.SING_ALONG, False, False),
        UserSongRating(songs[3], Rating.DONT_KNOW, False, False),
        UserSongRating(songs[4], Rating.DONT_KNOW, False, False),
        UserSongRating(songs[4], Rating.SING_ALONG, False, False),
    ]

    users[1].song_ratings = [
        UserSongRating(songs[0], Rating.SING_ALONG, False, False),
        UserSongRating(songs[1], Rating.SING_ALONG, False, False),
        UserSongRating(songs[2], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[3], Rating.SING_ALONG, False, False),
        UserSongRating(songs[4], Rating.NEED_THE_MIC, False, False),
        UserSongRating(songs[5], Rating.SING_ALONG, False, False),
        ]

    users[2].song_ratings = [
        UserSongRating(songs[0], Rating.SING_ALONG, False, False),
        UserSongRating(songs[1], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[2], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[3], Rating.DONT_KNOW, False, False),
        UserSongRating(songs[4], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[5], Rating.NEED_THE_MIC, False, False),
    ]

    users[3].song_ratings = [
        UserSongRating(songs[0], Rating.SING_ALONG, False, False),
        UserSongRating(songs[1], Rating.SING_ALONG, False, False),
        UserSongRating(songs[2], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[3], Rating.NEED_THE_MIC, True, False),
        UserSongRating(songs[4], Rating.CAN_TAKE_THE_MIC, False, False),
        UserSongRating(songs[5], Rating.DONT_KNOW, False, False),
    ]

    session = Session("ABCD", users)

    playlist: list[Song] = [
        session.get_next_song(),
        session.get_next_song(),
        session.get_next_song(),
        session.get_next_song(),
        session.get_next_song(),
        session.get_next_song(),
    ]

    assert playlist == []

