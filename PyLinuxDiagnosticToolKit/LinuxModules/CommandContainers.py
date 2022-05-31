#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Ryan Henrichson, Timothy Nodine

# Version: 1.1.0
# Description: This is an object that contains/wraps a single command or other CommandContainers too support multiple
# commands. It is designed to be thread safe and has many helper functions designed to assist in working with commands
# in a threaded/network environment. It is highly customizable allowing for both a simple single command or to be part
# of a batch or queue. It also provides the ability for custom pre/post tasks which are functions to run specifically
# when failures are detected and tasks to run when commands complete.
# For more information review the README file found in the same directory as this.


from __future__ import annotations


import logging
import re
import traceback
import time
import uuid
from collections import OrderedDict  # TODO remove OrderedDict
from threading import RLock, Event
from functools import partial
from sshConnector.sshLibs.sshChannelEnvironment import EnvironmentControls
from PyLinuxDiagnosticToolKit.libs.LDTKExceptions import SSHExceptionConn, RequirementsException, PreparserException, \
    ExecutionException, PostParserException, SetFailureException, CompletionTaskException, TimeoutException, \
    DataFormatException, ForceCompleteException, BetweenBitException, TimeToFirstBitException
from PyMultiTasking import safe_acquire, safe_release, method_wait, MultiEvent, PriorityTaskQueue, Task
from PyMultiTasking.ThreadingUtils import ThreadPool as Pool
from LinuxModules import genericCmdModule
from typing import Any, Optional, Union, Hashable, Iterable, List, Callable


# logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(message)s',
#                     level=logging.INFO)
log = logging.getLogger('CommandContainers')

# Regex's used to pull command tags.
# ensure that data was returned
matchRe = re.compile(r'(?<=^CMDSTART).+', flags=re.MULTILINE | re.DOTALL)
# clean up any errors or other data that may appear before the start tag
startSubRe = re.compile(r'.*?(?=^CMDSTART)', flags=re.MULTILINE | re.DOTALL)
# clean up all data after the end tag
endSubRe = re.compile(r'CMDEND.*', flags=re.MULTILINE | re.DOTALL)
#Unparse the command string
unParseCmd = re.compile(r'echo CMDSTART &&(.*)&& echo CMDEND')


