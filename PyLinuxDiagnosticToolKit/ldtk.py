#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 1.0
# Date: 02/19/15
# Description: This is designed to be an interface between sshConnector and different Command Modules. The purpose of
# this package is to create a sort of one-stop shop for programs to interact with modules and allow modules to easily
# interact with each other. Simply passing the ToolKitInterface across to each module allows them to be able to see
# each other.


# A requirement for portray
# import sys
# sys.path.append('/home/rye/PycharmProjects/PyLinuxDiagnosticToolKit')
# sys.path.append('/home/rye/PycharmProjects/PyCustomCollections')
# sys.path.append('/home/rye/PycharmProjects/PyCustomParsers')
# sys.path.append('/home/rye/PycharmProjects/PyMultiprocessTools')


import logging
import traceback
from libs import ArgumentWrapper
from libs.ArgumentWrapper import ArgumentParsers
from LinuxModules.genericCmdModule import GenericCmdModule
from LinuxModules.CommandContainers import CommandContainer
from sshConnector.sshThreader import sshThreader as threadedSSH
from sshConnector.sshLibs.SCPChannel import SCPChannel
from sshConnector.sshLibs.SFTPChannel import SFTPChannel
from sshConnector.sshLibs.sshChannelEnvironment import sshEnvironment, EnvironmentControls
from typing import Union, List, Any, Optional


logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(message)s',
                    level=logging.DEBUG)
_ptlog = logging.getLogger('paramiko.transport')
_ptlog.setLevel(logging.WARNING)
_pclog = logging.getLogger('paramiko.channel')
_pclog.setLevel(logging.WARNING)
log = logging.getLogger('ToolKitInterface')


class _ToolKitModules(dict):

    tki = None

    def __init__(self, tki, *args, **kwargs):
        self.tki = tki
        super(_ToolKitModules, self).__init__(*args, **kwargs)

    def __getattr__(self, item):
        if not (item.startswith('_') or (item.startswith('__') and item.endswith('__'))):
            return self.tki.getModules(item) or getattr(self.tki, item)


