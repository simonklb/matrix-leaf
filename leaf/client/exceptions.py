class LoginException(Exception):
    def __init__(self, msg):
        super().__init__("Error while logging in: {}".format(msg))


class LoginUnknownError(LoginException):
    def __init__(self, matrix_exc):
        msg = "Unknown error, check debug log"

        if hasattr(matrix_exc, "code"):
            msg += " (code: {})".format(matrix_exc.code)

        super().__init__(msg)


class LoginFailed(LoginException):
    def __init__(self):
        super().__init__("Login failed")


class RegistrationException(Exception):
    def __init__(self, msg):
        super().__init__("Error while registering new user: {}".format(msg))


class RegistrationUnknownError(RegistrationException):
    def __init__(self, matrix_exc):
        msg = "Unknown error, check debug log"

        if hasattr(matrix_exc, "code"):
            msg += " (code: {})".format(matrix_exc.code)

            if matrix_exc.code == 500:
                msg += (" [hint] Might be caused by uncommon characters in "
                        "username or password.")

        super().__init__(msg)


class UsernameTaken(RegistrationException):
    def __init__(self, username):
        super().__init__("Username '{}' taken. Try a different "
                         "one.".format(username))


class CaptchaRequired(RegistrationException):
    def __init__(self):
        super().__init__("Captcha required for registration. Please use "
                         "https://riot.im/app/#/register for now.")


class JoinRoomException(Exception):
    def __init__(self, msg):
        super().__init__("Error while joining room: {}".format(msg))


class JoinRoomUnknownError(JoinRoomException):
    def __init__(self, matrix_exc):
        msg = "Unknown error, check debug log"

        if hasattr(matrix_exc, "code"):
            msg += " (code: {})".format(matrix_exc.code)

        super().__init__(msg)


class RoomNotFound(JoinRoomException):
    def __init__(self):
        super().__init__("Room not found")