class CommandData(object):
    """
        This is where all the data associated with the Command is located.
    """

    _results: Any = None
    _lastResults: Any = None
    failure = None
    complete: bool = False
    running: bool = False
    parsed: bool = False
    noParsing: Union[None, bool] = None
    children: Any = None
    parent: Any = None
    events: list = None
    timeout: Union[int, float] = None
    __PRIORITY__: int = 10
    __OBJECTLOCK__: RLock = None
    kwargs: dict = {}
    args: tuple = ()
    EnvironmentObject: Optional[EnvironmentControls] = None
    _EnvironmentObjectBackup: Optional[EnvironmentControls] = None
    root: bool = None
    tki = None
    _tkiBackup = None
    _event: MultiEvent = None
    _completionEvent: Event = None
    _stopOnFailure: bool = None
    _timeoutExceptions: bool = None
    rawResults: str = None

    def __init__(self, timeout: Union[int, float] = 300, root: bool = None, event: Optional[MultiEvent] = None,
                 noParsing: Optional[bool] = None, stopOnFailure: Optional[bool] = None,
                 timeoutExceptions: Optional[Exception] = None, *args, **kwargs):
        """ The bottom level parent. All other classes inherit this class down the chain.

        - :param timeout: This is the global timeout for encompassing all actions taken on or in this CommandObject.
        - :param root: This determines if root is required to run this command.
        - :param event: This provides a pre-existing event that will be set once the CommandObject is complete.
        - :param noParsing: do not parse results using the default methods
        - :param stopOnFailure: stop queue or unthreaded execution, or prevent completion tasks if an error occurs
        - :param timeoutExceptions: return an exception instead of None if something times out
        - :return:
        """

        self.timeout = timeout or kwargs.get('runTimeout') or kwargs.get('wait') or 300
        if not type(self.timeout) in (int, float):
            self.timeout = 300
        self.__OBJECTLOCK__ = RLock()
        self.__LASTRESULTSLOCK__ = RLock()
        self.args = args
        self.kwargs = kwargs
        self.noParsing = noParsing is True
        self._stopOnFailure = stopOnFailure is True
        self._timeoutExceptions = timeoutExceptions is True
        if not self.tki:
            self.tki = self._tkiBackup = kwargs.get('tki', {})
        if root is None:
            root = getattr(getattr(self.tki, 'arguments', None), 'root', False)
        self.root = root
        self.children = []
        self.parent = None
        if 'runTimeout' not in self.kwargs:
            self.kwargs['runTimeout'] = self.timeout
        self._event = MultiEvent()
        self._completionEvent = Event()
        self._completionEvent.set()
        if event is None:
            event = Event()
        if self.events is None:
            self.events = []
        self.addEvent(event)

    def addEvent(self, event: MultiEvent) -> None:
        """ This will add a new event if it does not already have it.

        - :param event: (MultiEvent)
        """

        if not isinstance(event, Event):
            raise TypeError('event parement is not an Event')
        if not self.hasEvent(event):
            self.events.append(event)

    def hasEvent(self, event: MultiEvent) -> bool:
        """ This checks to see if the specified event exists or not. This is mainly used by 'addEvent' method.

        - :param event:
        - :return: bool
        """

        if self.events and event in self.events:
            return True
        return False

    def forceComplete(self, results: Optional[Any] = None) -> ForceCompleteException:
        """ Force completion for the parent container and all children without changing the results.
            Utility method to be used on a fully initialized command container.
        """

        log.info(f'Forcing completion for command object: {self}')
        if self.children:
            for child in self.children:
                log.info(f'Parent forcing completion of child: {self} : {child}')
                child.forceComplete(results)
        self._completionEvent.set()
        self._event.set()
        self._setEvents()
        self.failure = True
        self.parsed = True
        self.running = False
        self.complete = True
        self._tkiBackup = self.tki
        self.tki = None
        self._EnvironmentObjectBackup = self.EnvironmentObject
        self.EnvironmentObject = None
        return ForceCompleteException(results, baseException=results)

    # noinspection PyUnresolvedReferences
    def resetContainers(self) -> None:
        """ Reset the command containers to a usable state wth all previous settings.
            Utility method to be used on a fully initialized command container.
        """

        log.info(f'Resetting command object: {self}')
        if self.children:
            for child in self.children:
                log.info(f'Parent resetting child: {self} : {child}')
                child.resetContainers()
        self._completionEvent.clear()
        self._event.clear()
        self.results = None
        self.failure = None
        self.parsed = False
        self.running = False
        self.complete = False
        self.tki = self._tkiBackup
        self.EnvironmentObject = self._EnvironmentObjectBackup
        try:
            self.setRequirementsFailureCondition(self.requirementsFailureCondition)
        except:
            pass

    def handleChildren(self, tki: Optional[Any] = None) -> None:
        """ This function is called once the CommandObject is done setting up children if it has any.
            It makes sure the children are aware of it as the parent and of tki of the parent.
        """

        if not self.children:
            return
        self._event = MultiEvent(len(self.children))
        for child in self.children:
            child.addEvent(self._event)
            child.parent = self
            if tki:
                child.tki = tki
            child.handleChildren(tki=tki or self.tki)

    def _setEvents(self) -> None:
        """ This transverses the list of events known to this object and sets them. """

        for item in self.events:
            item.set()

    @staticmethod
    def _isKwargs(item: dict) -> bool:
        """ This is a helper function for _parseCommand.
            It checks to see if the dictionary type object is a command or multiple commands.
        """

        return 'command' in item

    @staticmethod
    def _hasKwargs(item: dict) -> list:
        """ This is a helper function for _parseCommand.
            It checks to see if the parent dictionary type object has custom functions.
        """

        return [c for c in ['requirements', 'preparser', 'postparser', 'completiontask'] if c in item]

    @staticmethod
    def _needsKwargs(item: dict) -> bool:
        """ This is a helper function for _parseCommand.
            It checks to see if the parent dictionary type object needs updating to be suitable for use as kwargs.
        """

        return CommandData._hasKwargs(item) or (not CommandData._isKwargs(item) and
                                                    len(item) - len(CommandData._hasKwargs(item)) == 1)

    @staticmethod
    def _injectCommandKey(item: dict, key: Hashable) -> dict:
        """
            This is a helper function for _processMultiItemIterable.
            It makes sure that commandKey is in kwargs because it is a requirement when creating a CommandObject.
        """

        if 'commandKey' not in item:
            item['commandKey'] = key
        return item

    @staticmethod
    def _isQue(item: Iterable) -> bool:
        """ This is a helper function for _parseCommand.
            Determines if the iterable datatype is a queue or a batch.

        - :return: bool: True if queue, False if batch
        """

        return isinstance(item, (OrderedDict, list, tuple))

    @staticmethod
    def _createTags(command: Optional[Any] = None, noParsing: bool = False, ignoreAlias: bool = False) \
            -> Union[DataFormatException, Union[dict, str]]:
        """ This is designed to add command tags to the beginning and end of a command.
            These tags help determine success and failure and also helps parse the output.
            The noParsing flag can stop this from being added.
            The idea here is that not all commands will run on bash.
        """

        if noParsing:
            if type(command) is dict and len(command) > 0:
                command = command.values().pop()
            if isinstance(command, str):
                return command
            return DataFormatException(f"The command is not formatted correctly: {command}")
        if isinstance(command, dict):
            for key, value in command.items():
                if not re.search('echo CMDSTART.*echo CMDEND', value, flags=re.DOTALL | re.MULTILINE):
                    if ignoreAlias:
                        value = "command " + value
                    command[key] = re.sub(r'(.+)', r'COLUMNS=200; export COLUMNS; echo CMDSTART && \1 && echo CMDEND',
                                          value, flags=re.DOTALL | re.MULTILINE)
            if len(command) == 1:
                return list(command.values()).pop()
            return command
        if not isinstance(command, str):
            return ''
        if not re.search('echo CMDSTART.*echo CMDEND', command, flags=re.DOTALL | re.MULTILINE):
            if ignoreAlias:
                command = "command " + command
            return re.sub(r'(.+)', r'COLUMNS=200; export COLUMNS; echo CMDSTART && \1 && echo CMDEND',
                          command, flags=re.DOTALL | re.MULTILINE)
        return command

    @property
    def results(self):
        try:
            with self.__OBJECTLOCK__:
                return self._results
        except RuntimeError as e:
            log.error(f'ERROR: for results property: {e}')
            log.debug(f'[DEBUG] for results property: {traceback.format_exc()}')

    @results.setter
    def results(self, value):
        try:
            with self.__OBJECTLOCK__:
                self._results = value
                self._event.set()
                self._setEvents()
        except RuntimeError as e:
            log.error(f'ERROR: for results.setter property: {e}')
            log.debug(f'[DEBUG] for results.setter property: {traceback.format_exc()}')

    @results.deleter
    def results(self):
        try:
            with self.__OBJECTLOCK__:
                self._results = None
        except RuntimeError as e:
            log.error(f'ERROR: for results.deleter property: {e}')
            log.debug(f'[DEBUG] for results.deleter property: {traceback.format_exc()}')

    @property
    def lastResults(self):
        try:
            with self.__LASTRESULTSLOCK__:
                return self._lastResults
        except RuntimeError as e:
            log.error(f'ERROR: for lastResults property: {e}')
            log.debug(f'[DEBUG] for lastResults property: {traceback.format_exc()}')

    @lastResults.setter
    def lastResults(self, value):
        try:
            with self.__LASTRESULTSLOCK__:
                self._lastResults = value
        except RuntimeError as e:
            log.error(f'ERROR: for lastResults.sette property: {e}')
            log.debug(f'[DEBUG] for lastResults.sette property: {traceback.format_exc()}')

    @lastResults.deleter
    def lastResults(self):
        try:
            with self.__LASTRESULTSLOCK__:
                self._lastResults = None
        except RuntimeError as e:
            log.error(f'ERROR: for lastResults.deleter property: {e}')
            log.debug(f'[DEBUG] for lastResults.deleter property: {traceback.format_exc()}')


