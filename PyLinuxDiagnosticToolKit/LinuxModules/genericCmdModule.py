#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Ryan Henrichson, Timothy Nodine

# Version: 2.0
# Date: 06/17/17
# Description: This is the foundation for all Command Modules. It is a set of classes that are inherited by all
# CommandModules


import logging
from functools import partial
from copy import copy, deepcopy
from LinuxModules import CommandContainers
from typing import Any, Optional, Union, Hashable, Callable


log = logging.getLogger('GenericCommandModule')


def executionDecorator(func):
    def runResultsValue(bindingObject, *args, **kwargs):
        exeResults = func(bindingObject, *args, **kwargs)
        if exeResults and getattr(bindingObject, 'returnValueType', None):
            return bindingObject.returnValueType(exeResults)
        return exeResults
    return runResultsValue


# noinspection PyBroadException
class CommandModuleSettings(object):
    """
        A list of variables that represent the settings of a Command Module and their default values.
        Also a collection of properties used for accessing and manipulating those settings.
    """

    tki = None
    useDefaultParsing = __useDefaultParsing = None
    returnValueType = __returnValueType = None
    __ignoreAlias = None
    __requireFlags = None

    defaultCmd: str = ""
    defaultKey: str = ""
    defaultFlags: str = ""
    defaultKwargs: dict = {}
    defaultWait: int = 120

    def __init__(self, *args, **kwargs):
        try:
            super(CommandModuleSettings, self).__init__(*args, **kwargs)
        except Exception:
            super(CommandModuleSettings, self).__init__()

    def doesCommandExistPreParser(self, *args, **kwargs) -> Optional[bool]:
        return self.tki.modules.which.doesCommandExist(kwargs.get('executable',
                                                                  getattr(kwargs.get("this"), 'command', '')
                                                                  .strip().split()[0]))

    @property
    def _useDefaultParsing(self) -> Optional[bool]:
        return self.__useDefaultParsing

    @_useDefaultParsing.setter
    def _useDefaultParsing(self, value):
        if value not in (True, False, None):
            raise AttributeError('Default parsing must have a boolean value or None')
        self.__useDefaultParsing = value

    @_useDefaultParsing.deleter
    def _useDefaultParsing(self):
        self.__useDefaultParsing = self.useDefaultParsing = None

    @property
    def _returnValueType(self) -> Optional[bool]:
        return self.__returnValueType

    @_returnValueType.setter
    def _returnValueType(self, value):
        if value not in (str, None):
            raise AttributeError('%s is not a supported return value type' % value)
        self.__returnValueType = self.returnValueType = value

    @_returnValueType.deleter
    def _returnValueType(self):
        self.__returnValueType = None

    @property
    def ignoreAlias(self) -> Optional[bool]:
        return self.__ignoreAlias

    @ignoreAlias.setter
    def ignoreAlias(self, value):
        if value not in (True, False, None):
            raise AttributeError('Alias selection must have a boolean value or None')
        self.__ignoreAlias = value

    @ignoreAlias.deleter
    def ignoreAlias(self):
        self.__ignoreAlias = None

    @property
    def requireFlags(self) -> Optional[bool]:
        return self.__requireFlags

    @requireFlags.setter
    def requireFlags(self, value):
        if value not in (True, False, None):
            raise AttributeError('Requiring flags must have a boolean value or None')
        self.__requireFlags = value

    @requireFlags.deleter
    def requireFlags(self):
        self.__requireFlags = None


