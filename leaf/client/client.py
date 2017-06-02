import json
import logging
from requests.exceptions import ConnectionError
import time

from matrix_client.client import MatrixClient
from matrix_client.errors import MatrixRequestError

from .. import settings
from . import command
from .op import op, OPExecutor
from .room_event import RoomEventObserver
from .user import Users

#: The maximum number of previous messages backfilled when connecting
HISTORY_LIMIT = 100

#: The maximum time to wait for the server to respond
SERVER_TIMEOUT_MS = 5000

LOG = logging.getLogger(__name__)


class LoginException(Exception):
    def __init__(self, msg):
        super().__init__("Error while logging in: {}".format(msg))


class RegistrationException(Exception):
    def __init__(self, msg):
        super().__init__("Error while registering new user: {}".format(msg))


class UsernameTakenException(Exception):
    pass


class UsernameInvalidException(Exception):
    pass


class CaptchaRequiredException(Exception):
    pass


class JoinRoomException(Exception):
    def __init__(self, msg):
        super().__init__("Error while joining room: {}".format(msg))


class Client:
    """
    A Matrix client implementation.

    :param server_url: The Matrix server URL
    :type server_url: str
    :param UI: The user interface object
    :type UI: :class:`.ui.base.BaseUI`
    """
    def __init__(self, server_url, UI):
        assert server_url, "Missing server URL"

        self.room = None

        self.client = MatrixClient(server_url)

        self.op_executor = OPExecutor(self._server_exception_handler)

        self.room_event_observer = RoomEventObserver(self)

        self.users = Users(self.client.api)

        commands = {}
        for name in dir(self):
            attr = getattr(self, name)
            if isinstance(attr, command.Command):
                commands[attr.cmd_type] = attr
        self.ui = UI(self.send_message, self.users, commands)

        self.users.set_modified_callback(self.ui.refresh_user_list)

    @property
    def connected(self):
        return self.client and self.client.should_listen

    def _register(self, username, password):
        """
        Register a new user on the server.
        """
        try:
            LOG.debug("Trying to register new user")
            self.client.register_with_password(username=username,
                                               password=password)
        except MatrixRequestError as exc:
            LOG.exception(exc)

            try:
                error_content = json.loads(exc.content)
            except json.decoder.JSONDecodeError:
                pass

            if exc.code == 400:
                if "errcode" in error_content:
                    if error_content["errcode"] in ("M_USER_IN_USE",
                                                    "M_EXCLUSIVE"):
                        raise UsernameTakenException()
                    elif error_content["errcode"] == "M_INVALID_USERNAME":
                        raise UsernameInvalidException(error_content["error"])
                    elif (error_content["errcode"] == "M_UNKNOWN" and
                          "error" in error_content):
                        if "captcha" in error_content["error"].lower():
                            raise CaptchaRequiredException()

    def login(self, username, password):
        """
        Login to the server.

        If the login fails we try to register a new user using the same
        username and password.

        :param username: The username to login with
        :type username: str
        :param password: The password to login with
        :type password: str
        """
        assert username, "Missing username"
        assert password, "Missing password"

        LOG.info("Trying to log in with username {}".format(username))

        try:
            self.client.login_with_password(username=username,
                                            password=password)
        except MatrixRequestError as exc:
            LOG.exception(exc)

            error_msg = "Unknown error, check debug log."

            # The login attempt failed
            if exc.code == 403:
                try:
                    self._register(username, password)
                    return
                except UsernameTakenException:
                    error_msg = ("Username '{}' taken. "
                                 "Try a different one.").format(username)
                except UsernameInvalidException as reg_exc:
                    error_msg = str(reg_exc)
                except CaptchaRequiredException:
                    error_msg = ("Captcha required for registration. Please "
                                 "use https://riot.im/app/#/register for now")
                raise RegistrationException(error_msg)

            raise LoginException(error_msg)

    def _create_room(self, room_alias):
        """
        Create a new room on the server.
        """

        """ #room:host -> room """
        room_alias_name = room_alias[1:].split(':')[0]
        return self.client.create_room(room_alias_name)

    def join(self, room_alias):
        """
        Join a room.

        If the room does not already exist on the server we try to
        automatically create it.

        :param room_alias: The alias of the room to join
        :type room_alias: str
        """
        assert room_alias, "Missing room"

        LOG.info("Joining room {}".format(room_alias))

        try:
            self.room = self.client.join_room(room_alias)
        except MatrixRequestError as exc:
            LOG.exception(exc)

            error_msg = "Unknown error, check debug log."

            # There is no mapped room ID for this room alias
            if exc.code == 404:
                self.room = self._create_room(room_alias)
                return
            else:
                try:
                    error_content = json.loads(exc.content)
                    if "errcode" in error_content:
                        if (error_content["errcode"] == "M_FORBIDDEN" or
                            (error_content["errcode"] == "M_UNKNOWN" and
                                "not legal" in error_content["error"])):
                            error_msg = error_content["error"]
                except json.decoder.JSONDecodeError:
                    pass

            raise JoinRoomException(error_msg)

    def run(self):
        """
        Run the client.
        """
        assert self.room, "You need to join a room before you run the client"

        self.room.add_listener(self.room_event_observer.on_room_event)

        self.op_executor.start()

        self.connect()

        self.ui.run()

    def stop(self):
        """
        Stop the client.
        """
        self.ui.stop()

        self.op_executor.stop()

        if self.connected:
            print("Waiting for server connection to close")
            print("Press ctrl+c to force stop")
            try:
                self.disconnect()
            except KeyboardInterrupt:
                pass

    def _server_exception_handler(self, exc):
        """
        Exception handler for Matrix server errors.
        """
        LOG.exception(exc)

        if isinstance(exc, ConnectionError):
            self.ui.draw_client_info("Server connection error")
        else:
            self.ui.draw_client_info("Unexpected server error: {}".format(exc))
            if not settings.debug:
                self.ui.draw_client_info(
                    "For more details enable debug mode, "
                    "reproduce the issue and check the logs. "
                    "Debug mode is enabled by setting the "
                    "MATRIX_DEBUG environment variable")

        self.disconnect()

    def _populate_room(self):
        # Clear the users model from old user data. To avoid duplicates when
        # for example reconnecting
        self.users.clear()

        # Temporarily disable UI user list refresh callback when doing the
        # initial population of the users model. Especially important for large
        # rooms which would cause an excessive amount of re-draws.
        modified_callback = self.users.modified_callback
        self.users.set_modified_callback(lambda: None)

        users = self.room.get_joined_members().items()
        for user_id, user in users:
            self.users.add_user(user_id, nick=user["displayname"])

        # Restore refresh callback
        self.users.set_modified_callback(modified_callback)

        # Execute an initial refresh
        modified_callback()

    @command.cmd(command.CONNECT, help_msg="Reconnect to the server")
    @op(require_connection=False)
    def connect(self):
        """
        Connect to the server.

        Before the client starts syncing events with the server it retrieves
        the users currently in the room and backfills previous messages. The
        number of previous messages backfilled are decidede by
        :const:`HISTORY_LIMIT`.
        """
        if self.connected:
            self.ui.draw_client_info("Already connected")
            return

        # Retrieve users currently in the room
        self._populate_room()

        # Get message history
        self.room.backfill_previous_messages(limit=HISTORY_LIMIT)

        self.client.start_listener_thread(
            timeout_ms=SERVER_TIMEOUT_MS,
            exception_handler=self._server_exception_handler)

        self.ui.draw_client_info("Connected to server")

    def disconnect(self):
        """
        Disconnect from the server.

        This also causes the user to logout when the sync thread has closed.
        """
        if self.connected:
            # Can't unfortunately cancel an in-flight request
            # https://github.com/kennethreitz/requests/issues/1353
            self.client.should_listen = False

            self.ui.draw_client_info("Disconnected")

            # Wait here for the matrix client sync thread to exit before
            # joining so that we can interrupt using signals.
            while self.client.sync_thread.isAlive():
                time.sleep(0.1)

        try:
            self.client.api.logout()
        except ConnectionError:
            pass

    @op
    def send_message(self, msg):
        """
        Send a message to the room.

        :param msg: Message to send
        :type msg: str
        """
        self.room.send_text(msg)

    @command.cmd(command.INVITE,
                 help_msg=("Invite a user to the room "
                           "(user_id syntax: @[mxid]:[server])"))
    @op
    def invite(self, user_id):
        """
        Invite a user to the room.

        :param user_id: The MXID of the user you want to invite
        :type user_id: str
        """
        try:
            self.client.api.invite_user(self.room.room_id, user_id)
            # self.room.invite_user(args[0])
        except MatrixRequestError as exc:
            try:
                error_msg = json.loads(exc.content)["error"]
            except:
                error_msg = str(exc)
            self.ui.draw_client_info("Invite error: {}".format(error_msg))

    @command.cmd(command.CHANGE_NICK, help_msg="Change nick")
    @op
    def change_nick(self, nick):
        """
        Change your nick.

        :param nick: The displayname you want to change to.
        :type nick: str
        """
        self.users.get_user(self.client.user_id).set_display_name(nick)

    @command.cmd(command.LEAVE, help_msg="Leave the room")
    def leave(self):
        """
        Leave the room.
        """
        # Stop listening for new events, when we leave the room we're forbidden
        # from interacting with the it anything anyway
        self.client.should_listen = False

        self.room.leave()

        self.ui.stop()

    @command.cmd(command.QUIT, help_msg="Exit the client")
    def quit(self):
        """
        Exit the client.
        """
        self.ui.stop()

    @command.cmd(command.HELP, help_msg="Show this")
    def show_help(self, cmd_type=None):
        """
        Show a help message explaining all the available commands.

        :param cmd_type: Use cmd_type to display the help message of a specific
                         command rather than all of them.
        :type cmd_type: int
        """
        self.ui.draw_help(cmd_type)