class CommandParsers(CommandData):
    """ This is where all standard and custom parsing goes. """

    _command: Any = None
    _commandKey: str = None
    customPostParser: bool = False

    def __init__(self, command: Any, commandKey: Union[None, str], **kwargs):
        """ Parse the command and the commandKey that identifies the container.

        - :param command: The datatype of command depends on the behavior of the CommandObject.
                 If it is a string or a single length iterable, then the command becomes a string.
        - :param commandKey: The name of the command object.
                 This object might be bound to a class if created through the 'simpleExecute' method.
                 In that case, this is also the variable name that gets bound.
                 This also helps determine its __hash__ and __str__.
        """

        super(CommandParsers, self).__init__(**kwargs)
        if isinstance(command, dict) and CommandData._needsKwargs(command) and not commandKey:
            commandKey, command = self._findCmdAndKey(command)
        self.commandKey = (command, commandKey)
        # print(f'command/type = {command} / {type(command)}')
        self.commandRaw = self.command = command

    @staticmethod
    def _findCmdAndKey(command: dict) -> tuple:
        for cmdKey, cmd in command.items():
            if cmdKey not in ['requirements', 'preparser', 'postparser', 'completiontask', 'onFail']:
                return cmdKey, cmd

    @staticmethod
    def _parseCommandInput(command: Optional[Union[str, dict]] = None, commandKey: Optional[str] = None) -> str:
        """ Used by simpleExecute.
            Use it to retrieve a command object by name after using simpleExecute.

        - :param command: This can either be a str or a single item dict
        - :param commandKey:
        - :return: A tuple. First item is the key and the second item is the value
        """

        if not command and not commandKey:
            return CommandParsers._parseCmdObjKey(str(uuid.uuid1()))
        if isinstance(commandKey, str) or isinstance(command, str):
            return CommandParsers._parseCmdObjKey(command, commandKey)
        try:
            if commandKey is None:
                return CommandParsers._parseCmdObjKey(''.join(command))
        except:
            pass
        return CommandParsers._parseCmdObjKey(str(uuid.uuid1()))

    @staticmethod
    def _parseCmdObjKey(cmd: Optional[str] = None, cmdKey: Optional[str] = None) -> str:
        """ This static method is designed to parse the command key.
            The command key may be used as the name of this object if it is bound to another object.
            Namespaces have restrictions and cannot have certain characters.
            This static removes invalid characters.
            This is static so that it can be accessed outside of the class object
                allowing a programmer to use this anytime and ensure that the name is always the same.

        - :param cmd: The command variable from init
        - :param cmdKey: The commandkey variable from init
        - :return: str
        """

        def _replaceStringHelper(tmpStr):
            return tmpStr.replace('/', '').replace('-', '').replace('.', '').replace(',', '').replace(';', ''). \
                replace("'", '').replace('"', '').replace(' ', '')

        if not cmd and not cmdKey:
            return ''
        if not cmdKey:
            cmdKey = cmd
        elif '%s' in cmdKey and isinstance(cmd, str):
            return cmdKey % _replaceStringHelper(cmd)
        return _replaceStringHelper(cmdKey)

    @staticmethod
    def _parseCommand(command: Any, noParsing: bool = False, ignoreAlias: bool = False) -> Any:
        """
            This is an designed to parse the command variable from init.
            It determines if the command is a single command or a queue or batch of commands.
            This is based on the command datatype and structure.
        """
        # print(f'command/type: {command} / {type(command)}')
        if isinstance(command, str):
            return CommandData._createTags(command, noParsing, ignoreAlias)
        if len(command) == 1:
            return CommandParsers._processSingleItemIterable(command, noParsing, ignoreAlias)
        if isinstance(command, Iterable):
            if CommandData._isQue(command):
                return CommandParsers._processMultiItemIterable(command)
            return set(CommandParsers._processMultiItemIterable(command))

    @staticmethod
    def _processSingleItemIterable(command: Iterable, noParsing: bool, ignoreAlias: bool) -> str:
        """
            This is a helper function for '_parseCommand'.
            This is designed to handle an iterable that only has one command to run.
            The command is then run in this Object.
        """
        if isinstance(command, set) or isinstance(command, list):
            command = command.pop()
        elif isinstance(command, dict):
            command = list(command.values()).pop()
        elif isinstance(command, tuple):
            command = command[0]
        return CommandData._createTags(command, noParsing, ignoreAlias)

    @staticmethod
    def _processMultiItemIterable(command: Iterable) -> Any:
        """
            This is a helper function for '_parseCommand'.
            This is designed to handle an iterable that has multiple commands to run.
            It creates new CommandContainers for each 'command' that it iterates through.
        """

        children = []
        if isinstance(command, dict):
            for key, item in command.items():
                if CommandData._isKwargs(item):
                    item = CommandData._injectCommandKey(item, key)
                    children.append(CommandContainer(**item))
                else:
                    children.append(CommandContainer(item, key))
        else:
            for item in command:
                if isinstance(item, dict) and CommandData._isKwargs(item):
                    children.append(CommandContainer(**item))
                else:
                    children.append(CommandContainer(item, None))
        return children

    @staticmethod
    def _singleCommandParser(cmdResults: Union[Any, str]) -> str:
        """
            This is used specifically by _parseResults but also in all simple parsing functions.
            Parses only the output of a single command from a string.
        """

        if not isinstance(cmdResults, str):
            return cmdResults
        # compile these up front one time for better performance on repeated calls
        # all this parsing helps us handle custom prompts and other weirdness better
        cmdOutputRe = matchRe.search(startSubRe.sub('', cmdResults, count=1))
        if cmdOutputRe:
            output = endSubRe.sub('', cmdOutputRe.group(), count=1).strip()
            if not output:
                return ''
            return output
        return ''

    @property
    def command(self):
        try:
            with self.__OBJECTLOCK__:
                return self._command
        except RuntimeError as e:
            log.error(f'ERROR: for command property: {e}')
            log.debug(f'[DEBUG] for command property: {traceback.format_exc()}')

    @command.setter
    def command(self, value):
        """
            This makes sure that command is parsed and calls _handleChildren() to take care of any children.
        """
        try:
            with self.__OBJECTLOCK__:
                output = self._parseCommand(value, self.noParsing, self.kwargs.get('ignoreAlias', False))
                if type(output) is list or type(output) is set:
                    self._command = None
                    self.children = output
                    self.handleChildren(tki=self.tki)
                elif isinstance(output, str):
                    self._command = output
        except RuntimeError as e:
            log.error(f'ERROR: for command.setter property: {e}')
            log.debug(f'[DEBUG] for command.setter property: {traceback.format_exc()}')

    @command.deleter
    def command(self):
        try:
            with self.__OBJECTLOCK__:
                self._command = None
        except RuntimeError as e:
            log.error(f'ERROR: for command.deleter property: {e}')
            log.debug(f'[DEBUG] for command.deleter property: {traceback.format_exc()}')

    @property
    def commandUnparsed(self):
        command = self.command
        if '&&' in command and 'CMDSTART' in command:
            for cmd in unParseCmd.findall(command):
                return cmd
        return command

    @property
    def commandKey(self):
        return self._commandKey

    @commandKey.setter
    def commandKey(self, value):
        """
            This passes the value through _parseCommandInput() before applying the command key value.
            It requires that value be a tuple.
        :value: tuple
        """
        self._commandKey = self._parseCommandInput(*value)


