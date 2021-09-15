#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the kill command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule
from PyCustomParsers.PyCustomParsers.GenericParser import BashParser


log = logging.getLogger('mountModule')


class mountModule(GenericCmdModule, BashParser):
    """
         mountModule class. This class inherits from both the GenericCmdModule and BashParser. It is used to execute the
         Linux command 'mount' on remote machines.
         defaultCmd: mount
         defaultFlags =
    """

    _mountTemplate = {'Device': 0, 'MountPoint': 2, 'Type': 4, 'Flags': 5}

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating mount module")
        super(mountModule, self).__init__(tki=tki)
        super(GenericCmdModule, self).__init__(template=self._mountTemplate)
        self.defaultCmd = 'mount '
        self.defaultKey = "mountCmd"
        self.defaultFlags = ""
        self.defaultKwargs = {'postparser': self._mountFormatOutput}
        self.__NAME__ = "mount"

    def _mountFormatOutput(self, results, *args, **kwargs):
        if not results:
            return None
        self.parseInput(source=results, refreshData=True)
        return self

    def mountDevice(self, mountStr, checkMount=None, **kwargs):
        """ Attempts to mount a device using the mount command via the '_mountCmdHelper' method with 'mountStr' as
            arguments.

        - :param mountStr: (str) the arguments used with '/bin/mount'
        - :param checkMount: (str) if given the method will pass 'checkMount' too method 'isMounted' and return the
                value.
        - :param kwargs:
        - :return:
        """

        return self._mountCmdHelper(f"/bin/mount {mountStr}", commandKey="mount_" + mountStr,
                                    checkMount=checkMount, **kwargs)

    def umountDevice(self, mountStr, checkMount=None, **kwargs):
        """ Like mountDevcie except it runs umount instead.

        - :param mountStr:
        - :param checkMount:
        - :param kwargs:
        - :return:
        """

        return self._mountCmdHelper(f"/bin/umount {mountStr}", commandKey="umount_" + mountStr,
                                    checkMount=checkMount, **kwargs)

    def mountAsPerFstab(self, device, checkMount=None, **kwargs):
        """ This takes data from the 'fstab' and uses it to constructs a mount command. This is to avoid using
            'mount -a' as this may have unforeseen consequences.

        - :param device: The device in fstab to grab info about
        - :param checkMount: A 'str' of the MountPoint that should show up if this command works. If this is passed the
             method will rerun the mount command and then run 'isMounted' method.
        - :param kwargs:
        - :return:
        """

        mountCmd = "/bin/mount -t %s %s %s -o %s"
        fstab = self.tki.modules.fstab
        fstab(rerun=True, wait=180)
        mountPoint = fstab.getSearchValues(('Device', device))['MountPoint']
        deviceType = fstab.getSearchValues(('Device', device))['Type']
        options = fstab.getSearchValues(('Device', device))['Options']
        if len(mountPoint) + len(deviceType) + len(options) != 3:
            log.error("Failed to the correct data for Device: %s from the '/etc/fstab' file.")
            raise Exception("Failed to the correct data for Device: %s from the '/etc/fstab' file.")
        return self._mountCmdHelper(mountCmd % (deviceType.pop(), device, mountPoint.pop(), options.pop()),
                                    commandKey='mountAsPerFstab_', checkMount=checkMount, **kwargs)

    def getMountFlags(self, device=None, mountPoint=None):
        output = []
        if device:
            output.append(self.getSearch(device))
        if mountPoint:
            output.append(self.getSearch(mountPoint))
        return list(filter(None, output)).pop()['Flags'].pop().strip('(').strip(')').split(',')

    def reMountOptions(self, mountStr, newOptions, checkMount=None, **kwargs):
        mountStr = "-o remount,"+','.join(newOptions)+" "+mountStr
        return self.mountDevice(mountStr, checkMount=checkMount, **kwargs)

    def _mountCmdHelper(self, mountCmd, commandKey, checkMount=None, **kwargs):
        """ This called by 'mountDevice', 'umountDevice', and 'mountAsPerFstab'. It runs the command and then if
            'checkMount' is passed then it returns the output of 'isMounted'.

        - :param mountCmd:
        - :param commandKey:
        - :param checkMount:
        - :param kwargs:
        - :return:
        """

        if 'wait' not in kwargs:
            kwargs['wait'] = 30
        self.simpleExecute(command=mountCmd, commandKey=commandKey, **kwargs)
        if type(checkMount) is str:
            self(rerun=True, wait=60)
            if self.isMounted(checkMount):
                return True
            return False
        return None

    def isMounted(self, searchStr, **kwargs):
        return self.getSearch(searchStr, **kwargs)

    def isDeviceMounted(self, device, **kwargs):
        return self.getSearch(('Device', device))

    def isPointMounted(self, point, **kwargs):
        return self.getSearch(('MountPoint', point))

    def mountType(self, mount):
        mountInfo = self.isPointMounted(mount)
        if not mountInfo:
            return None
        mType = mountInfo['Type'][0]
        if mType != 'none':
            return mType
        if 'bind' in str(mountInfo['Flags'][0]).lower():
            return 'bind'
        return None

    def mountIsType(self, Mount, deviceType):
        mType = self.mountType(Mount)
        if not mType:
            return None
        return mType.lower() in deviceType.lower()

    def mountDeviceToPoint(self, Device):
        filesystem = self.isDeviceMounted(Device)
        if not filesystem:
            return None
        return filesystem['MountPoint'][0]

    def mountPointToDevice(self, MountPoint):
        filesystem = self.isPointMounted(MountPoint)
        if not filesystem:
            return None
        return filesystem['Device'][0]

    def deviceType(self, Device):
        filesystemInfo = self.isDeviceMounted(Device)
        if not filesystemInfo:
            return []
        return str(filesystemInfo['Type'][0])

    def deviceIsType(self, Device, deviceType):
        dType = self.deviceType(Device)
        if not dType:
            return False
        return dType.lower() in deviceType.lower()
