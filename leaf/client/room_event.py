import logging
from pprint import pformat

from .. import settings

LOG = logging.getLogger(__name__)

# Event handler mapping
handlers = {}

# Event types
UNHANDLED = -1
MSG = 1
JOIN = 2
LEAVE = 3
INVITE = 4
PROFILE_CHANGE = 5


class RoomEventHandlerType(type):
    """
    Metaclass that automatically registers the room event handler in the
    handlers dict.
    """
    def __new__(meta, name, bases, dct):
        cls = super(RoomEventHandlerType, meta).__new__(meta, name, bases, dct)

        if bases:  # We don't want to register the base class
            if "event_type" not in dct:
                raise NotImplementedError

            handlers[dct["event_type"]] = cls

        return cls


class RoomEventHandler(metaclass=RoomEventHandlerType):
    """
    Base class for room event handlers.

    :param event: The event to handle
    :type event: dict
    :param client: The client instance the room event observer is created by
    :type client: :class:`leaf.client.client.Client`
    """
    def __init__(self, event, client):
        self.event = event
        self.client = client

    def parse(self):
        """
        This should be implemented to do the event specific parsing.
        """
        raise NotImplementedError

    def callback(self, **event_data):
        """
        The callback functions that takes action on the incoming event.
        """
        raise NotImplementedError

    def process(self):
        """
        Parses the event and executes the callback.
        """
        self.callback(**self.parse())


class UnhandledHandler(RoomEventHandler):
    """
    Handler for all room events that are not parsed.
    """
    event_type = UNHANDLED

    def parse(self):
        return {
            "event": self.event
        }

    def callback(self, event):
        if not settings.debug:
            return

        text = "UNHANDLED EVENT: {}".format(pformat(event))
        self.client.ui.draw_unhandled(text)


class MessageHandler(RoomEventHandler):
    """
    Handler for text message events.
    """
    event_type = MSG

    def parse(self):
        return {
            "user_id": self.event["sender"],
            "msg": self.event["content"]["body"]
        }

    def callback(self, user_id, msg):
        user = self.client.users.get_user(user_id)
        self.client.ui.draw_user_message(user, msg)


class JoinHandler(RoomEventHandler):
    """
    Event handler for users joining the room.
    """
    event_type = JOIN

    def parse(self):
        nick = None
        if "displayname" in self.event["content"]:
            nick = self.event["content"]["displayname"]

        return {
            "user_id": self.event["sender"],
            "nick": nick
        }

    def callback(self, user_id, nick):
        user = self.client.users.add_user(user_id, nick=nick)
        self.client.ui.draw_user_join(user)


class LeaveHandler(RoomEventHandler):
    """
    Event handler for users leaving the room.
    """
    event_type = LEAVE

    def parse(self):
        return {
            "user_id": self.event["sender"]
        }

    def callback(self, user_id):
        user = self.client.users.remove_user(user_id)

        # Could happen that a user leave event is included in the backlog but
        # not the associated join. Get a temporary user.
        if not user:
            user = self.client.users.get_user(user_id)

        self.client.ui.draw_user_leave(user)


class InviteHandler(RoomEventHandler):
    """
    Handler for invite events.
    """
    event_type = INVITE

    def parse(self):
        return {
            "user_id": self.event["sender"],
            "invited_user_id": self.event["state_key"]
        }

    def callback(self, user_id, invited_user_id):
        user = self.client.users.get_user(user_id)
        invited_user = self.client.users.get_user(invited_user_id)
        self.client.ui.draw_user_invite(user, invited_user)


class ProfileChangeHandler(RoomEventHandler):
    """
    Handler for profile change events.

    This only supports displayname changes right now.
    """
    event_type = PROFILE_CHANGE

    def parse(self):
        return {
            "user_id": self.event["sender"],
            "new_nick": self.event["content"]["displayname"]
        }

    def callback(self, user_id, new_nick):
        """
        :param user_id: The MXID of the user that did a profile change
        :param new_nick: The new displayname of the user.
        """
        user = self.client.users.get_user(user_id)

        # Profile changes could be caused by different things other than
        # changing the nick
        if user.nick == new_nick:
            return

        self.client.ui.draw_user_change_nick(user, new_nick)

        # We want to update the nick after the ui room event output has been
        # drawn so that it shows the previous nick of the user
        user.update_nick(nick=new_nick)


class RoomEventObserver:
    """
    The RoomEventObserver class takes care of incoming room events from the
    server sync thread. It parses incoming event types and runs the
    corresponding room event handler.

    :param client: The client instance the room event observer is created by
    :type client: :class:`leaf.client.client.Client`
    """
    def __init__(self, client):
        self.client = client

    def on_room_event(self, room, event):
        """
        The room event listener function which receives incoming events and
        executes the appropriate handler.

        :param room: The room which the observer is listening to
        :param event: The event that was just intercepted
        """
        LOG.debug("Received event: {}".format(pformat(event)))
        event_type = self.parse_event_type(event)
        handler = handlers[event_type](event, self.client)
        handler.process()

    def parse_event_type(self, event):
        """
        This function parses an event and returns an event type.

        :param event: The event that is going to be parsed
        :return: The event type
        """
        if "redacted_because" in event:
            return UNHANDLED

        if event["type"] == "m.room.member":
            return self._parse_membership_event_type(event)

        if event["type"] == "m.room.message":
            if ("msgtype" in event["content"] and
                    event["content"]["msgtype"] == "m.text"):
                return MSG

        return UNHANDLED

    def _parse_membership_event_type(self, event):
        if event["content"]["membership"] == "join":
            return self._parse_join_event_type(event)

        if event["content"]["membership"] == "leave":
            return LEAVE

        if event["content"]["membership"] == "invite":
            return INVITE

    def _parse_join_event_type(self, event):
        # join -> join is a profile change
        if ("prev_content" in event["unsigned"] and
                event["unsigned"]["prev_content"]["membership"] == "join"):
            return PROFILE_CHANGE

        else:
            return JOIN
