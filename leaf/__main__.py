from getpass import getpass
import logging
import os
from requests import exceptions as requests_exceptions

from matrix_client.errors import MatrixRequestError

from . import settings as leaf_settings
from . import client as leaf_client
from .client import exceptions as leaf_exceptions
from . import ui as leaf_ui

LOG = logging.getLogger(__name__)


def user_parameter(envvar, text, password=False, example=None):
    input_value = os.environ.get(envvar)
    if input_value:
        return input_value

    input_func = getpass if password else input
    example = " (example {})".format(example) if example else ""
    prompt = "{}{}: ".format(text, example)

    while not input_value:
        input_value = input_func(prompt)

    return input_value


def main():
    if leaf_settings.debug:
        logging.basicConfig(filename="debug.log", level=logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.WARN)
        logging.getLogger("urllib3").setLevel(logging.WARN)
    else:
        logging.basicConfig(level=logging.CRITICAL)

    server_url = user_parameter("MATRIX_SERVER_URL", "Server URL",
                                example="https://matrix.org")
    username = user_parameter("MATRIX_USERNAME", "Username")
    password = user_parameter("MATRIX_PASSWORD", "Password", password=True)
    room = user_parameter("MATRIX_ROOM", "Room", example="#matrix:matrix.org")

    client = leaf_client.Client(server_url, leaf_ui.ConsoleUI)

    try:
        try:
            client.login(username, password)
        except leaf_exceptions.LoginFailed as exc:
            print(str(exc))

            try:
                print("Trying to register a new user")
                client.register(username, password)
            except leaf_exceptions.RegistrationException as exc:
                print(str(exc))
                exit()

        except leaf_exceptions.LoginException as exc:
            print(str(exc))
            exit()

        try:
            client.join(room)
        except leaf_exceptions.RoomNotFound as exc:
            print(str(exc))

            try:
                print("Trying to create a new room")
                client.create_room(room)
            except Exception as exc:
                print(str(exc))
                exit()

        except leaf_exceptions.JoinRoomException as exc:
            print(str(exc))
            exit()

        client.run()
    except MatrixRequestError as exc:
        LOG.exception(exc)
        print("Matrix server error")

        if leaf_settings.debug:
            print("Check the debug log")
        else:
            print("Enable debug mode and check the log. (Use MATRIX_DEBUG=1)")
    except requests_exceptions.ConnectionError as exc:
        print("Server connection error")
        LOG.exception(exc)
    except (requests_exceptions.MissingSchema,
            requests_exceptions.InvalidSchema):
        print("The server URL needs a valid schema. "
              "Did you forget to add 'https://'?")
    finally:
        client.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
