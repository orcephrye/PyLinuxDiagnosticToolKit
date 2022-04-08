#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson

# Version: 0.5.0
# Date: 12/10/14
# Description:

import logging
import uuid
import traceback
import re
from paramiko import Channel
from threading import RLock
from PyLinuxDiagnosticToolKit.libs.LDTKExceptions import SSHExceptionConn
from typing import Optional, Union, AnyStr, Any


log = logging.getLogger('sshChannelEnvironment')


# noinspection PyMissingConstructor,PyUnusedLocal
class sshChannelWrapper(Channel):
    """
        This is a special wrapper class for the Paramiko Channel class. This is designed to store additional information
        regarding the status of environment associated with the channel. IE: console type, user permissions, PATH and
        so on.
    """

    _id = None
    __MAIN__ = None
    _defaultPromptReg = r"bash-\d\.\d[#|$|>|@|~]"
    _defaultPromptCompileReg = None

    def __new__(cls, parentInst: Any, **kwargs):
        parentInst.__class__ = sshChannelWrapper
        return parentInst

    def __init__(self, parentInst: Any, main: bool = False, **kwargs):
        self._id = str(uuid.uuid4())
        self.__MAIN__ = main
        self._defaultPromptCompileReg = re.compile(self._defaultPromptReg)

    @property
    def isMain(self):
        return self.__MAIN__


