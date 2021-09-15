#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.5.0
# Date: 02/19/15
# Description: This is the 6th class in the sshConnect chain. Technically the last in this change. The next class to
# inherent this class should be CommandRunner which no longer focuses on anything regarding SSH. This file has two
# classes. The public class 'sshThreader' and a private class '_createThread'. The sshThreader should be the only
# class called.


# A requirement for portray
# import sys
# sys.path.append('/home/rye/PycharmProjects/PyCustomCollections')
# sys.path.append('/home/rye/PycharmProjects/PyCustomParsers')
# sys.path.append('/home/rye/PycharmProjects/PyMultiprocessTools')


import logging
import traceback
from libs.LDTKExceptions import _errorConn
# A requirement for portray
try:
    from LinuxModules.CommandContainers import CommandContainer
except:
    from ldtk import CommandContainer
from sshConnector.sshEnvironmentManager import sshEnvironmentManager
from sshConnector.sshLibs.sshChannelEnvironment import EnvironmentControls
from PyMultiprocessTools.PyThreadingPool.ThreadingPool import Pool
from typing import Optional, Union, Any
from time import time


# logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(message)s',
#                     level=logging.INFO)
log = logging.getLogger('SSHThreader')


class sshThreader(sshEnvironmentManager):
    threadDict = {}
    tPool = None
    tki = None

    def __init__(self, arguments, **kwargs):
        """ This class is designed to managed another private class that inherits from Thread. The __init__ only job
            is to build and pass info along to the rest of the chain while overriding the root flag in args to avoid
            unnecessary work.

        - :param arguments: Passed along super to sshEnvironmentManager's construct.
        - :param kwargs: A placeholder for inheritance.
        """

        super(sshThreader, self).__init__(arguments=arguments, **kwargs)
        self.tki = kwargs.pop('tki', None)
        self.tPool = Pool(maxWorkers=self._MAX_SESSIONS * 2, workerAutoKill=False)

    def isIdle(self) -> bool:
        """ This checks the 'ThreadPool' class's 'isIdle()' function and returns the results.

        - :return: bool
        """

        return self.tPool.isIdle

    def waitForIdle(self, **kwargs) -> bool:
        """ This is a wrapper for the 'waitCompletion' method in ThreadingPool.

        - :param kwargs: Review the 'waitCompletion' method in ThreadingPool for all the arguments.
        - :return: (bool)
        """

        return self.tPool.waitCompletion(**kwargs)

    def executeOnThread(self, cmd: Union[CommandContainer, Any],
                        EnvObj: Optional[EnvironmentControls] = None, **kwargs) -> CommandContainer:
        """ Submits a new command to be executed via the 'submit' method in Pool. All commands ran should be within a
            CommandContainer. So the method first checks to see if the command is already a Container or not.

        - :param CC: [Either a CommandContainer or Any other datatype]
        - :param EnvObj: (EnvironmentControls) default None. This specifies a Channel to run the command on. This
              bypasses using a Thread and instead expects that the channelObject is already 'active' or 'taken' by the
              thread currently calling this method.
        - :param kwargs: used to create a new CommandContainer is 'cmd' is not a CommandContainer
        - :return: CommandContainer (The same container that either was submitted as the cmd or the one created)
        """

        def _preparserCmd(commands, **kwargs):
            if isinstance(commands, CommandContainer):
                return commands
            if 'commandKey' not in kwargs:
                kwargs['commandKey'] = None
            if 'tki' not in kwargs and self.tki is not None:
                kwargs['tki'] = self.tki
            return CommandContainer(commands, **kwargs)

        CC = _preparserCmd(cmd, **kwargs)

        if EnvObj is None:
            self.tPool.submit(fn=self._exeThread, CC=CC, submit_task_priority=CC.__PRIORITY__)
            return CC
        else:
            if not EnvObj.active:
                log.warning("This channel is not active and it has been manually requested for use by the executor!")
            with CC:
                return CC.executor(channelObject=EnvObj)

    def threadedDisconnect(self, wait: int = 90) -> None:
        """ This does what it says. It disconnects the SSH connection to a server using a thread for each Environment.
            This is not necessary faster. In fact it is often slower. This is designed if there are many connections
            open that have many user and environment escalations. In that situation this becomes faster then
            'disconnectEnvironments'. However, this is necessary to ensure that the logout commands are not given until
            all other threaded commands have finished.

            NOTE: If disconnect is called and then later another connection is established the ThreadPool will not work!
                The function: 'setActiveThreads' will have to be called again in order for Threading to work. The var
                '_MAX_CHANNELS' must be passed to 'setActiveThreads' as the Parm 'maxThreads'.

        - :param wait: (int) default 90 - How long the method is will too wait until all login commands are finished.
        - :return:
        """

        log.info(' === Disconnecting the SSH connection')

        current_time = time()

        def _parseWait(w):
            w = w - (time() - current_time)
            if w < 10:
                w = 10
            return w

        try:
            if not self.tPool:
                super(sshThreader, self).disconnectEnvironments()
            else:
                with self.tPool:
                    self.tPool.waitCompletion(timeout=wait)
                    for env in [envs for envs in self.EnvironmentList if not envs.isMain]:
                        self.tPool.submit(env.disconnectEnvironment)
                    self.tPool.join(_parseWait(wait))
                super(sshThreader, self).disconnect(self.mainEnvironment)
        except Exception as e:
            log.error(f"Error in threadedDisconnect: {e}")
            log.debug(f"[DEBUG] for threadedDisconnect: {traceback.format_exc()}")
        finally:
            if self.checkConnection():
                super(sshThreader, self).disconnect()

    def _exeThread(self, CC: CommandContainer, **kwargs) -> CommandContainer:
        """ The method that is passed to the Pool via the 'submit' method. This method is the connection between the
            CommandContainer (which holds the command and manages the output) and the Environment that will be used to
            execute the command. This is ran on the Pool in a thread. It will also respond with the CC it was given.

        - :param CC: (CommandContainer)
        - :param kwargs: (Passed into the 'getEnvironment' method)
        - :return: (CommandContainer) The same as the 'CC' parameter
        """
        log.info(f'running _exeThread for: {CC.command}')
        if not self.checkConnection():
            log.debug("The SSH Connection is closed!")
            raise _errorConn("While running a thread it was found that the SSH Channel is closed!")

        def setupParams(otherObject: CommandContainer) -> tuple:
            if otherObject is None:
                return None, None, None
            return otherObject.kwargs.pop('label', None), \
                otherObject.kwargs.get('EnvironmentID', None), otherObject.timeout

        log.debug("About to with CC")
        with CC:
            log.debug("Successful with of CC")
            if CC.children:
                log.debug("I have children... ")
                return CC.executor()
            log.debug("About too get environment and with it")
            with self.getEnvironment(True, *setupParams(CC), **kwargs) as EnvObj:
                log.debug("Got environment and executing with environment")
                return CC.executor(EnvironmentObject=EnvObj)
