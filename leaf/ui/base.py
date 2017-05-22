import logging

LOG = logging.getLogger(__name__)


class OUTPUT_TAG:
    """
    Different types of output.
    """
    UNHANDLED = -1
    SERVER_EVENT = 1
    CLIENT_INFO = 2
    USER_MSG = 3


class BaseUI:
    """
    Base class for UIs.

    :param message_callback: The function that should be used when a user sends
                             a message
    :type message_callbac: function
    :param users: Users model
    :type users: :class:`leaf.client.user.Users`
    :param commands: Available commands
    :type commands: dict{int: :class:`leaf.client.command.Command`}
    """
    def __init__(self, message_callback, users, commands):
        self.message_callback = message_callback
        self.users = users
        self.commands = commands

    def refresh_user_list(self):
        """
        Triggers a refresh of the user list in the UI.
        """
        raise NotImplemented()

    def execute_command(self, cmd_type, *args):
        """
        Executes a :class:`leaf.client.command.Command`.

        :param cmd_type: The type of command to execute
        :type cmd_type: int
        """
        if cmd_type not in self.commands:
            LOG.error("Unknown command: {}".format(cmd_type))
            return

        self.commands[cmd_type](*args)

    def run(self):
        """
        Start running the UI loop.
        """
        raise NotImplemented

    def stop(self):
        """
        Stop the UI loop.
        """
        raise NotImplemented

    def draw_output(self, tag, text, prefix=None):
        """
        Draw output on the UI.

        :param tag: The type of output. See :class:`OUTPUT_TAG`.
        :type tag: int
        :param text: Text to output
        :type text: str
        :param prefix: Optional prefix to the output (for example a user
                       for the sender of a message)
        :type prefix: object
        """
        raise NotImplemented

    def draw_unhandled(self, text):
        """
        Draw an output message about unhandled things (for example events not
        supported by the client).

        :param text: Text to output
        :type text: str
        """
        self.draw_output(OUTPUT_TAG.UNHANDLED, text)

    def draw_client_info(self, text):
        """
        Draw an client info text on the UI.

        :param text: Text to output
        :type text: str
        """
        self.draw_output(OUTPUT_TAG.CLIENT_INFO, text)

    def draw_user_message(self, user, msg):
        """
        Draw a message sent to the room.

        :param user: User
        :type user: :class:`leaf.client.user.User`
        :param msg: Message to output
        :type msg: str
        """
        self.draw_output(OUTPUT_TAG.USER_MSG, msg, prefix=user)

    def draw_user_join(self, user):
        """
        Draw an user joining the room.

        :param user: User
        :type user: :class:`leaf.client.user.User`
        """
        text = "joined the room"
        self.draw_output(OUTPUT_TAG.SERVER_EVENT, text, prefix=user)

    def draw_user_leave(self, user):
        """
        Draw an user leaving the room.

        :param user: User
        :type user: :class:`leaf.client.user.User`
        """
        text = "left the room"
        self.draw_output(OUTPUT_TAG.SERVER_EVENT, text, prefix=user)

    def draw_user_invite(self, user, invited_user):
        """
        Draw an user being invited to the room.

        :param user: User
        :type user: :class:`leaf.client.user.User`
        :param invited_user: User
        :type invited_user: :class:`leaf.client.user.User`
        """
        text = "invited {}".format(invited_user)
        self.draw_output(OUTPUT_TAG.SERVER_EVENT, text, prefix=user)

    def draw_user_change_nick(self, user, new_nick):
        """
        Draw an user changing nick.

        :param user: User
        :type user: :class:`leaf.client.user.User`
        :param new_nick: The new nickname
        :type new_nick: str
        """
        text = "changed nick to {}".format(new_nick)
        self.draw_output(OUTPUT_TAG.SERVER_EVENT, text, prefix=user)

    def draw_help(self, cmd_type=None):
        """
        Draw :class:`leaf.client.command.Command` help descriptions.

        :param cmd_type: Type of a specific command to show help for
        :type cmd_type: int
        """
        raise NotImplemented