# noinspection PyMissingConstructor,PyUnusedLocal
class sshEnvironment(sshChannelWrapper):
    """
        Uses the sshChannelWrapper and is used by the EnvironmentControls. This handles the state of the ssh Environment
        it is associated with. Such as the prompt/current user/console and so on.
    """

    BASH = "BASH"
    CSH = "CSH"
    ZSH = "ZSH"
    SH = "SH"
    NOSH = "NO_SH"
    ORACLE = "ORACLE"
    MYSQL = "MYSQL"

    __USER_ESCALATION__ = 1
    __CONSOLE_ESCALATION__ = 2
    __ENVIRONMENT_CHANGE__ = 3
    __UNKNOWN__ = 4
    __TYPE_DICT__ = {'user': 1, 'console': 2, 'env': 3, 'unknown': 4}
    __INVERTED_TYPE_DICT__ = {1: 'User', 2: 'Console', 3: 'Environment', 4: 'Unknown'}

    # Item template Type, Command, Input
    # InputType is one of the static variables above
    # Name: This is the console or userName or the name of the environment variable being changed
    # Command is a string/dictionary that will be ran on the console
    # Input is usually the password used. But can also be any other expected input for the command to complete.
    # _template = (type, name, command, input)
    _template = (None, None, None, None)

    prompt: str = None
    _consoleStack: list = None
    _CONSOLESTACK_LOCK: RLock = None

    def __new__(cls, parentInst: Any, *args, **kwargs):
        parentInst.__class__ = sshEnvironment
        return parentInst

    def __init__(self, parentInst: Any, **kwargs):
        # log.debug("Creating the Console Stack Object")
        self._CONSOLESTACK_LOCK = RLock()
        self.consoleStack = kwargs.get('consoleStack', [])

    def __iter__(self):
        if self.consoleStack:
            for item in self.consoleStack:
                yield item

    def printStack(self) -> str:
        """ This returns a string. It is a nicely formatted list of the history of console changes on the Environment"""

        output = ""
        for item in self.consoleStack:
            if not item or len(item) < 4:
                continue
            typeStr = self.__INVERTED_TYPE_DICT__.get(item[0])
            output += f'{typeStr}: {item[1]} Using Command: {item[2]} AdditionalInput: {item[3]}\n'
        return output

    def push(self, item: Union[tuple, str], name: Optional[str] = None, escalationType: Optional[int] = None,
             additionalInput: Optional[str] = None) -> bool:
        """ Append a new change to the console. This is to record a change to the environment.

        :param item: (either tuple or str)
        :param name: (str)
        :param escalationType: (int) This should either be (__USER_ESCALATION__) 1, (__CONSOLE_ESCALATION__) 2,
         (__ENVIRONMENT_CHANGE__) 3 or (__UNKNOWN__) 4.
        :param additionalInput: (str) Optional additional information for example a password.
        :return: (bool)
        """

        def _parsePushInput(_item, _name, _escalationType, _additionalInput):
            if type(_item) is not tuple and (type(_escalationType) is int or type(_escalationType) is str):
                if type(_escalationType) is str:
                    _escalationType = self.__TYPE_DICT__.get(_escalationType) or 4
                elif abs(_escalationType) > 4 or _escalationType <= 0:
                    _escalationType = 4
                return _escalationType, _name, _item, _additionalInput
            if type(_item) is tuple and len(_item) == 4 and type(_item[0] is int):
                return _item
            if type(_item) is str or type(_item) is dict and _escalationType is None:
                return self.__USER_ESCALATION__, _name, _item, _additionalInput
            return False

        command = _parsePushInput(item, name, escalationType, additionalInput)

        if command is False:
            return False
        self.consoleStack.append(command)
        return True

    def pull(self) -> tuple:
        """ This pulls from the consoleStack removing the item and returning it.

        :return: (tuple) The escalation information formated as a tuple
        """

        if len(self.consoleStack) >= 1:
            return self.consoleStack.pop()
        return tuple()

    def peak(self) -> tuple:
        """ Just like a peak it simply returns the last console change without removing it. """

        if self.consoleStack:
            return self.consoleStack[-1]

    def peer(self, num) -> tuple:
        """ Just like a peer for a stack this allows one to look at an particular index of the stack. """

        try:
            return self.consoleStack[num]
        except:
            return ()

    def getPreviousEscalation(self) -> tuple:
        return self.peak()

    def getPreviousEscalationType(self) -> int:
        return self.peak()[0]

    def getUserList(self) -> list:
        """ This returns a list of users that are currently logged into this environment in order of there login. """

        def _filterUsers(item):
            return self.__USER_ESCALATION__ == item[0]

        def _userGenerator(itemListToGen):
            output = []
            for item in itemListToGen:
                output.append(item[1])
            return output

        if not self.consoleStack:
            return []

        # itemList = list(filter(_filterUsers, self.consoleStack))
        return _userGenerator(filter(_filterUsers, self.consoleStack))

    def getCurrentUser(self) -> str:
        """ Returns a string that is the name of the current user authenticated on this environment. """

        currentUsers = self.getUserList()
        if currentUsers:
            return currentUsers[-1]
        return ''

    def getConsoleList(self) -> list:
        """ LIke 'getUserList' but returns a list of the console escalations in order that they happened. """

        def _filterConsoles(item):
            return self.__CONSOLE_ESCALATION__ == item[0]

        def _consoleGenerator(itemListToGen):
            output = []
            for item in itemListToGen:
                output.append(item[1])
            return output

        # itemList = list(filter(_filterConsoles, self.consoleStack))
        return _consoleGenerator(filter(_filterConsoles, self.consoleStack))

    def getCurrentConsole(self) -> str:
        """ Like 'getCurrentUser' but gets what the current console type is. """

        consoles = self.getConsoleList()
        if consoles:
            return consoles[-1]
        return "BASH"

    def getPasswordFor(self, name: str) -> str:
        """ Gets the current recorded password for the user specified by the 'name' parameter.

        :param name: (str) the name of the user that you are getting a password for.
        :return: (str)
        """

        def _filterUserByName(x):
            return name.lower() in str(x[1]).lower()

        for item in filter(_filterUserByName, self.consoleStack):
            if item[-1] is not None:
                return item[-1]
        return ""

    def resetEnvironment(self) -> None:
        """ Resets the environment console stack """

        numOfPulls = 0
        for item in reversed(self.consoleStack):
            if item[0] == self.__USER_ESCALATION__ or item[0] == self.__CONSOLE_ESCALATION__:
                break
            numOfPulls += 1
        for x in range(numOfPulls):
            self.consoleStack.pop()

    @property
    def console(self):
        return self.getCurrentConsole()

    @property
    def userCount(self):
        return len(self.getUserList())

    @property
    def consoleStack(self):
        try:
            with self._CONSOLESTACK_LOCK:
                return self._consoleStack
        except RuntimeError:
            pass

    @consoleStack.setter
    def consoleStack(self, value):
        try:
            with self._CONSOLESTACK_LOCK:
                self._consoleStack = value
        except RuntimeError:
            pass

    @consoleStack.deleter
    def consoleStack(self):
        if self._consoleStack:
            del self._consoleStack

    @property
    def numEscalations(self):
        def _filterUsers(item):
            return self.__USER_ESCALATION__ == item[0] or self.__CONSOLE_ESCALATION__ == item[0]
        if not self.consoleStack:
            return 0
        return len(list(filter(_filterUsers, self.consoleStack)))

    @property
    def numUsers(self):
        return len(self.getUserList())

    @property
    def userList(self):
        return self.getUserList()

    @property
    def whoami(self):
        return self.getCurrentUser()


