#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the echo command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule


log = logging.getLogger('echoModule')


class echoModule(GenericCmdModule):
    """
         echoModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'echo'
         on remote machines.
         defaultCmd: buitlin echo
         defaultFlags = '"%s"'
            This pre-appends builtin before echo to avoid alias and uses '"%s"' to incaplase whatever you intend to
            echo. If you wish to avoid this execute the echo command using 'ldtk.execute('echo exampleargs')'.
    """
    cp = None

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating echo module.")
        super(echoModule, self).__init__(tki=tki)
        self.cp = self.tki.modules.cp
        self.defaultCmd = 'builtin echo '
        self.defaultKey = "echo%s"
        self.defaultFlags = '-e "%s"'
        self.__NAME__ = "echo"
        self.requireFlags = True

    def appendFile(self, filePathName=None, fileUpdate=None, backupPathName=None, rerun=False, wait=30, **kwargs):
        """ Verify and update the contents of file
        - :param filePathName:
        - :param fileUpdate:
        - :param backupPathName:
        - :param rerun:
        - :param wait:
        - :param kwargs:
        - :return:
        """

        requirements = {'fileBackup': self.buildFuncWithArgs(self.cp.makeBackup,
                                                             *(filePathName, backupPathName),
                                                             **{'preparser': kwargs.get('preparser'), 'wait': 60})}
        kwargs.update(self.updatekwargs('requirements', requirements, **kwargs))
        kwargs.update(self.updatekwargs('postparser', GenericCmdModule._formatExitCode, **kwargs))
        return self.simpleExecute(command=f'builtin echo "{fileUpdate}" >> {filePathName} 2>&1; echo $?',
                                  commandKey=f'echoAppend{filePathName}', rerun=rerun, wait=wait, **kwargs)

    def replaceFile(self, filePathName=None, fileUpdate=None, rerun=False, wait=30, **kwargs):
        """ Backup and replace the contents of a file
        - :param filePathName:
        - :param fileUpdate:
        - :param rerun:
        - :param wait:
        - :param kwargs:
        - :return:
        """

        fileBackupKwargs = {}
        fileBackupKwargs.update({'preparser': kwargs.get('preparser'), 'wait': 60,
                                 'backupPath': kwargs.get('backupPath'), 'backupExt': kwargs.get('backupExt')})

        requirements = {'fileBackup': self.buildFuncWithArgs(self.cp.makeBackup, *(filePathName,),
                                                             **fileBackupKwargs)}
        kwargs.update(self.updatekwargs('requirements', requirements, **kwargs))
        kwargs.update(self.updatekwargs('postparser', GenericCmdModule._formatExitCode, **kwargs))
        return self.simpleExecute(command=f'builtin echo "{fileUpdate}" > {filePathName} 2>&1; echo $?',
                                  commandKey=f'echoReplace{filePathName}', rerun=rerun, wait=wait, **kwargs)

    def makeFile(self, filePathName, fileContents=None, rerun=False, wait=30, **kwargs):
        """ Creates a file
            If fileContents is provided the file will be created to contain that data
        - :param filePathName:
        - :param fileContents:
        - :param rerun:
        - :param wait:
        - :param kwargs:
        - :return:
        """

        kwargs.update(self.updatekwargs('postparser', GenericCmdModule._formatExitCode, **kwargs))
        if fileContents:
            return self.simpleExecute(command=f'builtin echo "{fileContents}" > {filePathName} 2>&1; echo $?',
                                      rerun=rerun, wait=wait, **kwargs)
        return self.simpleExecute(command=f'/bin/touch {filePathName} 2>&1; echo $?' % filePathName,
                                  rerun=rerun, wait=wait, **kwargs)
