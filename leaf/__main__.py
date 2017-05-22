from getpass import getpass
import logging
import os
from requests.exceptions import ConnectionError

from matrix_client.errors import MatrixRequestError

from . import settings
from .client import Client, LoginException, JoinRoomException
from .ui import ConsoleUI

LOG = logging.getLogger(__name__)


def main():
    if settings.debug:
        logging.basicConfig(filename="debug.log", level=logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.WARN)
        logging.getLogger("urllib3").setLevel(logging.WARN)
    else:
        logging.basicConfig(level=logging.CRITICAL)

    hostname = os.environ.get("MATRIX_HOSTNAME") or input("Server hostname: ")
    username = os.environ.get("MATRIX_USERNAME") or input("Username: ")
    password = os.environ.get("MATRIX_PASSWORD") or getpass("Password: ")
    room = os.environ.get("MATRIX_ROOM") or input("Room: ")

    client = Client(hostname, ConsoleUI)

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
    finally:
        client.stop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
