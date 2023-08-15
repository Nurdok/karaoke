from karaoke.core.song import get_video_link
import pytest


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        [
            "https://www.youtube.com/watch?v=6_35a7sn6ds",
            "https://youtube.com/watch?v=6_35a7sn6ds",
        ],
        [
            "https://www.youtube.com/embed/6_35a7sn6ds",
            "https://youtube.com/watch?v=6_35a7sn6ds",
        ],
        [
            "6_35a7sn6ds",
            "https://youtube.com/watch?v=6_35a7sn6ds",
        ],
        [
            "https://link.to/video.mp4",
            "https://link.to/video.mp4",
        ],
        [
            "https://www.video-cdn.com/embed/iframe/e13f3b996e82c544b591a4b8884dec5d/fc94e91dd725a9947b5348603c9a8487/?type=mp4&time_limit=300&autoplay=true&simple=true&noadv=true",
            "https://www.video-cdn.com/embed/iframe/e13f3b996e82c544b591a4b8884dec5d/fc94e91dd725a9947b5348603c9a8487/?type=mp4&time_limit=300&autoplay=true&simple=true&noadv=true",
        ],
    ],
)
def test_get_video_link_no_embed(url: str, expected: str) -> None:
    assert get_video_link(url, embed_yt_videos=False) == expected


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        [
            "https://www.youtube.com/watch?v=6_35a7sn6ds",
            "https://www.youtube.com/embed/6_35a7sn6ds",
        ],
        [
            "https://www.youtube.com/embed/6_35a7sn6ds",
            "https://www.youtube.com/embed/6_35a7sn6ds",
        ],
        [
            "6_35a7sn6ds",
            "https://www.youtube.com/embed/6_35a7sn6ds",
        ],
        [
            "https://link.to/video.mp4",
            "https://link.to/video.mp4",
        ],
        [
            "https://www.video-cdn.com/embed/iframe/e13f3b996e82c544b591a4b8884dec5d/fc94e91dd725a9947b5348603c9a8487/?type=mp4&time_limit=300&autoplay=true&simple=true&noadv=true",
            "https://www.video-cdn.com/embed/iframe/e13f3b996e82c544b591a4b8884dec5d/fc94e91dd725a9947b5348603c9a8487/?type=mp4&time_limit=300&autoplay=true&simple=true&noadv=true",
        ],
    ],
)
def test_get_video_link_with_embed(url: str, expected: str) -> None:
    assert get_video_link(url, embed_yt_videos=True) == expected