class CommandRequirements(CommandParsers):
    """
        This class handles the Requirements for a Command. It parses the provided requirements and the runRequirements
        method it has is called when the Requirement phase starts. Which is at the start of the execution. Requirements
        can either be a list, dict, or callable object.
    """

    requirements: Any = None
    requirementTasks: list = None
    requirementFailureVar: dict = None
    requirementIncompleteVar: dict = None
    _requirementKeys: set = None
    _requirementResults: OrderedDict = None
    __REQUIREMENT_LOCK__: RLock = None

    def __init__(self, command: Any, commandKey: Optional[str], requirements: Optional[Any] = None, **kwargs):
        """
            This init's job is too setup the requirements and make sure that they are correctly formatted.
        :param command: passing thru to the next container
        :param commandKey: passing thru to the next container
        :param requirements: takes this which can either be list, dict, or callable
        :param kwargs: passed thru to the next container
        """
        self.__REQUIREMENT_LOCK__ = RLock()
        super(CommandRequirements, self).__init__(command, commandKey, **kwargs)
        if 'requirementsCondition' in kwargs:
            self.setRequirementsFailureCondition(kwargs.pop('requirementsCondition'))
        self.requirementFailureVar = {}
        self.requirementIncompleteVar = {}
        self._requirementKeys = set()
        if requirements is not None:
            self.requirements = requirements
        if self.requirements:
            self._parseRequirements()

    def runRequirements(self) -> Optional[Exception]:
        """
            This is the only public method. It is called when the CommandContainer is being executed.
        :return: The output of _detectRequirementFailure which is either an exception or None
        """
        if self.requirements:
            reqTasks = PriorityTaskQueue()
            for req in self.requirementTasks:
                reqTasks.put(Task(req))
            Pool(tasks=reqTasks, daemon=False, timeout=self.timeout)
            return self._detectRequirementFailure(self.requirementTasks)

    def _parseRequirements(self) -> Optional[Exception]:
        """ This is called by __init__ and its job is to setup the requirements and make it ready for execution.
        - :return: None. An exception is raised if there is an error.
        """

        try:
            if not self.requirements:
                return None
            requirements = self._parseRequirementsHelper(self.requirements)
            if type(requirements) is not list:
                requirements = [requirements]
            self.requirementTasks = requirements
            if len(self.requirementTasks) != len(self._requirementKeys):
                raise RequirementsException(f"The func keys for requirements does not match the number of "
                                            f"requirementTasks\nrequirementKeys: "
                                            f"{self._requirementKeys}\nrequirementTasks: {self.requirementTasks}")
            self.requirementResults = OrderedDict([])
        except Exception as e:
            log.error(f"ERROR: Requirements setup failed: \n{e}\n")
            log.debug(f"[DEBUG] for _parseRequirements: {traceback.format_exc()}")
            raise e

    def _parseRequirementsHelper(self, rawRequirements: Any) -> Union[Union[List[partial], partial], Exception]:
        """ This is the work horse of the __init__/_parseRequirements methods.
            This is a recursive method that attempts to parse requirements and turn them into callable partials
                for the _requirementRunner method to be used by the Pool.
        - :param rawRequirements: can either be a list, dict, or callable.
        - :return: This is either a partial a list of partials or an Exception
        """

        if type(rawRequirements) is list:
            return [self._parseRequirementsHelper(item) for item in rawRequirements]

        if callable(rawRequirements):
            self._requirementKeys.add(str(rawRequirements))
            if hasattr(self, 'requirementsFailureCondition'):
                self.requirementFailureVar.update({str(rawRequirements): self.requirementsFailureCondition})
            return partial(self._requirementRunner, str(rawRequirements), rawRequirements, 0.1, None, False)

        if 'failureVar' in rawRequirements:
            self.requirementFailureVar.update({rawRequirements['funcKey']: rawRequirements['failureVar']})
        elif hasattr(self, 'requirementsFailureCondition'):
            try:  # dict of any length
                self.requirementFailureVar.update(
                    {rawRequirements.get('funcKey', rawRequirements.keys()[0]): self.requirementsFailureCondition})
            except:  # callable object
                self.requirementFailureVar.update({str(rawRequirements): self.requirementsFailureCondition})

        if isinstance(rawRequirements, dict):
            if len(rawRequirements) == 1:
                funcKey = list(rawRequirements.keys())[0]
                self._requirementKeys.add(funcKey)
                return partial(self._requirementRunner, funcKey, rawRequirements[funcKey], 0.1, None, False)
            if len(rawRequirements) > 1:
                if 'funcKey' not in rawRequirements or 'func' not in rawRequirements:
                    raise RequirementsException("Invalid requirements format")
                self.requirementIncompleteVar.update(
                    {rawRequirements['funcKey']: rawRequirements.get('incompleteVar', None)})
                self._requirementKeys.add(rawRequirements['funcKey'])
                return partial(self._requirementRunner, **rawRequirements)
        raise RequirementsException("Invalid requirements format")

    def _requirementRunner(self, funcKey: str, func: Callable, delay: float = 0.1, incompleteVar: Any = None,
                           raiseExc: bool = False, *args, **kwargs) -> None:
        """ Created by the _parseRequirementsHelper method and passed to the Pool for threading.
            This takes the results of methodWait from Pool and stores the output in requirementResults.

        - :param funcKey: This is used as the key associated with the output for requirementResults.
        - :param func: The callable that will be passed to methodWait.
        - :param delay: How long in between runs
        - :param incompleteVar: The variable used to determine if the 'func' being called has finished
        - :param raiseExc: Tells methodWait whether or not to raise or return an exception if an exception occurs
        - :param args: passed to methodWait and then to the 'func'
        - :param kwargs: passed to methodWait and then to the 'func'. However it may container failureVar which is
                pulled from kwargs and used as a control for methodWait.
        - :return: None
        """

        kwargs.update({'this': self})
        self.requirementResults.update({funcKey: method_wait(func, timeout=self.timeout, delay=delay,
                                                             incompleteVar=incompleteVar, raiseExc=raiseExc,
                                                             *args, **kwargs)})

    def _detectRequirementFailure(self, requirements: Any) -> Optional[Exception]:
        """ This attempts to detect if there was a failure in the requirements.
            Checks to see if requirementResults exists.
            Then checks requirementResults for length against the original requirements.
            This can be different if an exception occurred and _requirementRunner did not update requirementResults.
            Lastly it checks all the results as follows:
                Results are an exception.
                Results are equal to incompleteVar (did not finish).
                Was failureVar provided and if do are results equal to it.
            All failures are collected into a single RequirementsException.

        - :param requirements: This is the requirementTasks which is a list of callables.
        - :return: None or Exception
        """

        if not self.requirementResults:
            log.error("ERROR: Requirements results are empty")
            return RequirementsException("Requirements results are empty")
        if isinstance(self.requirementResults, Exception):
            log.error(f"An Exception occurred within the requirements: {self.requirementResults}")
            return RequirementsException(self.requirementResults)
        if not isinstance(self.requirementResults, dict):
            log.error(self.requirementResults)
            return DataFormatException(f"The requirementsResults should be a dict but instead are "
                                       f"{type(self.requirementResults)}")
        if self.requirementResults and len(requirements) != len(self.requirementResults):
            missingReq = set.difference(self._requirementKeys, set(self.requirementResults.keys()))
            log.error(f"ERROR: Missing requirements results after execution: {missingReq}")
            return RequirementsException(f"Requirements did not complete: {missingReq}")
        if self.requirementResults:
            failedReqs = []
            for funcKey, results in self.requirementResults.items():
                failureVar = self.requirementFailureVar.get(funcKey, None)
                incompleteVar = self.requirementIncompleteVar.get(funcKey, None)
                if isinstance(results, Exception) or \
                        results is incompleteVar or \
                        funcKey in self.requirementFailureVar and results is failureVar:
                    failedReqs.append(funcKey)
            if failedReqs:
                return RequirementsException(f"Requirements failed: {', '.join(failedReqs)}")

    def setRequirementsFailureCondition(self, requirementsFailureCondition: Any) -> None:
        """ This will be checked against the results of the requirements to determine if a failure occurred.
            This MUST be set before running the command and executing the command object.
            To allow a default failure condition in addition to an exception to define requirements success or failure
                and allow None to be a valid success criteria, the attribute requirementsFailureCondition will not
                exist and the absence of the attribute will prevent anything other than an exception from being used.
            However, the current default value is None to allow for backward compatibility.

        - :param requirementsFailureCondition:
        - :return: None
        """

        self.requirementsFailureCondition = requirementsFailureCondition

    @property
    def requirementResults(self):
        """
            Wraps requirementResults with a lock.
        """
        try:
            with self.__REQUIREMENT_LOCK__:
                return self._requirementResults
        except RuntimeError as e:
            log.error(f'ERROR: for requirementResults property: {e}')
            log.debug(f'[DEBUG] for requirementResults property: {traceback.format_exc()}')

    @requirementResults.setter
    def requirementResults(self, value):
        try:
            with self.__REQUIREMENT_LOCK__:
                self._requirementResults = value
        except RuntimeError as e:
            log.error(f'ERROR: for requirementResults.setter property: {e}')
            log.debug(f'[DEBUG] for requirementResults.setter property: {traceback.format_exc()}')

    @requirementResults.deleter
    def requirementResults(self):
        try:
            with self.__REQUIREMENT_LOCK__:
                self._requirementResults = OrderedDict()
        except RuntimeError as e:
            log.error(f'ERROR: for requirementResults.deleter property: {e}')
            log.debug(f'[DEBUG] for requirementResults.deleter property: {traceback.format_exc()}')


