from collections import Counter
from datetime import datetime
from threading import Lock

import urwid
import urwid.curses_display

from ... import settings
from ...client import command
from ...client.user import User
from ..base import BaseUI, OUTPUT_TAG

#: Width of user list pane
USER_WIDTH = 16

#: Colors that the users will get assigned
USER_COLOR_PALETTE = [
    ("user_red", urwid.LIGHT_RED, urwid.DEFAULT),
    ("user_magenta", urwid.LIGHT_MAGENTA, urwid.DEFAULT),
    ("user_blue", urwid.LIGHT_BLUE, urwid.DEFAULT),
    ("user_cyan", urwid.LIGHT_CYAN, urwid.DEFAULT),
    ("user_green", urwid.LIGHT_GREEN, urwid.DEFAULT),
    ("user_yellow", urwid.YELLOW, urwid.DEFAULT),
]

#: Symbols to indicate different types of outputs
TAG_SYMBOLS = {
    OUTPUT_TAG.UNHANDLED: '?',
    OUTPUT_TAG.SERVER_EVENT: '*',
    OUTPUT_TAG.CLIENT_INFO: '!',
    OUTPUT_TAG.USER_MSG: ''
}

#: The character used to indicate an input being a command
CMD_PREFIX = '/'

#: Aliases that the users can use to execute commands
CMD_ALIASES = {
    command.HELP: ["help"],
    command.CONNECT: ["connect", "reconnect"],
    command.INVITE: ["invite"],
    command.CHANGE_NICK: ["nick", "name"],
    command.LEAVE: ["leave", "part"],
    command.QUIT: ["quit", "close", "exit"]
}


class UserList(urwid.SimpleListWalker):
    """
    User list widget.

    :param users: Users model
    :type users: :class:`leaf.client.user.Users`
    """
    def __init__(self, users):
        self._users = users
        self.colormap = dict()
        super().__init__(list())
        self.refresh()

    def _get_least_used_color(self):
        color_values = [color[0] for color in USER_COLOR_PALETTE]
        counter = Counter(list(self.colormap.values()) + color_values)
        return min(counter, key=counter.get)

    def _update_colormap(self):
        for user_id in list(self.colormap):
            if user_id not in self._users:
                del self.colormap[user_id]

        for user_id in self._users:
            if user_id not in self.colormap:
                self.colormap[user_id] = self._get_least_used_color()

    def get_user_text(self, user):
        """
        Create a text widget with the colorized username of a user.

        :param user: The user
        :type user: :class:`leaf.client.user.Users`
        """
        if user.user_id in self._users:
            return urwid.Text((self.colormap[user.user_id], str(user)))
        else:
            return urwid.Text((self._get_least_used_color(), str(user)))

    def refresh(self):
        """
        Re-draw the user list.
        """
        self._update_colormap()
        del self[:]
        self += list(self._users)

    def __getitem__(self, index):
        user = self._users[super().__getitem__(index)]
        return self.get_user_text(user)


