from getpass import getpass
import logging
import os
from requests.exceptions import ConnectionError, InvalidSchema, MissingSchema

from matrix_client.errors import MatrixRequestError

from . import settings
from .client import Client, LoginException, JoinRoomException
from .ui import ConsoleUI

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
    if settings.debug:
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

    client = Client(server_url, ConsoleUI)

    try:
        client.login(username, password)
        client.join(room)
        client.run()
    except LoginException as exc:
        print(str(exc))
        exit(1)
    except JoinRoomException as exc:
        print(str(exc))
        exit(2)
    except MatrixRequestError as exc:
        LOG.exception(exc)
        print("Matrix server error")

        if settings.debug:
            print("Check the debug log")
        else:
            print("Enable debug mode and check the log. (Use MATRIX_DEBUG=1)")

        exit(3)
    except ConnectionError as exc:
        print("Server connection error")
        LOG.exception(exc)
        exit(4)
    except (MissingSchema, InvalidSchema):
        print("The server URL needs a valid schema. "
              "Did you forget to add 'https://'?")
        exit(5)
    finally:
        client.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