# noinspection PyMissingConstructor,PyUnusedLocal
class EnvironmentControls(sshEnvironment):
    """ This is meant to be an easy access to the methods within the sshEnvironmentControl class. There that class
        can handle any ssh Environment/Paramiko ssh Channel this wraps a single Channel and when calling the methods
        within this class it uses the methods of the same name within its sshParent (an instance of
        sshEnvironmentControl) and passes itself as the environment to be acted on. This also adds locks for thread
        safe actions and is designed to work along side a Command Container.
    """

    _LOCK: RLock = None
    dead: bool = None
    sshChannel: Channel = None
    sshParent: Any = None
    _label: str = None
    active: bool = None
    command: Optional[str] = None
    _commandObject: Any = None
    timeout: Optional[Union[int, float]] = None
    kwargs: Optional[dict] = {}
    customChannel: bool = None

    def __new__(cls, parentInst: Any, **kwargs):
        parentInst.__class__ = EnvironmentControls
        return parentInst

    def __init__(self, parentInst: Any, **kwargs):
        """ Creates the EnvironmentControls object. Read more about the class in the class comments above.

        - :param sshParent: This is a sshThreader object. The sshThread class passes itself to the container.
        - :param label: This is a string identifying this channel. This is unnecessary as we already had a UUID. However
            the label need not be uniq which can lead to some interesting combinations. Such as two "MySQL" channels.
            The search can look for MySQL instead of a specific UUID. It doesn't matter which one it finds.
        - :return:
        """

        self.dead = False
        self.active = False
        self._label = kwargs.get('label', '')
        self.customChannel = kwargs.get('customChannel', True if self._label else False)
        self._LOCK = RLock()
        self.sshParent = kwargs.get('sshParent')
        if kwargs.get('autoConnect', False):
            self.sshParent.createConn()

    def __enter__(self):
        if not self._LOCK.acquire():
            raise RuntimeError(f"Channel ID: {self.EnvironmentID} The Lock failed within the time frame: 60")
        if not self.sshParent.checkConnection(self):
            raise SSHExceptionConn("Connection closed!")
        self.active = True
        return self

    # noinspection PyProtectedMember
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self._LOCK.release()
        except RuntimeError as e:
            log.debug(f"An RuntimeError occurred while attempting to release lock: {e}")
        except Exception as e:
            log.debug(f"An unknown error occurred while releasing the lock: {e}")
        finally:
            if not self.checkConnection():
                log.debug("About to disconnect channel because checkConnection returned False")
                self.disconnectEnvironment()
            if not self._LOCK._is_owned():
                self.active = False
                del self.commandObject

    def __hash__(self):
        return hash(self.EnvironmentID)

    def executeOnEnvironment(self, *args, **kwargs) -> AnyStr:
        """ Takes the param command is passes it to executeOnEnvironment function in 'sshCommand' class with the
            environment and prompt variables as well.

        - :return:
        """

        kwargs.pop('environment', None)
        return self.sshParent.executeOnEnvironment(self, *args, **kwargs)

    def escalate(self, *args, **kwargs) -> Union[sshEnvironment, bool]:
        """ Wrapper for the escalate method on the sshEnvironmentControl """
        kwargs.update({'environment': self})
        return self.sshParent.escalate(*args, **kwargs)

    def becomeRoot(self, *args, **kwargs) -> bool:
        """ This is specific logic just for handling becoming the root user. This hopefully will be deprecated once
            sshUserControl becomes more thread friendly.

        - :return: bool: True if successful or already root, false if it didn't even try.
        """

        kwargs.update({'environment': self})
        return self.sshParent.becomeRoot(*args, **kwargs)

    def becomeUser(self, *args, **kwargs) -> Union[sshEnvironment, bool]:
        """ Wrapper for the becomeUser method on the sshEnvironmentControl """

        kwargs.update({'environment': self})
        return self.sshParent.becomeUser(*args, **kwargs)

    def consoleEscalation(self, *args, **kwargs) -> Union[sshEnvironment, bool]:
        """ Wrapper for the consoleEscalation method on the sshEnvironmentControl """

        kwargs.update({'environment': self})
        return self.sshParent.consoleEscalation(*args, **kwargs)

    def environmentChange(self, *args, **kwargs) -> Union[sshEnvironment, bool]:
        """ Wrapper for the environmentChange method on the sshEnvironmentControl """

        kwargs.update({'environment': self})
        return self.sshParent.environmentChange(*args, **kwargs)

    def getPrompt(self, reCapturePrompt: bool = False) -> Optional[str]:
        """ Wrapper for the getPrompt method on the sshEnvironmentControl """

        return self.sshParent.getPrompt(self, reCapturePrompt=reCapturePrompt)

    def isPromptDefault(self, reCapturePrompt: bool = False) -> bool:
        """ Uses getPrompt and attempts to determine if prompt is the default bash prompt ie: bash-5.1$ """

        return self._defaultPromptCompileReg.search(self.getPrompt(reCapturePrompt)) is not None

    def checkConnection(self) -> bool:
        """ Wrapper for the checkConnection method on the sshEnvironmentControl """

        if not self.sshParent.checkConnection(self):
            self.dead = True
            return False
        return True

    def disconnectEnvironment(self, *args, **kwargs) -> bool:
        """ This attempts to log out of the channel gracefully exiting the terminal connection. This should normally be
            called inside of a thread although it doesn't matter. This also reduces 'channelCount' variable by one.

        - :param args: This is simply a place holder to satisfy the '_Worker' class from the ThreadPool.
        - :param kwargs: This is simply a place holder to satisfy the '_Worker' class from the ThreadPool.
        - :return: (bool) False if it is already disconnected True for everything else
        """

        with self._LOCK:
            if not self.checkConnection():
                return False
            try:
                self.sshParent.disconnect(environment=self)
            except SSHExceptionConn:
                log.debug("Failed to complete logout correctly! This could because of a corrupt userList!")
            except Exception as e:
                log.error(f"error in disconnectEnvironment: {e}")
                log.debug(f"[DEBUG] for disconnectEnvironment: {traceback.format_exc()}")
            finally:
                self.dead = True
                self.sshParent.removeEnvironment(self)
        return True

    def logoutCurrentUser(self) -> None:
        """ Wrapper for the logoutCurrentUser method on the sshEnvironmentControl """

        self.sshParent.logoutCurrentUser(environment=self)

    def logoutConsole(self, *args, **kwargs) -> bool:
        """ A override method for logoutConsole on the sshEnvironmentControl class """

        kwargs.update({'environment': self})
        return self.sshParent.logoutConsole(*args, **kwargs)

    # noinspection PyProtectedMember
    def _becomePreviousUser(self, *args, **kwargs) -> sshEnvironment:
        """ De-escalates the current user in a provided channel """

        kwargs.update({'environment': self})
        return self.sshParent._becomePreviousUser(*args, **kwargs)

    @property
    def isClosed(self):
        return self.dead or not self.sshParent.checkConnection(sshChannel=self)

    @property
    def commandObject(self):
        return self._commandObject

    @commandObject.setter
    def commandObject(self, value):
        self.command = value.command
        self.timeout = value.timeout
        self.kwargs = value.kwargs

    @commandObject.deleter
    def commandObject(self):
        self._commandObject = None
        self.timeout = None
        self.kwargs = None

    @property
    def userName(self):
        return self.whoami

    @property
    def EnvironmentID(self):
        return self._id

    @property
    def label(self):
        if self.__MAIN__:
            return "MAIN"
        return self._label

    @label.setter
    def label(self, value):
        if not self.__MAIN__ == "MAIN" or str(value) == "MAIN":
            self._label = str(value)
