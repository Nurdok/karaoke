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
    ],
)
def test_get_video_link_with_embed(url: str, expected: str) -> None:
    assert get_video_link(url, embed_yt_videos=True) == expected