# noinspection PyMethodMayBeStatic,PyUnusedLocal
class CommandSetup(CommandRequirements):
    """
        This is where the setup before running the command occurs.
        Requirements and the preparser are executed here.
        This also does the preliminary checking to ensure commands can be run.
    """

    def __init__(self, command: Any, commandKey: Optional[str], preparser: Optional[Callable] = None,
                 postparser: Optional[Callable] = None, onFail: Optional[Callable] = None,
                 completiontask: Optional[Callable] = None, **kwargs):
        super(CommandSetup, self).__init__(command, commandKey, **kwargs)
        if preparser is not None:
            self._preparser = preparser
        if postparser is not None:
            self._postparser = postparser
            self.customPostParser = True
        if onFail is not None:
            self._onFailure = onFail
        if completiontask is not None:
            self._completionEvent.clear()
            self._onComplete = completiontask
            self.customPostParser = True

    def _preparser(self, *args, **kwargs) -> Any:
        """ Placeholder for custom command preparser.
            All parsers MUST accept *args and **kwargs.
            Must return bool value or None (None means Failure).
        """
        return True

    def _postparser(self, results: Optional[str] = None, this: Optional[Any] = None, **kwargs) -> Any:
        """ Placeholder for custom command parser.
            All parsers MUST accept **kwargs.
            May be a single function or method or a list thereof.
            Must return results or None (None means Failure).
        """
        return results

    def _onFailure(self, results: Optional[str] = None, this: Optional[Any] = None, **kwargs) -> Any:
        """  Standard on fail method and a placeholder for a custom on fail method  """
        return results

    def _onComplete(self, results: Optional[str] = None, this: Optional[Any] = None, **kwargs) -> Any:
        """
            Placeholder for custom onComplete function.
            This is called by performComplete which is called by the exit magic function.
        :return: bool: True or False
        """
        return results

    def runCommandSetup(self, **kwargs) -> Optional[Exception]:
        """ Checks to make sure it is possible to run a command either via
            a EnvironmentObject or the ToolKitInterface
        """

        if (self.EnvironmentObject is None and 'EnvironmentObject' not in kwargs) and self.tki is None:
            log.error("ERROR: ToolKitInterface and EnvironmentObject not found")
            return ExecutionException('ToolKitInterface and EnvironmentObject not found')

        self._setup(**kwargs)

    def _setup(self, **kwargs) -> None:
        """ This checks to see if there are any requirements before this command can be executed.
            If there are, the requirements are executed in a batch using _requirementsRunner.
        """

        self.EnvironmentObject = self._EnvironmentObjectBackup = kwargs.get('EnvironmentObject')
        if self.EnvironmentObject:
            self.EnvironmentObject.commandObject = self
            if self.root:
                self.EnvironmentObject.becomeRoot()
        if 'tki' in kwargs:
            self.tki = self._tkiBackup = kwargs.get('tki')
            self.handleChildren(tki=self.tki)

    def _preparserRunner(self):
        try:
            if type(self._preparser) is list:
                preparResults = None
                for prepar in self._preparser:
                    preparResults = prepar(this=self)
                return preparResults
            return self._preparser(this=self)
        except Exception as e:
            log.error(f"ERROR in _preparserRunner: {e}")
            log.debug(f"[DEBUG] for _preparserRunner: {traceback.format_exc()}")
            return PreparserException(e, baseException=e)


