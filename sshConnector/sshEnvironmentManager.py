#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.5.0
# Date: 11/10/15
# Description: This is the 5th class in the sshConnector. This is to focus on creating and handling custom channels.
# This file also the home of the _ChannelContainer and manages when and how to make new channels.


import logging
import time
import traceback
from threading import RLock
from sshConnector.sshEnvironmentControl import sshEnvironmentControl
from sshConnector.sshLibs.sshChannelEnvironment import EnvironmentControls
from typing import Optional, Union


log = logging.getLogger('sshChannelManager')


class sshEnvironmentManager(sshEnvironmentControl):

    _EnvironmentList = None
    _ENVIRONMENT_LIST_LOCK = None
    _MAX_SESSIONS = None
    _DEFAULT_MAX_SESSIONS = 8
    _MaxSessionsString = "if [ -f /etc/ssh/sshd_config ]; then output=$(grep -v '^#' /etc/ssh/sshd_config 2>&1 | awk " \
                         "'/MaxSessions/ {print $2}'); if [ -z \"$output\" ]; then output='%s'; fi; else output='%s';" \
                         "fi; echo $output"

    def __init__(self, arguments, **kwargs):
        self._ENVIRONMENT_LIST_LOCK = RLock()
        super(sshEnvironmentManager, self).__init__(arguments=arguments, **kwargs)
        self._MAX_SESSIONS = self.getMaxSessionsValue(maxChannels=arguments.maxChannels)
        self._EnvironmentList = []
        self.addEnvironment(self.mainEnvironment)

    def getMaxSessionsValue(self, maxChannels: Optional[int] = None) -> int:
        """ This attempts to change the max amount of channels this tool can use based on the target server's
            MaxSessions variable in sshd_config file. If the machine received the argument maxChannels it will
            attempt to use that as long as it isn't above 10. The default value is 8.

        - :param maxChannels:
        - :return:
        """

        try:
            if type(maxChannels) is int and (10 >= maxChannels > 0):
                return maxChannels
            output = self.executeOnEnvironment(self.mainEnvironment,
                                               self._MaxSessionsString %
                                               (self._DEFAULT_MAX_SESSIONS, self._DEFAULT_MAX_SESSIONS),
                                               self.mainEnvironment.prompt,
                                               runTimeout=15)
            if not output:
                return self._DEFAULT_MAX_SESSIONS
            return int(output.strip().splitlines()[-1].strip()) - 1
        except Exception as e:
            log.error(f"error in getMaxSessionsValue: {e}")
            log.debug(f"[DEBUG] for getMaxSessionsValue: {traceback.format_exc()}")
            return self._DEFAULT_MAX_SESSIONS

    def getEnvironment(self, autoCreate=True, label=None, EnvironmentID=None, wait=60, delay=1, **kwargs)\
            -> Union[bool, EnvironmentControls]:
        """ This grabs the next available EnvironmentControls object or creates one.

        - :param autoCreate: (bool) default True, If no label or channelID is provided then this will make the method
            return a new _channelContainer if none available are found.
        - :param label: (str) default None. Looks for a particular label. Waits if it finds one but it is being used.
            Returns False is none are found.
        - :param channelID: (str) default None. Looks for a particular channelID. Waits if it finds it but finds it being
            used. Returns False
        - :param wait: (int) default 60. Tells how long to wait for a channel to become available.
        - :param delay: (float) default 0.1. Tells how long to pause between waiting.
        - :param kwargs: passed into a new _channelObject if this method tries to make a new channel.
        -:return:
        """

        try:
            start_time = time.time()
            while time.time() < start_time + wait:
                channelObj = self._checkEnvironments(autoCreate, label, EnvironmentID)
                if channelObj is True:
                    channelObj = self.createEnvironment(label=label, **kwargs)
                if channelObj is False:
                    time.sleep(delay)
                    continue
                if channelObj is not None:
                    channelObj.active = True
                return channelObj
            return False
        except Exception as e:
            log.error(f"ERROR in getEnvironment: There was a failure getting Channel: {e}")
            log.debug(f"[DEBUG] for getEnvironment: {traceback.format_exc()}")

    def createEnvironment(self, **kwargs) -> Union[bool, EnvironmentControls]:
        """ Used to create a new channel.

        - :param maxChannels: (int) default (whatever the _MAX_CHANNEL class variable is set to). This is passed directly
            to '_checkMaxChannels'. This can temporarily override the _MAX_CHANNEL setting.
        - :param autoAdd: (bool) default True: determines if the 'addChannel' method will be called to add the new channel
        - :param toBeUsed: (bool) default True: This is actually a _ChannelContainer object param but it is important here
            as it can be sued to control weather or not the new object will be available for use by the calling thread
            or can immediately be available for other threads to use.
        - :param kwargs:
        - :return:
        """

        if not self._checkMaxSessions(**kwargs):
            log.debug("A new channel cannot be made as there already are too many channels")
            return False
        autoAdd = kwargs.pop('autoAdd', True)
        EnvObj = self._openChannel(self.mainEnvironment.get_transport())
        EnvObj.label = kwargs.get('label', '')
        EnvObj.push("su -", name=self.arguments.username, additionalInput=self.arguments.password)
        if self.arguments.root:
            EnvObj.becomeRoot()
        else:
            EnvObj.escalate(escalationCmd='bash', escalationArgs='-norc', name='BASH',
                            console=True, unsafe=True, reCapturePrompt=True)
        if autoAdd:
            self.addEnvironment(EnvObj)
        return EnvObj

    def addEnvironment(self, channel: EnvironmentControls, **kwargs) -> bool:
        """ Adds a provided channel to the channel manager.

        - :param channel: (Channel) default None.
        - :param kwargs: passed into a new _ChannelObject if one is created.
        - :return: (bool)
        """

        try:
            if not self._checkMaxSessions(**kwargs):
                log.debug("A new channel cannot be added as there already are too many channels")
                return False
            self.EnvironmentList.append(channel)
            return True
        except Exception as e:
            log.error(f"ERROR: There was a failure in addEnvironment: {e}")
            log.debug(f"[DEBUG] for addEnvironment: {traceback.format_exc()}")
            return False

    def removeEnvironment(self, channel: EnvironmentControls) -> Optional[bool]:
        """ Removed the provided object.

        - :param channel: (_ChannelObject)
        - :return:
        """

        try:
            if channel in self._EnvironmentList:
                self._EnvironmentList.remove(channel)
                return True
            else:
                log.debug("Channel %s appears to have already been removed!" % channel.EnvironmentID)
                return None
        except Exception as e:
            log.error("ERROR: There was a failure in removeEnvironment: %s" % e)
            log.error("The failure is associated with channel: %s" % channel.EnvironmentID)
            return False

    def disconnectEnvironments(self) -> None:
        """ Disconnects all Environments. Used by 'disconnect' method from 'sshThreader'

        - :return:
        """

        with self._ENVIRONMENT_LIST_LOCK:
            for environment in [env for env in self.EnvironmentList if not env.isMain]:
                environment.disconnectEnvironment()
            self.mainEnvironment.disconnectEnvironment()

    def _checkMaxSessions(self, **kwargs) -> bool:
        """ This parses maxChannels out of kwargs for some methods.

        - :param kwargs:
        - :return:
        """

        maxChannels = kwargs.pop('maxChannels', self._MAX_SESSIONS) or self._MAX_SESSIONS
        return not self.EnvironmentCount >= maxChannels

    def _checkEnvironments(self, autoCreate: Optional[bool] = True, label: Optional[str] = None,
                           EnvironmentID: Optional[str] = None) -> Optional[Union[bool, EnvironmentControls]]:
        """ This is the work horse of this class. This finds what is available.

        - :param autoCreate: (bool) default True. This is parsed based on label and channelID. It is set to False if
            either label or channelID are not None. Then this is variable is returned if this method cannot find a
            _ChannelContainer.
        - :param label: (str) default None. If label is found then this will look exclusively for a _ChannelContainer with
            that label.
        - :param EnvironmentID: (str) default None. If EnvironmentID is found then this will look exclusively for a
            EnvironmentControls with that EnvironmentID.
        - :return: either a EnvironmentControls or autoCreate
        """

        autoCreate = autoCreate and (EnvironmentID is None)

        def labelFilter(envObj):
            return label == envObj.label

        def EnvironmentIDFilter(envObj):
            return EnvironmentID == envObj.EnvironmentID

        def activeCustomFilter(envObj):
            return not envObj.active and not envObj.customChannel

        def justActiveFilter(envObj):
            return not envObj.active

        def popChannel(envObj) -> Optional[Union[bool, EnvironmentControls]]:
            if len(envObj) < 1:
                return autoCreate
            envObj = envObj[0]
            envObj.active = True
            return envObj

        with self._ENVIRONMENT_LIST_LOCK:
            if label is not None or EnvironmentID is not None:
                if EnvironmentID:
                    envObject = list(filter(EnvironmentIDFilter, self._EnvironmentList))
                else:
                    envObject = list(filter(labelFilter, self._EnvironmentList))
                if not envObject:
                    return autoCreate or None
                return popChannel(list(filter(justActiveFilter, envObject)))
            return popChannel(list(filter(activeCustomFilter, self._EnvironmentList)))

    @property
    def EnvironmentCount(self):
        with self._ENVIRONMENT_LIST_LOCK:
            return len(self._EnvironmentList)

    @property
    def EnvironmentList(self):
        with self._ENVIRONMENT_LIST_LOCK:
            return self._EnvironmentList
