from collections import defaultdict
import logging

from matrix_client.user import User as MatrixUser

LOG = logging.getLogger(__name__)

#: The way a nick is formatted if more than one user has the same nick
UNIQUE_NICK_FORMAT = "{nick} ({user_id})"


class Users(dict):
    """
    A dict model of Matrix users.

    :param matrix_api: The Matrix client-server API
    :type matrix_api: :class:`matrix_client.api.MatrixHttpApi`
    """
    def __init__(self, matrix_api):
        self.matrix_api = matrix_api
        self.nick_hashmap = defaultdict(list)
        self.modified_callback = lambda: None

    def set_modified_callback(self, modified_callback):
        """
        Sets a callback function that is executed whenever the user dictionary
        or a :class:`User` has changed.

        :param modified_callback: The callback function
        :type modified_callback: function
        """
        self.modified_callback = modified_callback

    def clear(self):
        self.nick_hashmap.clear()
        super().clear()

    def __setitem__(self, user_id, user):
        super().__setitem__(user_id, user)
        self.modified_callback()

    def __delitem__(self, user_id):
        super().__delitem__(user_id)
        self.modified_callback()

    def get_user(self, user_id=None, nick=None):
        """
        Get a user from the user dict.

        If the user does not exist in the dictionary a new user is created.

        :param user_id: The MXID of the user
        :type user_id: str
        :param nick: The displayname of the user (only relevant the user
                     doesn't already exist)
        :type nick: str

        :return: The user
        :rtype: :class:`User`
        """
        if user_id in self:
            return self[user_id]
        else:
            return User(self, user_id, nick=nick)

    def add_user(self, user_id, nick=None):
        """
        Add a user to the dictionary and return it.

        :param user_id: The MXID of the user
        :type user_id: str
        :param nick: The displayname of the user
        :type nick: str
        :return: The user that has or already have been added
        :rtype: :class:`User`
        """
        user = self.get_user(user_id, nick)

        if user_id not in self:
            self[user_id] = user

        return user

    def remove_user(self, user_id):
        """
        Remove a user from the dictionary.

        :param user_id: The MXID of the user to remove
        :type user_id: str
        :return: The user that has been removed
        :rtype: :class:`User`
        """
        if user_id in self:
            user = self[user_id]
            del self[user_id]
            return user


class User(MatrixUser):
    """
    A single user.

    :param users: The users model this user belongs to.
    :type users: :class:`Users`
    :param user_id: The user's MXID
    :type user_id: str
    :param nick: The user's nickname
    :type nick: str
    """
    def __init__(self, users, user_id, nick=None):
        self.users = users

        super().__init__(self.users.matrix_api, user_id)

        self.nick = None
        if nick:
            self.update_nick(nick)

    def update_nick(self, nick):
        """
        Change the nickname of a user.

        :param nick: The new nick
        :type nick: str
        """
        if self.nick == nick:
            return

        # Update the nick hashmap
        if self.nick:
            self.users.nick_hashmap[self.nick].remove(self)
        self.users.nick_hashmap[nick].append(self)

        LOG.info("Updating user nick: {} -> {}".format(self.nick, nick))

        self.nick = nick

        self.users.modified_callback()

    def __eq__(self, other):
        return self.user_id == other.user_id

    def __ne__(self, other):
        return self.user_id != other.user_id

    def __str__(self):
        if not self.nick:
            return self.user_id

        # Check if the nick exist in the nick hashmap
        if len(self.users.nick_hashmap[self.nick]) == 1:
            return self.nick

        # If the nick is already taken by another user it is made unique
        return UNIQUE_NICK_FORMAT.format(nick=self.nick, user_id=self.user_id)
