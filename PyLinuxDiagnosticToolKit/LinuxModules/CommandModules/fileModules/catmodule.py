#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson, Timothy Nodine

# Version: 0.2.0
# Date: 7/12/16
# Description: This is a module for using the cat command.


import logging
from LinuxModules.genericCmdModule import GenericCmdModule

log = logging.getLogger('catModule')


class catModule(GenericCmdModule):
    """
         catModule class. This class inherits from the GenericCmdModule. It is used to execute the Linux command 'cat'
         on remote machines.
         defaultCmd: cat
         defaultFlags =
    """
    cp = None

    def __init__(self, tki, *args, **kwargs):
        log.info("Creating cat module.")
        super(catModule, self).__init__(tki=tki)
        self.cp = self.tki.modules.cp
        self.defaultCmd = '/bin/cat '
        self.defaultKey = "cat%s"
        self.defaultFlags = "%s"
        self.__NAME__ = 'cat'
        self.requireFlags = True

    def appendFile(self, filePathName=None, fileUpdate=None, backupPathName=None, rerun=False, wait=30, **kwargs):
        """
            Verify and update the contents of file
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
                                                             **{'preparser': kwargs.get('preparser'),
                                                                'rerun': kwargs.get('backupRerun', True), 'wait': 30})}
        kwargs.update(self.updatekwargs('preparser', catModule._ExportFunction, **kwargs))
        kwargs.update(self.updatekwargs('completiontask', catModule._unsetFunction, **kwargs))
        kwargs.update(self.updatekwargs('requirements', requirements, **kwargs))
        kwargs.update(self.updatekwargs('postparser', GenericCmdModule._formatExitCode, **kwargs))
        return self.simpleExecute(command=f'(\n/bin/cat <<\'CATAPPENDEOF\'\n{fileUpdate}'
                                          f'\nCATAPPENDEOF\n) >> {filePathName} 2>&1; echo $?',
                                  commandKey='catAppend%s' % filePathName, rerun=rerun, wait=wait, **kwargs)

    def replaceFile(self, filePathName=None, fileUpdate=None, rerun=False, wait=30, **kwargs):
        """
            Backup and replace the contents of a file
        - :param filePathName:
        - :param fileUpdate:
        - :param rerun:
        - :param wait:
        - :param kwargs:
        - :return:
        """

        fileBackupKwargs = {'preparser': kwargs.get('preparser'), 'wait': 60, 'rerun': kwargs.get('backupRerun', False),
                            'backupPath': kwargs.get('backupPath'), 'backupExt': kwargs.get('backupExt')}

        requirements = {'fileBackup': self.buildFuncWithArgs(self.cp.makeBackup, *(filePathName,),
                                                             **fileBackupKwargs)}
        kwargs.update(self.updatekwargs('preparser', catModule._ExportFunction, **kwargs))
        kwargs.update(self.updatekwargs('completiontask', catModule._unsetFunction, **kwargs))
        kwargs.update(self.updatekwargs('requirements', requirements, **kwargs))
        kwargs.update(self.updatekwargs('postparser', GenericCmdModule._formatExitCode, **kwargs))
        return self.simpleExecute(command=f'(\n/bin/cat <<\'CATREPLACEEOF\'\n{fileUpdate}'
                                          f'\nCATREPLACEEOF\n) > {filePathName} 2>&1; echo $?',
                                  commandKey='catReplace%s' % filePathName, rerun=rerun, wait=wait, **kwargs)

    def makeFile(self, filePathName, fileContents=None, rerun=False, wait=30, **kwargs):
        """
            Creates a file
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
            kwargs.update(self.updatekwargs('preparser', catModule._ExportFunction, **kwargs))
            kwargs.update(self.updatekwargs('completiontask', catModule._unsetFunction, **kwargs))
            return self.simpleExecute(command=f'(\n/bin/cat <<\'CATMAKEEOF\'\n{fileContents}'
                                              f'\nCATMAKEEOF\n) > {filePathName} 2>&1; echo $?',
                                      rerun=rerun, wait=wait, **kwargs)
        return self.simpleExecute(command=f'/bin/touch {filePathName} 2>&1; echo $?', rerun=rerun, wait=wait, **kwargs)

    @staticmethod
    def _ExportFunction(*args, **kwargs):
        this = kwargs.get("this")
        command = "export HISTSIZE=0"
        sshCon = this.EnvironmentObject
        sshCon.environmentChange(command)

    @staticmethod
    def _unsetFunction(*args, **kwargs):
        this = kwargs.get("this")
        command1 = "unset HISTSIZE"
        sshCon = this.EnvironmentObject
        sshCon.environmentChange(command1)