class ToolKitInterface:

    __KNOWNMODULES__ = {'sophos': {'from': 'sophosModule', 'import': 'SophosModule'},
                        'oracle': {'from': 'OracleModule', 'import': 'oracleAllTheThings'},
                        'mysql': {'from': 'mysqlModule', 'import': 'mysqlModule'}}

    def __init__(self, arguments: ArgumentParsers, auto_login: bool = True, *args, **kwargs):
        """ This acts differently depending on what is passed to it. More explained below.

        - :param arguments: Args is from argparse and is the main way data is passed between classes
        - :param autoLogin: Automatically attempt to log into the specified device
        - :param kwargs: This is an unused placeholder. This class inherits from object and its best practice to have
                have kwargs.
        """

        log.debug("Creating a ToolKitInterface module")
        self.sshCon: Optional[threadedSSH] = None
        self.modules = _ToolKitModules(self)
        if arguments is None:
            arguments = ArgumentWrapper.arguments().parse_known_args()[0]
        self.arguments = arguments
        self.auto_login = auto_login
        if auto_login:
            self.createConnection()
        # try:
        #     super(ToolKitInterface, self).__init__(*args, **kwargs)
        # except Exception as e:
        #     log.warning(f"Call too super init failed trying without args: {e}")
        #     super(ToolKitInterface, self).__init__()

    def createConnection(self, arguments: Optional[ArgumentParsers] = None) -> threadedSSH:
        """ This creates a new SSH connection using the sshConnector tool which wraps Paramiko

        - :param arguments: (ArgumentParsers) This is a wrapper object around the argparse parser object it handles
            script arguments
        - :return: (threadedSSH)
        """

        if self.sshCon is not None:
            return self.sshCon
        try:
            if arguments is None:
                arguments = self.arguments
            self.sshCon = threadedSSH(arguments=arguments, tki=self)
            return self.sshCon
        except Exception as e:
            log.error(f'ERROR: for method createConnection: {e}')
            log.debug(f'[DEBUG] for method createConnection: {traceback.format_exc()}')
            raise e

    def disconnect(self) -> None:
        """ This wraps around the 'threadedDisconnect' method of the sshConnector """
        if self.sshCon:
            self.sshCon.threadedDisconnect()

    def checkConnection(self, *args, **kwargs) -> bool:
        """ This wraps around the 'checkConnection' method of the sshConnector """
        if not self.sshCon:
            return False
        return self.sshCon.checkConnection(*args, **kwargs)

    def getModules(self, *args, **kwargs) -> Union[GenericCmdModule, List[GenericCmdModule]]:
        """ Takes in arguments as args or a single arg in the form of a str or iterable data type. This will take that
            string and attempt to return an CommandModule object that it is associated with. I.E: 'ps' will return a
            'psModule' instance of the psModule. Call this function a second time and it will return the same instance.

        - :param args: str or iterable
        - :param kwargs: Ignores
        - :return: CommandModule object as a single item or in a list.
        """

        def _parseNames(moduleNames):
            if len(moduleNames) == 1:
                moduleNames = moduleNames[0]
            if isinstance(moduleNames, str):
                return [moduleNames]
            return moduleNames or []

        def _buildOutputList(names):
            outputModules = []
            for name in _parseNames(names):
                if name in self.modules:
                    outputModules.append(self.modules[name])
                else:
                    outputModules.append(self._importAndInstantiateModule(name, **kwargs))
            if len(outputModules) == 1:
                return outputModules.pop()
            return outputModules

        if 'modules' in kwargs:
            args = kwargs.pop('modules')
        elif 'name' in kwargs:
            args = kwargs.pop('name')

        return _buildOutputList(args)

    def _importAndInstantiateModule(self, moduleName: str, **kwargs) -> GenericCmdModule:
        """ This is called directly by the 'getModules' function and should not be directly called. This function uses
            the '_importAndInstantiateModuleHelper' to do most of the heavy lifting. This functions job is to iterate
            thru the modulesNames variable and pass it along to the helper class.

        - :param moduleName: string
        - :return: GenericCmdModule
        """

        def _parseName(name):
            if 'Module' not in name:
                name += "Module"
            return name.lower(), name

        if moduleName in self.__KNOWNMODULES__:
            knowModule = self.__KNOWNMODULES__[moduleName]
            moduleObj = self._importAndInstantiateModuleHelper(knowModule['from'], knowModule['import'], **kwargs)
        else:
            moduleObj = self._importAndInstantiateModuleHelper(*_parseName(moduleName), **kwargs)
        if moduleObj is not None:
            self.modules[moduleName] = moduleObj
            if hasattr(self, moduleName):  # report any naming conflicts
                log.warning('Overwriting value for module "%s": Name already exists with value: %s'
                            % (moduleObj, getattr(self, moduleName)))
            setattr(self, moduleName, moduleObj)
        return moduleObj

    def _importAndInstantiateModuleHelper(self, moduleFrom: str, moduleImport: str, **kwargs) -> GenericCmdModule:
        """ Utilized by the '_importAndInstantiateModule' only this function attempts to dynamically import and
            instantiate an Class and return the object or return None.

        - :param moduleName: The single module name that it will try to import
        - :param knownMod: Whether or not the name can be found in the '__KNOWNMODULES__' class variable.
        - :return: GenericCmdModule
        """

        def _importHelper(fromName, importName):
            try:
                return getattr(__import__(fromName), importName)
            except Exception as e:
                print(f"Failed to import module {importName} with error:\n{e}")
                print(f"StackTrace: {traceback.format_exc()}")
                log.error(f"Failed to import module {importName} with error:\n{e}")

        def _instantiateModule(module):
            try:
                if 'tki' in kwargs:
                    return module(**kwargs)
                return module(tki=self, **kwargs)
            except Exception as e:
                print(f"Failed to instantiate module {str(module)} with error:\n{e}")
                print(f"StackTrace: {traceback.format_exc()}")
                log.error("Failed to instantiate module %s with error:\n%s" % (str(module), e))

        return _instantiateModule(_importHelper(moduleFrom, moduleImport))

    def execute(self, commands: Any, threading: bool = True, **kwargs) -> Any:
        """ This is the primary function of the LDTK for executing any command. It can be passed a string, dict,
            CommandContainer object or a list of those types. It can execute commands threaded or unthreaded.
            Threaded is default and unthreaded will use the base/main ssh channel that was opened upon connection.

        - :param commands: string,dict,CommandContainer/list/tuple/set
        - :param threading: Bool, default True
        - :param kwargs: Values passed to the CommandContainer and thus to the sshThreader
        - :return: Depends on if threading is true or not and if successful. Threading=True: It will return a
            CommandContainer. Threading=False: It will return a dictionary.
        """

        log.info(f'Executing command/type: {commands}/{type(commands)} with threading = {threading}')

        if not isinstance(commands, CommandContainer):
            kwargs.update({'tki': kwargs.get('tki', self)})
            kwargs.update({'commandKey': kwargs.get('commandKey', None)})
            commands = CommandContainer(commands, **kwargs)

        if not self.checkConnection():
            try:
                self.createConnection()
            except Exception as e:
                raise commands.forceComplete(e)

        env_obj = kwargs.get('environment', None)
        if env_obj is not None:
            commands.root = False
        threading = commands.kwargs.get('threading', threading) or threading
        if not threading:
            return self._executeUnthread(commands)
        self.sshCon.executeOnThread(commands, EnvObj=env_obj)
        return commands

    def _executeUnthread(self, commands: Any) -> Any:
        """ This allows unthreaded commands to be mixed with threaded ones.  This is called by the execute method. """

        def _exeUnthread(cmd):
            with cmd:
                cmd.executor(tki=self)
                return cmd.results

        if type(commands) is list:
            outDict = {}
            for command in commands:
                outDict[command.commandKey] = _exeUnthread(command)
            return outDict
        return _exeUnthread(commands)

    def waitForIdle(self, timeout: Union[int, float] = 60, delay: float = 0.1, block: bool = False) -> bool:
        """ This waits on the threads in the sshThreader class within sshConnector, to complete. This actually calls the
            'waitForIdle' method in sshThreader which just calls the 'waitCompletion' method in ThreadPool.
            Below are the docs from that method:

            This is the preferred method for waiting. It is thread safe and does not rely on signals.
            This will return False if tasks remain but no threads exist unless standbyTasks==True.

        - :param timeout: (int) Time to wait for all tasks to complete that cannot exceed 500 seconds
        - :param delay: (float) Time to wait between checks for all tasks complete
        - :param block: (bool) Block the task queue so that no new tasks can be added
        - :return: bool
        """

        if not self.checkConnection():
            return True
        return self.sshCon.waitForIdle(timeout=timeout, delay=delay, block=block)

    def escalate(self, *args, **kwargs) -> Union[sshEnvironment, bool]:
        """ Wraps the sshConnector's 'escalate' method """
        return self.sshCon.escalate(*args, **kwargs)

    def becomeRoot(self, **kwargs) -> Union[sshEnvironment, bool]:
        """ Wraps around becomeRoot in the sshEnvironmentControl class. """
        return self.sshCon.becomeRoot(**kwargs)

    def becomeUser(self, **kwargs) -> Union[sshEnvironment, bool]:
        """ Wraps around becomeUser in the sshEnvironmentControl class. """
        return self.sshCon.becomeUser(**kwargs)

    def environmentChange(self, *args, **kwargs) -> Union[sshEnvironment, bool]:
        """ Wraps sshConnector's 'environmentChange' """
        return self.sshCon.environmentChange(*args, **kwargs)

    def checkWhoami(self, environment=None) -> str:
        """ Wraps around the sshConnector's 'checkWhoAmI' method """
        return self.sshCon.checkWhoAmI(environment=environment)

    def getEnvironment(self, *args, **kwargs) -> Union[bool, EnvironmentControls]:
        """ Wraps around the sshConnector's 'getEnvironment' method """
        if not self.checkConnection():
            self.createConnection()
        return self.sshCon.getEnvironment(*args, **kwargs)

    def createEnvironment(self, **kwargs) -> Union[bool, EnvironmentControls]:
        """ Wraps around the sshConnector's 'createEnvironment' method """
        if not self.checkConnection():
            self.createConnection()
        return self.sshCon.createEnvironment(**kwargs)

    def getSFTPClient(self) -> SFTPChannel:
        """ Creates and returns a SFTP Channel object """
        if not self.checkConnection():
            self.createConnection()
        return SFTPChannel(self)

    def getSCPClient(self) -> SCPChannel:
        """ Creates and returns a SCP Channel object """
        if not self.checkConnection():
            self.createConnection()
        return SCPChannel(self)


if __name__ == '__main__':
    print("This should be called as a module.")
