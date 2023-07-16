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