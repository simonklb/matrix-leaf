from inspect import signature, Signature

HELP = 1
CONNECT = 2
INVITE = 3
CHANGE_NICK = 4
LEAVE = 5
QUIT = 6


class Command:
    """
    A command is a function that can be executed by a certain trigger.

    If the command is called with the wrong set of parameters the HELP
    command will be triggered.

    :param cmd_type: The type of command
    :type cmd_type: int
    :param callback: The callback to be executed when this command is triggered
    :type callback: function
    :param help_msg: Description of what the command does
    :type help_msg: str
    """
    def __init__(self, cmd_type, callback, help_msg):
        self.cmd_type = cmd_type

        self._callback = callback

        self.help_msg = help_msg

        self.parameters = []
        self.optional_paramters = []
        for param in signature(callback).parameters.values():
            if param.name != "self":
                if param.default != Signature.empty:
                    self.optional_paramters.append(param.name)
                else:
                    self.parameters.append(param.name)

    def __get__(self, client, client_class):
        self._client = client
        return self

    def __call__(self, *args, **kwargs):
        if (len(args) < len(self.parameters) or
                len(args) > (len(self.parameters) +
                             len(self.optional_paramters))):
            self._client.show_help(self.cmd_type)
        else:
            self._callback(self._client, *args, **kwargs)


def cmd(cmd_type, help_msg="N/A"):
    """
    Decorator to turn a function into a :class:`Command`

    :param cmd_type: The type of command
    :type cmd_type: int
    :param help_msg: Description of what the command does
    :type help_msg: str
    """
    def decorator(func):
        return Command(cmd_type, func, help_msg)
    return decorator
