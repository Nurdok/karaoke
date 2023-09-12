// Function to get the value of a cookie by its name

const USER_ID_COOKIE_NAME = "userId";
const USER_NAME_COOKIE_NAME = "username";


function getCookie(cookieName) {
    let name = cookieName + "=";
    let decodedCookie = decodeURIComponent(document.cookie);
    let cookieArray = decodedCookie.split(';');

    for (let i = 0; i < cookieArray.length; i++) {
        let cookie = cookieArray[i];
        while (cookie.charAt(0) === ' ') {
            cookie = cookie.substring(1);
        }
        if (cookie.indexOf(name) === 0) {
            return cookie.substring(name.length, cookie.length);
        }
    }
    return null;
}

function getUserOrRedirectToLoginPage () {
    let userId = getCookie(USER_ID_COOKIE_NAME);
    if (userId === null) {
        // If the user is not logged in, redirect to the login page
        window.location.href = "/users";
    }
    let username = getCookie(USER_NAME_COOKIE_NAME);
    return {id: userId, name: username};
}

// Function to set a cookie with a specified name, value, and expiration date
function setCookie(cookieName, cookieValue, expirationDays) {
    var date = new Date();
    date.setTime(date.getTime() + (expirationDays * 24 * 60 * 60 * 1000));
    var expires = "expires=" + date.toUTCString();
    document.cookie = cookieName + "=" + cookieValue + ";" + expires + ";path=/";
}

function login(id, name) {
    setCookie(USER_ID_COOKIE_NAME, id, 300);
    setCookie(USER_NAME_COOKIE_NAME, name, 300);

    window.location.href = '/';
}
function toRatingEnumString(rating_int) {
    switch (rating_int) {
        case 0:
            return 'UNKNOWN';
        case 1:
            return 'DONT_KNOW';
        case 2:
            return 'SING_ALONG';
        case 3:
            return 'CAN_TAKE_THE_MIC';
        case 4:
            return 'NEED_THE_MIC';
    }
}

function toRatingDisplayString(rating_int) {
    switch (rating_int) {
        case 0:
            return 'Not rated';
        case 1:
            return 'I don\'t know this song';
        case 2:
            return 'I can sing along';
        case 3:
            return 'I can take the mic';
        case 4:
            return 'I NEED THE MIC';
    }
}

function toScore(rating_int) {
    switch (rating_int) {
        case 0:
            return 0;
        case 1:
            return -1;
        case 2:
            return 1;
        case 3:
            return 2;
        case 4:
            return 5;
    }
}

function toStars(rating_int) {
    switch (rating_int) {
        case 0:
            return '<span class="empty-star">★★★★★</span>'
        case 1:
            return '<span class="empty-star">★★★★★</span>'
        case 2:
            return '<span class="gold-star">★</span><span class="empty-star">★★★★</span>';
        case 3:
            return '<span class="gold-star">★★</span><span class="empty-star">★★★</span>';
        case 4:
            return '<span class="gold-star">★★★★★</span>'
    }
}

function parseJsonSong(song) {
    if (song.status === 'OK') {
        return {
            'status': song.status,
            'id': song.id,
            'title': song.title,
            'artist': song.artist,
            'video_link': song.video_link,
            'ratings': song.ratings,
        };
    }
    return {
        'status': song.status,
        'id': null,
        'title': song.title,
        'artist': '',
        'video_link': '',
    };
}

function rateSong(user_id, song_id, rating_int) {
    let ratingString = toRatingEnumString(rating_int)
    const data = {
        userId: user_id,
        songId: song_id,
        rating: ratingString
    };
    console.log(data);

    return fetch('/api/rate-song', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
}

function getCurrentScores(session_display_id) {
    return fetch(`/api/get-current-scores?s=${session_display_id}`)
        .then(response => response.json());
}

function getVideoEmbedInnerHtml(video_link, autoplay = false) {
    let autoplay_int = autoplay ? 1 : 0;
    return `<iframe width="100%" height="100%" src="${video_link}?autoplay=${autoplay}" frameborder="0" allowfullscreen allow="autoplay"></iframe>`;
}

function editSong(song_id, artist, title, video_link) {
    const data = {
        song_id: song_id,
        artist: artist,
        title: title,
        video_link: video_link
    };

    return fetch('/api/edit-song', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
}

function deleteSong(song_id) {
    const data = {
        song_id: song_id,
    };

    return fetch('/api/delete-song', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    });
}