class CommandContainer(CommandSetup):
    """ This is most of the logic/work is done.
        Note that this object is automatically created as an inherited class via CommandContainer below.
        Type checks are also automatically performed during execution that require this structure.
        This may be cleaned up at some point but there are no issues due to it so it is low priority.
        Just remember to use CommandContainer if manually creating CommandObjects.
    """

    startTime: float = None
    endTime: float = None

    def __init__(self, *args, **kwargs):
        """ This class has nothing to do here. It is the work horse not the _setup().
            Main user functions (aside from context manager):
                executor()
                waitForResults()
                forceComplete()
                resetContainers()
            Other public functions usually not directly accessed by a user:
                setLastResults()
                checkResults() (used by setLastResults())
                setFailure() (called from setLastResults())
                performComplete()
                finalizeExecution()
            Note that methods are clustered closest to other dependent methods to promote better reading flow.
            Statics and privates are mixed in with publics, but properties are always at the bottom and magics on top.
        """
        log.info("Setting up CommandContainer")
        super(CommandContainer, self).__init__(*args, **kwargs)
        self.startTime = None
        self.endTime = None

    def __hash__(self):
        return hash(self.commandKey)

    def __enter__(self):
        if safe_acquire(self.__OBJECTLOCK__, self.timeout):
            self._event.clear()
            self.running = True
            return self
        else:
            log.error(f"ERROR: CommandObject waitLock failed with timeout: {self.commandKey} : {self.timeout}")
            log.debug(f"[DEBUG] for CommandOBject waitLock: {traceback.format_exc()}")
            raise RuntimeError(f"CommandObject failed to obtain lock within the timeframe: "
                               f"{self.commandKey} : {self.timeout}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        safe_release(self.__OBJECTLOCK__)
        self._completionEvent.set()
        self.complete = True
        self.running = False
        log.debug(f'CommandObject completed: {self.commandKey} : {self._command}')

    def __str__(self):
        return str(self.commandKey)

    def executor(self, **kwargs) -> CommandContainer:
        """ This is the main function run in order to execute command(s).
            It requires that the EnvironmentObject and/or the tki variable be set.
            This is normally run after _setup() and is called from within _exeThread().
            Steps:
            1. Ensure the CommandObject is executable.
            2. Requirements run and return None or an exception.
            2. Preparser runs and returns whatever.
            4. Execution of the command structure occurs and commands are executed and results returned.
            5. Postparser runs using lastResults and returns the updated results.
            6. Completion task runs using lastResults and returns nothing but can run setFailure() for stopOnFailure.
            7. Finalization occurs moving lastResults to results and setting all remaining events.

        - :return: a copy of this container
        """

        try:
            log.debug(f" ===== CommandObject executor running with command and children: "
                      f"{self.commandKey} : {self.command} : {[c.commandKey for c in self.children]} ===== ")
            # Run requirements and preparser and abort if an exception is found
            self.startTime = time.time()
            if self.setLastResults(self.runCommandSetup(**kwargs)):
                if self.setLastResults(self.runRequirements(), phase='requirements'):
                    if self.setLastResults(self._preparserRunner(), phase='preparser'):
                        # Decision tree for which mode to execute in. Threaded/UnThreaded or unknown
                        if self.EnvironmentObject is not None or self.children:
                            self.setLastResults(self._executorThreadHelper(), phase='execution')
                        elif self.EnvironmentObject is None:
                            self.setLastResults(self._executorUnThreadedHelper(), phase='execution')
                        else:  # Y U NO SSH or whatever thing of error
                            self.setLastResults(self._executorFailure())
        except Exception as e:  # any unexpected exceptions could be anywhere in the process
            self.setLastResults(self._processException(e))
        finally:
            self.endTime = time.time()
            return self.finalizeExecution()

    def _executorThreadHelper(self) -> Union[Union[str, dict], Exception]:
        """ Attempts to execute threaded commands in a batch or a queue, or a single threaded command.

        - :return: string for single command, dict for multiple commands, exception on error
        """

        if self.command is not None:
            log.info(f"CommandObject has one threaded command: {self.commandKey} with kwargs: {self.kwargs}")
            return self.EnvironmentObject.executeOnEnvironment(cmd=self.command, **self.kwargs)
        if len(self.children) > 0:
            log.info(f"CommandObject has threaded children: {self.commandKey} : {self.children} ")
            if type(self.children) is set:
                log.debug(f'CommandObject running batched children: {self.commandKey} : {self.children} ')
                return self._executorHelper()
            if type(self.children) is list:
                log.debug(f'CommandObject running queued children: {self.commandKey} : {self.children} ')
                return self._executorHelper(_queue=True)
            log.error(f"ERROR: CommandObject format of child data is invalid: {self.commandKey} : {self.children} ")
            return DataFormatException(f'CommandObject format of child data is invalid: '
                                       f'{self.commandKey} : {self.children}')
        return self._executorFailure()

    def _executorUnThreadedHelper(self) -> Union[Union[str, dict], Exception]:
        """ Attempts to execute on the main ssh channel one command at a time.

        - :return: string for single command, dict for multiple commands, exception on error
        """

        if self.command is not None:
            log.info(f"CommandObject has one unthreaded command: {self.commandKey}")
            with self.tki.sshCon.mainEnvironment as env:
                return self.tki.sshCon.executeOnEnvironment(env, self.command, **self.kwargs)
        if len(self.children) > 0:
            log.info(f"CommandObject has unthreaded children: {self.commandKey} : {self.children} ")
            return self._executorHelper(threading=False)
        return self._executorFailure()

    def _executorHelper(self, _queue: Optional[Iterable] = None, threading: bool = True) -> Union[dict, Exception]:
        """ Designed to be a helper for _executorUnThreadedHelper() and _executorThreadHelper() for multiple commands.
            It is designed to help execute children.
            An unthreaded batch (unordered iterable data type only):
                stopOnFailure has no effect here and will be checked when waiting for results
            A threaded queue (ordered iterable data type, requires _timeout only):
                will return an exception if stopOnFailure is set,
                    incomplete children will have required events set on containers to prevent hanging and waiting
            An unthreaded queue (_executorHelperhreading set to False, no _timeout):
                will return an exception if stopOnFailure is set,
                    incomplete children will have required events set on containers to prevent hanging and waiting

        - :return: dict, exception on error if _stopOnFailure or _timeoutExceptions are true
        """
        log.info(f'ExecutorHelper _queue = {_queue} and threading = {threading}')
        if _queue:
            exHelperTimeout = sum([c.timeout for c in self.children]) or self.timeout
        else:
            exHelperTimeout = max([c.timeout for c in self.children]) or self.timeout
        _endTime = time.time() + exHelperTimeout
        log.debug(f"Looping through the childern with _endTime = {_endTime}")
        for child in self.children:
            log.debug(f"Running child: {child.command}")
            if 0 < _endTime <= time.time():
                return TimeoutException(f'Batch execution timed out before child command: '
                                        f'{self.commandKey} : {child.commandKey}')
            if _queue and ('EnvironmentObject' in self.kwargs and 'EnvironmentObject' not in child.kwargs):
                child.kwargs['EnvironmentObject'] = self.kwargs['EnvironmentObject']
            genericCmdModule.GenericCmdModule.simpleExecutor(self, child, child.commandKey, tki=self.tki,
                                                             threading=threading, **child.kwargs)

            if _queue or threading is False:  # wait for each child in a queue
                child.waitForResults(_endTime - time.time())
                # stopOnFailure only matters here if unthreaded or a queue to avoid waiting on each batch item
                if self._stopOnFailure and child.failure:
                    log.debug(f"Child command failed and stopped queue execution: {self.commandKey} : {child}")
                    return ExecutionException(f'Child command failed and stopped queue execution: '
                                              f'{self.commandKey} : {child}')
        # wait for the batch to fully complete and always return the results for every scenario
        if self.children:
            return self._waitForChildren(wait=_endTime - time.time())

    def _executorFailure(self) -> Exception:
        """ Simply returns an exception when the executor encounters a (usually) internal issue. """

        if self.command is None:
            log.error(f"CommandObject received no command or children: {str(self)}")
            return ExecutionException(f'CommandObject received no command or children: {str(self)}')
        log.error(f"Failed to determine execution mode for CommandObject: {self.commandKey}")
        return ExecutionException(f'Failed to determine execution mode for CommandObject: {self.commandKey}')

    def waitForResults(self, wait: Optional[Union[float, int]] = None) -> Union[Union[str, dict], Exception]:
        """ This is designed to wait until the command object is finished executing the command and parsing the results.

        - :param wait: use when the command object has children, defaults to the timeout attribute of the container
        """

        if wait is None:
            wait = self.kwargs.get('wait', self.timeout) or self.timeout
        if wait is True:
            wait = self.timeout
        if self.children:
            if self._event.wait(wait) and self._completionEvent.wait(wait):
                return self.results
        elif self._event.wait(wait):
            return self.results
        if self._timeoutExceptions:
            return TimeoutException(f'Command timed out waiting for results: {self.commandKey}')

    def _waitForChildren(self, wait: Optional[Union[float, int]] = None) -> Union[Union[str, dict], Exception]:
        """ Private method to wait for just the children so the parent knows when to proceed """

        if wait is None:
            wait = self.kwargs.get('wait', self.timeout) or self.timeout
        if wait is True:
            wait = self.timeout
        if self._event.wait(wait):
            return self.lastResults
        if self._timeoutExceptions:
            return TimeoutException(f'Child commands timed out waiting for results: '
                                    f'{self.commandKey} : {self.children}')

    def setLastResults(self, results: Optional[Any] = None, resultsOrigin: Optional[str] = None,
                       phase: Any =None, **kwargs) -> bool:
        """ This sets lastResults on the current object and tells the parent to do the same if a parent exists.

        - :param results: value used to set lastResults
        - :param resultsOrigin: name of the child command container if called by a child
        - :param phase:
        - :return: boolean value: True for success and False for failure found in the results
        """

        if not self.checkResults(results):
            results = self.setFailure(results, **kwargs)
        if resultsOrigin:
            try:
                self.lastResults.update({resultsOrigin: results})
            except:
                self.lastResults = {resultsOrigin: results}
        else:
            self.lastResults = results
        if self.parent:
            self.parent.setLastResults(results, self.commandKey)
        if phase and self.startTime is not None and time.time() > self.startTime + self.timeout:
            log.debug(f'CommandObject timed out during phase: {self.commandKey} : {phase}')
            raise TimeoutException(f"CommandObject timed out during phase: {self.commandKey} : {phase}")
        if self.failure:
            return False
        return True

    def checkResults(self, cmdData: Any = None) -> bool:
        """ Check the cmdData (results) at any time to see if they are an exception.

        - :param cmdData: the results of the command at any point in the process
        """

        if (self._stopOnFailure or not self.children) and isinstance(cmdData, Exception):
            return False
        if self.children and not [c for c in self.children if not c.failure]:
            log.warning(f'All children failed: {self.commandKey} : {self.children}')
            return False
        return True

    def setFailure(self, results: Any = None, **kwargs) -> Any:
        """ The method is run if a failure was detected somewhere in the process.
            This process also kicks off the custom onFailure method.

        - :param results: results of the command or failure
        - :return: results of custom failure method or an exception
        """

        try:
            log.warning(f"A failure occurred for Command: {str(self.commandKey)}")
            log.debug(f"The raw failure results are: {results}")
            return self._onFailure(results, this=self, **kwargs)
        except Exception as e:
            log.warning(f'Exception when setting failure for command: {str(self.commandKey)}')
            log.debug(f'The raw failure results are: {results}')
            return SetFailureException(e, baseException=e)
        finally:
            if not self.complete:
                self.forceComplete()
            self.failure = True

    def _parseResults(self) -> Any:
        """ This method is designed to do the reverse of the _createTags from CommandData
                except to the results of the command itself.
            It also calls the custom parser.

        - :return: the value of 'self.results' or Exception
        """

        try:
            if self.parsed:
                return self.lastResults or self.results
            results = self.lastResults
            if not self.noParsing and not self.children:
                results = CommandContainer._singleCommandParser(results)
            if not self.rawResults:
                self.rawResults = results
            if not self.customPostParser:
                return results
            if type(self._postparser) is list:
                for pparser in self._postparser:
                    results = pparser(results, this=self)
                return results
            return self._postparser(results, this=self)
        except Exception as e:
            log.error(f'Postparser exception: {self.commandKey} : {str(self._postparser)}')
            log.debug(f'Stack Trace: \n{traceback.format_exc()}')
            return PostParserException(e, baseException=e)
        finally:
            self.parsed = True

    def performComplete(self) -> Any:
        """ This is called by the __exit__ function and attempts to run a custom onComplete function.

        - :return: bool, results, or raises an exception on error
        """

        try:
            if self._completionEvent.is_set() or not self.customPostParser:
                return self.lastResults or self.results
            return self._onComplete(self.lastResults, this=self)
        except Exception as e:
            log.error(f'Completion task exception: {self.commandKey} : {str(self._onComplete)}')
            log.debug(f'Stack Trace:\n {traceback.format_exc()}')
            return CompletionTaskException(e, baseException=e)

    def finalizeExecution(self) -> CommandContainer:
        """
            This is the final wrap up step for the execution process and occurs only after the current object is done
            Moves lastResults to results and sets the event for the current object.
                Current event may be a shared multievent shared across parents and children.
            lastResults is then cleared.
        """
        try:
            if self._stopOnFailure:
                if not self.failure:
                    if self.setLastResults(self._parseResults()):
                        self.performComplete()
            else:
                self.setLastResults(self._parseResults())
                self.performComplete()
        except Exception as e:
            self.setLastResults(self._processException(e))
        finally:
            self.results = self.lastResults
            self.lastResults = None
            return self

    def _processException(self, e: Exception) -> Exception:
        """ General exception processor for errors during execution """

        def _disconnectHelper():
            try:
                log.debug("Disconnecting SSH connection due to a failure")
                if self.tki and not self.EnvironmentObject:
                    self.tki.disconnect()
                if self.EnvironmentObject:
                    self.EnvironmentObject.disconnectEnvironment()
            except Exception as secondaryException:
                log.debug(f"An unknown error occurred while attempting to disconnect: "
                          f"{self.commandKey}.\nError: {secondaryException}\n{traceback.format_exc()}\n")
                return secondaryException

        if not isinstance(e, Exception):
            return DataFormatException(f"The object provided is not an exception: {str(e)}")
        objectType = type(e)
        if objectType == SSHExceptionConn:
            log.error(f'CONNECTION ERROR: {e}\n{traceback.format_exc()}')
            log.debug(f'This usually occurs when the SSH connection is prematurely severed.')
            log.debug(f'The preRunner failed for CommandObject with preparser and requirements: '
                      f'{self.commandKey} : {str(self._preparser)} : {str(self.requirements)}')
            e = _disconnectHelper()
        elif objectType == TimeToFirstBitException or objectType == BetweenBitException:
            log.error(f"Error receiving data from buffer after command was sent. "
                      f"\nError: {e}\n{traceback.format_exc()}\n")
            log.debug(f'The preRunner failed for CommandObject with preparser and requirements: '
                      f'{self.commandKey} : {str(self._preparser)} : {str(self.requirements)}')
            e = _disconnectHelper()
        elif objectType == RuntimeError:
            log.error(f'A runtime error occurred when attempting to gain the lock on an object\n'
                      f'The commandKey is: {self.commandKey}\nThe preparser is: {str(self._preparser)}'
                      f'\nThe requirements are: {str(self.requirements)}')
            log.debug(f"An error occurred trying to gain the lock of the Object: "
                      f"{self.commandKey}.\nError: {e}\n{traceback.format_exc()}\n")
        else:
            log.error(f'Error occurred: {objectType}\nThe commandKey is: {self.commandKey}\n'
                      f'The preparser is: {str(self._preparser)}\nThe requirements are: {str(self.requirements)}')
            log.debug(f"Error occurred: {self.commandKey}.\nError: {e}\n{traceback.format_exc()}\n")
        return e

    @property
    def executionLength(self):
        try:
            if self.startTime and self.endTime:
                return round(self.endTime - self.startTime, 10)
        except Exception:
            return 0.0