# noinspection PyProtectedMember,PyUnusedLocal,PyBroadException
class GenericCmdModule(CommandModuleSettings, object):
    """
        This class is inherited by all Command Modules. This is has a collection of helper functions including
        'simpleExecute'. 'simpleExecute' is the most important method in this class as it how most commands get
        executed. It handles creating and binding CommandContainer objects as well as caching commands. It is always
        where certain parameters like 'rerun' are used.
    """

    def __init__(self, tki, *args, **kwargs):
        super(GenericCmdModule, self).__init__(*args, **kwargs)
        self.tki = tki
        self._useDefaultParsing = self.useDefaultParsing
        self._returnValueType = self.returnValueType

    def __call__(self, *args, **kwargs) -> Any:
        if kwargs.get('wait') is not False:
            kwargs.update({'wait': kwargs.pop('wait', self.defaultWait) or self.defaultWait})
        return self.run(*args, **kwargs)

    def run(self, flags: Any = None, *args, **kwargs) -> Any:
        """ This method is often overridden by different command modules to follow particular behavior. This is the
            default behavior that expected. It attempts to use the 'defaultCmd', 'defaultKey' and 'defaultFlags' to
            create the command and run it. For example with the 'cat' module one could simply run cat.run('/etc/hosts')
            or because of the '__call__' magic method: cat('/etc/hosts').

        - :param flags: Usually a dictionary or a string. This is suppose to follow the 'defaultCmd'.
        - :param args: (Passed to simpleExecute and possibly too CommandContainer)
        - :param kwargs: (Passed to simpleExecute and possibly too CommandContainer)
        - :return: This could be a CommandContainer or the results of the command depending on if the command has
            has finished.
        """

        if isinstance(flags, dict):
            return self.simpleExecute(command=flags, **kwargs)
        if flags is None and self.requireFlags:
            raise Exception("The parameter 'flags' is required.")
        if flags is None:
            newCmd = self.defaultCmd + self.defaultFlags
        elif '%s' in self.defaultFlags:
            newCmd = self.defaultCmd + self.defaultFlags % flags
        else:
            newCmd = self.defaultCmd + flags
        newKey = self.defaultKey
        if '%s' in newKey:
            newKey %= flags
        if not newKey:
            newKey = flags
        if 'postparser' in self.defaultFlags:
            if kwargs.get('useDefaultParsing') or (self.useDefaultParsing and 'useDefaultParsing' not in kwargs):
                kwargs.update(self.updatekwargs('postparser', self.defaultKwargs.get('postparser'), **kwargs))
        return self.simpleExecute(command={newKey: newCmd}, **self.mergeKwargs(kwargs, self.defaultKwargs))

    def _verifyNeedForRun(self, **kwargs) -> None:
        """ This is a helper method that can be used to see if the CommandModule needs to be ran again. It checks
            with a 'if not self' first which is useful if the CommandModule has inherited the BashParser class. It then
            checks to see if the 'rerun' parameter was passed True. If it determines that it needs to run again then
            it runs 'self(**kwargs)'.

        - :param kwargs: Passed to the '__call__' magic method if the CommandModule needs to be ran again.
        - :return: None
        """
        if not self or kwargs.get('rerun', False):
            self(**kwargs)

    def simpleExecute(self, command: Union[str, dict], *args, **kwargs) -> Any:
        """ This is a wrapper for the simpleExecutor static method. This method simply injects self as the binding
            object parameter for simpleExecutor.
            NOTE: If you execute a command with the flag 'threading=True' and then execute the command with the flag
            'threading=False' the results will come back as 'None' unless you place a wait in it.

        - :param command: String or dictionary that is passed to simpleExecutor.
        """

        if not self.tki:
            return False
        kwargs = GenericCmdModule.mergeKwargs(kwargs, {'ignoreAlias': self.ignoreAlias, 'tki': self.tki})
        return GenericCmdModule.simpleExecutor(self, command, *args, **kwargs)

    @staticmethod
    @executionDecorator
    def simpleExecutor(bindingObject: Any, command: Union[str, dict], commandKey: Optional[str] = None,
                       rerun: bool = False, wait=0, **kwargs) -> Any:
        """  Run a single command and create the command container object  """
        log.info(f'Using simpleExecutor for command: {command}, '
                 f'commandKey = {commandKey}, rerun = {rerun}, wait = {wait}')
        tki = kwargs.get('tki')
        if bindingObject is None or not tki:
            return False
        wait = GenericCmdModule._waitCheck(wait)
        commandKey = GenericCmdModule.cmdObjBinder(command, commandKey, bindingObject, rerun, **kwargs)
        if type(commandKey) is not str:
            tki.execute(commandKey, **kwargs)
            return GenericCmdModule._waitHelper(commandKey, wait)
        event = kwargs.get('event', None) or None
        if getattr(bindingObject, commandKey, CommandContainers.CommandContainer).complete:
            if event and not getattr(bindingObject, commandKey, CommandContainers.CommandContainer).hasEvent(event):
                event.set()
            if wait is False:
                return getattr(bindingObject, commandKey, CommandContainers.CommandContainer)
            return getattr(bindingObject, commandKey, CommandContainers.CommandContainer).results
        if event and hasattr(bindingObject, commandKey):
            getattr(bindingObject, commandKey, CommandContainers.CommandContainer).addEvent(event)
        return GenericCmdModule._waitHelper(
            getattr(bindingObject, commandKey, CommandContainers.CommandContainer), wait)

    @staticmethod
    def cmdObjBinder(command, commandKey=None, bindTo=None, rerun=False, **kwargs) \
            -> Union[str, CommandContainers.CommandContainer]:
        commandKey = CommandContainers.CommandContainer._parseCommandInput(command, commandKey)
        if bindTo is not None and (rerun or not hasattr(bindTo, commandKey)):
            if isinstance(command, CommandContainers.CommandContainer):
                setattr(bindTo, commandKey, command)
            else:
                setattr(bindTo, commandKey, CommandContainers.CommandContainer(command=command, commandKey=commandKey,
                                                                               **kwargs))
            return getattr(bindTo, commandKey)
        return commandKey

    @staticmethod
    def buildFuncWithArgs(func: Callable, *args, **kwargs) -> partial:
        """ build a functool partial object with the func variable as the callable function """
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        return partial(func, *args, **kwargs)

    @staticmethod
    def sanitizeFilename(filename: str) -> str:
        """ A wrapper for the 'CommandContainers.CommandContainer._parseCommandInput' staticmethod  """
        return CommandContainers.CommandContainer._parseCommandInput(filename)

    # noinspection PyMethodMayBeStatic
    def _formatOutput(self, output=None):
        """ This is a stand in method """
        return output

    # noinspection PyUnusedLocal
    @staticmethod
    def _formatExitCode(results: str, this: CommandContainers.CommandContainer, *args, **kwargs) -> bool:
        """ Use for simpleExecute or command modules to evaluate the exit status of the command ($command; echo $?)"""
        try:
            if results[-1:] == '0':
                return True
            this.rawResults = results[:-2]  # remove the newline too
        except Exception:
            this.rawResults = results
        return False

    @staticmethod
    def _formatExitCodeStr(results: str, this: CommandContainers.CommandContainer, *args, **kwargs) -> str:
        """ Use for simpleExecute or command modules to return only the exit status of the command (echo $?) """
        if GenericCmdModule._formatExitCode(results, this, *args, **kwargs):
            return results[:-2]  # remove the newline too
        return ""

    @staticmethod
    def _waitHelper(cmdObj: Optional[CommandContainers.CommandContainer] = None, wait: Union[int, float] = 0) -> Any:
        """ Used exclusively by the 'simpleExecutor' staticmethod """
        if wait is False:
            return cmdObj
        return cmdObj.waitForResults(wait=GenericCmdModule._waitCheck(wait))

    @staticmethod
    def _waitCheck(wait: Union[int, float] = 0) -> Optional[Union[int, float]]:
        """ Used exclusively by the 'simpleExecutor' staticmethod """
        if not isinstance(wait, (int, float)) or wait < 0:
            if wait is True:
                return None
            return 0
        return wait

    @staticmethod
    def mergeKwargs(parameterKwarg: dict, defaultKwarg: dict) -> dict:
        """ merge kwargs with parameterKwarg taking priority over defaultKwarg """
        return {**defaultKwarg, **parameterKwarg}

    @staticmethod
    def updatekwargs(addToArg: Optional[Hashable] = None, addThese: Any = None,
                     _forceFirst: bool = False, **kwargs) -> dict:
        """
            This returns a dict that can be used to update kwargs. Only use if the value of the kwarg you want to update
            is a string, list, or dict. If a dict is passed this will assume that the value of the kwargs to update is
            also a dict
        """

        if addToArg not in kwargs:
            return {addToArg: addThese}

        # copy to prevent updating pieces of the structure passed in such as lists and dicts
        try:
            newKwarg = copy(kwargs.get(addToArg))  # regular stuff, classes and instances
        except Exception:
            try:
                newKwarg = deepcopy(kwargs.get(addToArg))  # instance methods and such
            except Exception:
                newKwarg = kwargs.get(addToArg)  # copying is not thread safe
        kwargs.pop(addToArg)  # remove it

        if isinstance(addThese, dict):
            for addKey, addValue in addThese.items():
                newKwarg[addKey] = addValue  # maintain the order if required
            return {addToArg: newKwarg}

        if not type(addThese) is list:
            addThese = [addThese]
        if not type(newKwarg) is list:
            newKwarg = [newKwarg]
        for addThis in addThese:
            if _forceFirst:
                newKwarg.insert(0, addThis)
            else:
                newKwarg.append(addThis)
        return {addToArg: newKwarg}
