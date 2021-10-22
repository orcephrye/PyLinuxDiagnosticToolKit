#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson

# Version: 0.2
# Date: 10/05/17
# Description: This uses the LDTKscp.py third party module in combination with our Paramiko implementation to
# preform scp style file uploads.


import logging
from PyLinuxDiagnosticToolKit.libs.LDTKExceptions import exceptionDecorator as expDec
from sshConnector.sshLibs.LDTKscp import SCPClient
from paramiko import SSHClient
from typing import Any, Optional, AnyStr


# logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(message)s',
#                     level=logging.DEBUG)
log = logging.getLogger('SCP Client')


def put(ssh, files: Any, remotepath: AnyStr, recursive: Optional[bool] = False,
        preserve_times: Optional[bool] = False) -> None:
    """ This uses the 'put' method within the SCPClient class found in the LDTKscp.py package.

    - :param ssh: (Paramiko ssh object)
    - :param files: (AnyStr/File/IO Object)
    - :param remotepath: (AnyStr)
    - :param recursive: transfer files and directories recursively
    - :param preserve_times: preserve mtime and atime of transferred files and directories
    - :return: None
    """

    log.debug(f'About to pass the following file[s]: {files} - to the remote path of: [{remotepath}]')
    with SCPClient(ssh.get_transport()) as scpChannel:
        scpChannel.put(files, remotepath, recursive, preserve_times)


def get(ssh, remotefile: AnyStr, localpath: AnyStr, recursive: Optional[bool] = False,
        preserve_times: Optional[bool] = False) -> None:
    """ This uses the 'get' method within the SCPClient class found in the LDTKscp.py package.

    - :param ssh: (Paramiko ssh object)
    - :param remotefile: (AnyStr)
    - :param localpath: (AnyStr)
    - :param recursive: transfer files and directories recursively
    - :param preserve_times: preserve mtime and atime of transferred files and directories
    - :return: None
    """

    log.debug(f'About to get the following file: {remotefile} - and saving it to: [{localpath}]')
    with SCPClient(ssh.get_transport()) as scpChannel:
        scpChannel.get(remotefile, localpath, recursive, preserve_times)


class SCPChannel(object):
    """
        This is a wrapper for the two methods in the SCPClient class from the LDTKscp.py package. It is designed to
        be LDTK aware and to handle getting the correct SSH channel. While the package functions 'put' and 'get'
        wrap the third party SCPClient package.
    """

    ldtk = None
    ssh: SSHClient = None
    scp: SCPClient = None

    def __init__(self, ldtk):
        """ This requires the LDTK and uses it to get the main SSH channel by default. Or it uses a provided SSHChannel.

        - :param ldtk: A ToolKitInterface object. Used by the 'property' sshCon to pull the main SSH channel.
        """

        self.ldtk = ldtk
        self.ssh = ldtk.sshCon.ssh

    def __enter__(self):
        self.openSCP()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.closeSCP()

    def openSCP(self, autoLogin: bool = None, reopen: Optional[bool] = False) -> SCPClient:
        if self.scp is not None and not reopen:
            return self.scp
        if autoLogin is None:
            autoLogin = self.ldtk.auto_login
        if self.ldtk.checkConnection() is False and autoLogin:
            self.ldtk.createConnection()
        self.ssh = self.ldtk.sshCon.ssh
        self.scp = SCPClient(self.ssh.get_transport())
        return self.scp

    def closeSCP(self) -> None:
        if self.scp:
            self.scp.close()
        del self.scp

    @expDec(returnOnExcept=False)
    def put(self, files: Any, remotepath: AnyStr, autoLogin: bool = None) -> bool:
        """ Take a local file or multiple files and upload it to a remote location.

        - :param files: single or list of files to upload
        - :param remotepath: a full path to a remote directory
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (True)
        """

        return self.openSCP(autoLogin).put(files, remotepath)

    @expDec(returnOnExcept=False)
    def get(self, remotefile: AnyStr, localpath: AnyStr, autoLogin: bool = None) -> bool:
        """ Takes a file from a remote server and place it directly on the local machine.

        - :param remotefile: A full path to a file located on a remote machine
        - :param localpath: A full path to a local directory
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (True)
        """

        return self.openSCP(autoLogin).put(remotefile, localpath)
