#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 2.2


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('serviceModule')


class serviceModule(GenericCmdModule):
    """
         This is used to control services on remote machines.
         It can determine what service and persistence control command is present on the remote target and
         use that as the default command.
         defaultCmd: depends on OS.
         defaultFlags =
     """

    __COMMAND__ = {
        '__servicecontrol': 'if [[ -n `which systemctl 2>/dev/null` ]]; then echo "systemctlCMD"; '
                          'elif [[ -n `which service 2>/dev/null` ]]; then echo "serviceCMD"; '
                          'else echo "initdCMD"; fi'
    }
    __PERSISTENCE__ = {
        '__persistencecontrol': 'if [[ -n `which systemctl 2>/dev/null` ]]; then echo "systemctlPersistence"; '
                              'elif [[ -n `which chkconfig 2>/dev/null` ]]; then echo "chkconfigPersistence"; '
                              'else echo "placeHolderPersistence"; fi'
    }

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating Service Command Module")
        super(serviceModule, self).__init__(tki=tki)
        # self.simpleExecute(command=self.__COMMAND__, rerun=True)
        # log.info("About to simple execute persistence command")
        # self.simpleExecute(command=self.__PERSISTENCE__, rerun=True)
        self.requireFlags = True
        self.__NAME__ = "service"

    def run(self, *args, **kwargs):
        return self.serviceControl(*args, **kwargs)

    def serviceControl(self, service, stop=False, start=False, restart=False, status=None, wait=60, **kwargs):
        """ This will check the type of OS and version so it can call the correct service function.
            It will go through all the parameters in order so that you can switch both stop and start.

        - :param service: (str) service name
        - :param stop: (bool)
        - :param start: (bool)
        - :param restart: (bool)
        - :param status: (bool)
        - :param wait: (int)
        """

        if not (stop or start or restart):
            if status is None and not service:
                return
            if service and not status:
                status = True
        return self.getServiceCommand()(
            service=service, stop=stop, start=start, restart=restart, status=status, wait=wait, **kwargs)

    def persistenceControl(self, service, onBoot=True, wait=60, **kwargs):
        """ This will enable or disable the service in question on boot.

        - :param service: (str) service name
        - :param onBoot: (bool)
        - :param wait: (int)
        """

        if service:
            return self.getPersistenceCommand()(service=service, onBoot=onBoot, wait=wait, **kwargs)

    def serviceCMD(self, service, stop=False, start=False, restart=False, status=False, wait=60, rerun=True, **kwargs):

        if not status:
            kwargs.update(self.updatekwargs('postparser', GenericCmdModule._formatExitCode, **kwargs))
        if stop:
            return self.simpleExecute({'service-stop': f'service {service} stop; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        if start:
            return self.simpleExecute({'service-start': f'service {service} start; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        if restart:
            return self.simpleExecute({'service-restart': f'service {service} restart; echo $?' % service },
                                      rerun=rerun, wait=wait, **kwargs)
        if status:
            return self.simpleExecute({'service-status': f'service {service} status'}, rerun=rerun, wait=wait, **kwargs)

    def systemctlCMD(self, service, stop=False, start=False, restart=False, status=False,
                     wait=60, rerun=True, **kwargs):

        if not status:
            kwargs.update(self.updatekwargs('postparser', GenericCmdModule._formatExitCode, **kwargs))
        if stop:
            return self.simpleExecute({'systemctl-stop': f'systemctl --no-pager stop {service}; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        if start:
            return self.simpleExecute({'systemctl-start': f'systemctl --no-pager start {service}; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        if restart:
            return self.simpleExecute({'systemctl-restart': f'systemctl --no-pager restart {service}; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        if status:
            return self.simpleExecute({'systemctl-status': f'systemctl --no-pager status {service}'},
                                      rerun=rerun, wait=wait, **kwargs)

    def initdCMD(self, service, stop=False, start=False, restart=False, status=False, wait=60, rerun=True, **kwargs):

        if not status:
            kwargs.update(self.updatekwargs('postparser', GenericCmdModule._formatExitCode, **kwargs))
        if stop:
            return self.simpleExecute({'initd-stop': f'/etc/init.d/{service} stop; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        if start:
            return self.simpleExecute({'initd-start': f'/etc/init.d/{service} start; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        if restart:
            return self.simpleExecute({'initd-restart': f'/etc/init.d/{service} restart; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        if status:
            return self.simpleExecute({'initd-status': f'/etc/init.d/{service} status'},
                                      rerun=rerun, wait=wait, **kwargs)

    @staticmethod
    def _onBootParser(results, *args, **kwargs):
        if not isinstance(results, str):
            return False
        return results == '0'

    def systemctlPersistence(self, service, onBoot=False, wait=60, rerun=True, **kwargs):

        kwargs.update(self.updatekwargs('postparser', GenericCmdModule._formatExitCode, **kwargs))

        if onBoot:
            return self.simpleExecute({'systemctl-enable': f'systemctl --no-pager enable {service}; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        elif onBoot is False:
            return self.simpleExecute({'systemctl-disable': f'systemctl --no-pager disable {service}; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        elif onBoot is None:
            return self.simpleExecute({
                'systemctl-check':
                    f'systemctl --no-pager status {service} | grep "Loaded: " | grep -q "enabled" ; echo $?'},
                rerun=rerun, wait=wait, **kwargs)

    def chkconfigPersistence(self, service, onBoot=False, wait=60, rerun=True, **kwargs):

        kwargs.update(self.updatekwargs('postparser', GenericCmdModule._formatExitCode, **kwargs))

        if onBoot:
            if onBoot == 'add':
                return self.simpleExecute({'chkconfig-enable':
                                               f'chkconfig --add {service} && chkconfig {service} on; echo $?'},
                                          rerun=rerun, wait=wait, **kwargs)
            return self.simpleExecute({'chkconfig-enable': f'chkconfig {service} on; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        elif onBoot is False:
            return self.simpleExecute({'chkconfig-disable': f'chkconfig {service} off; echo $?'},
                                      rerun=rerun, wait=wait, **kwargs)
        elif onBoot is None:
            return self.simpleExecute({'chkconfig-check': f"chkconfig --list {service} | grep -q ':on' ; echo $?"},
                                      rerun=rerun, wait=wait, **kwargs)

    def getServiceCommand(self, wait=60):
        return getattr(self, self.servicecontrol.waitForResults(wait=wait), self.systemctlCMD)

    def getPersistenceCommand(self, wait=60):
        return getattr(self, self.persistencecontrol.waitForResults(wait=wait), self.systemctlPersistence)

    def isRunning(self, service, wait=60, rerun=True):

        def _parseStatus(results, *args, **kwargs):
            if not isinstance(results, str):
                return False
            if 'Active: ' in results:
                return 'running' in results.strip().splitlines()[2]
            elif len(results.strip().splitlines()) < 3:
                return 'running' in results
            else:
                return None

        return self.serviceControl(service, status=True, wait=wait, rerun=rerun, postparser=_parseStatus)

    def isOnBoot(self, service, wait=60, rerun=True):
        return self.persistenceControl(service, onBoot=None, wait=wait, rerun=rerun)

    @staticmethod
    def placeHolderPersistence(*args, **kwargs):
        return False

    @property
    def servicecontrol(self):
        if not hasattr(self, '__servicecontrol'):
            self.simpleExecute(command=self.__COMMAND__, rerun=True)
        return getattr(self, '__servicecontrol', None)


    @property
    def persistencecontrol(self):
        if not hasattr(self, '__persistencecontrol'):
            self.simpleExecute(command=self.__PERSISTENCE__, rerun=True)
        return getattr(self, '__persistencecontrol', None)