class ConsoleUI(BaseUI):
    """
    A terminal based UI with the look and feel of an IRC client built with
    the urwid lib using curses.
    """
    def __init__(self, message_callback, users, commands):
        super().__init__(message_callback, users, commands)

        self._draw_mutex = Lock()

        self.loop = None

        self.screen = urwid.curses_display.Screen()

        self.user_list = UserList(self.users)
        self.users_box = urwid.ListBox(self.user_list)

        self.output_box = urwid.ListBox(urwid.SimpleListWalker([]))

        body = urwid.Columns([
            self.output_box,
            (1, urwid.SolidFill(' ')),
            (1, urwid.SolidFill(u'\u2502')),
            (USER_WIDTH, self.users_box)
        ])

        self.input_box = urwid.AttrWrap(urwid.Edit("> "), "input_box")
        footer = urwid.Pile([urwid.Divider(u'\u2500'), self.input_box])

        self.frame = urwid.Frame(body, footer=footer)
        self.frame.set_focus("footer")

        color_palette = [
            ("input_box", urwid.LIGHT_CYAN, urwid.DEFAULT)
        ] + USER_COLOR_PALETTE

        self.loop = urwid.MainLoop(
            self.frame, color_palette,
            screen=self.screen,
            handle_mouse=False,
            input_filter=self._input_filter,
            unhandled_input=self._unhandled_input
        )

    def _refresh(self):
        # Prevent redraw race -- messes up the ui
        self._draw_mutex.acquire()

        if self.screen.started:
            self.loop.draw_screen()

        self._draw_mutex.release()

    def refresh_user_list(self):
        self.user_list.refresh()
        self._refresh()

    def _is_command_input(self, input_text):
        return len(input_text) > 0 and input_text[0] == CMD_PREFIX

    def _get_cmd_from_alias(self, alias):
        for cmd, aliases in CMD_ALIASES.items():
            if alias in aliases:
                return cmd

    def _input_filter(self, keys, raw):
        if not keys:
            return []

        key = keys[0]
        if key == "enter":
            input_text = self.input_box.get_edit_text()

            if self._is_command_input(input_text):
                cmd_line = input_text.split(' ')
                cmd_alias = cmd_line[0][1:]
                cmd_args = cmd_line[1:] if len(cmd_line) > 1 else []

                cmd = self._get_cmd_from_alias(cmd_alias)

                if not cmd:
                    self.draw_client_info("Unknown command: {}\n"
                                          "See /help".format(cmd_alias))
                    return []

                self.execute_command(cmd, *cmd_args)
            else:
                self.message_callback(input_text)

            self.input_box.set_edit_text("")

            return []

        elif key in ("page up", "page down"):
            self.frame.set_focus("body")

        else:
            self.frame.set_focus("footer")

        return keys

    def _unhandled_input(self, key):
        if settings.debug:
            self.draw_unhandled("UNHANDLED KEY: {}".format(key))

    def run(self):
        self.screen.start()

        # TODO
        # if self.loop.handle_mouse:
        #     self.loop.screen.set_mouse_tracking()

        while self.screen.started:
            self._refresh()

            keys = None
            raw = None
            try:
                while not keys:
                    keys, raw = self.screen.get_input(True)
            except KeyboardInterrupt:
                return

            keys = self.loop.input_filter(keys, raw)

            if keys:
                self.loop.process_input(keys)

            if "window resize" in keys:
                self.loop.screen_size = None

    def stop(self):
        self.screen.stop()

    def draw_output(self, tag, text, prefix=None):
        time = datetime.now().strftime("%H:%M:%S")
        time = (len(time), urwid.Text("{}".format(time)))

        tag_width = max([len(tag) for tag in TAG_SYMBOLS.values()])
        tag = (tag_width, urwid.Text(TAG_SYMBOLS[tag]))

        if not prefix:
            prefix = urwid.Text("")
        elif isinstance(prefix, User):
            prefix = self.user_list.get_user_text(prefix)
        else:
            prefix = urwid.Text(prefix)
        prefix.set_align_mode("right")
        prefix = (USER_WIDTH, prefix)

        hline = (1, urwid.SolidFill(u'\u2502'))

        text = urwid.Text(text)

        self.output_box.body.append(urwid.Columns([
            time, tag, prefix, hline, text
        ], dividechars=1, box_columns=[3]))

        # Scroll to bottom
        self.output_box.set_focus(len(self.output_box.body) - 1, "above")

        self._refresh()

    def draw_help(self, cmd_type=None):
        for cmd_type, cmd in self.commands.items():
            if not cmd_type or cmd_type in CMD_ALIASES:
                params = ""
                if cmd.parameters:
                    params = ["[{}]".format(param.replace('_', ' '))
                              for param in cmd.parameters]
                    params = " {}".format(' '.join(params))
                cmd_line = "{}{}{}".format(CMD_PREFIX,
                                           CMD_ALIASES[cmd_type][0], params)
                msg = "{}\n{}\n".format(cmd_line, cmd.help_msg)
                self.draw_client_info(msg)
