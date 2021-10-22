#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Ryan Henrichson

# Version: 0.1
# Date: 9/23/20
# Description: This uses the Paramiko's implementation of SFTP too preform put and get actions on a remote machine in
# the FTP style.


import logging
from PyLinuxDiagnosticToolKit.libs.LDTKExceptions import exceptionDecorator as expDec
from paramiko.sftp_client import SFTPClient
from paramiko.sftp_attr import SFTPAttributes
from paramiko import SSHClient
from typing import Union, AnyStr, IO, Optional, Any, List, Type

# logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(message)s',
#                     level=logging.DEBUG)
log = logging.getLogger('SFTP Client')


def put(ssh, files: Union[AnyStr, IO[bytes]], remotepath: AnyStr) -> None:
    """ This uses the 'putfo' method from SFTPClient in the Paramiko package.

    - :param ssh: (Paramiko ssh object)
    - :param files: (AnyStr/File/IO Object)
    - :param remotepath: (AnyStr)
    - :return: None
    """

    log.debug(f'About to pass the following file[s]: {files} - to the remote path of: [{remotepath}]')
    with ssh.get_transport().open_sftp_client() as sftp:
        sftp.putfo(files, remotepath)


def get(ssh, remotefile: AnyStr, localpath: Union[AnyStr, IO[bytes]]) -> None:
    """ This uses the 'getfo' method from SFTPClient in the Paramiko package.

    - :param ssh: (Paramiko ssh object)
    - :param remotefile: (AnyStr)
    - :param localpath: (AnyStr/File/IO Object)
    - :return: None
    """

    log.debug(f'About to get the following file: {remotefile} - and saving it to: [{localpath}]')
    with ssh.get_transport().open_sftp_client() as sftp:
        sftp.getfo(remotefile, localpath)


class SFTPChannel(object):
    """
        This is a wrapper for the two functions inside this package. The 'put' and 'get' functions. It is designed to
        be LDTK aware and to handle getting the correct SSH channel.
    """

    ldtk = None
    ssh: SSHClient = None
    sftp: SFTPClient = None

    def __init__(self, ldtk):
        """ This requires the LDTK and uses it to get the main SSH channel by default. Or it uses a provided SSHChannel.

        - :param ldtk: A ToolKitInterface object. Used by the 'property' sshCon to pull the main SSH channel.
        """
        self.ldtk = ldtk
        self.ssh = ldtk.sshCon.ssh

    def __enter__(self):
        self.openSFTP()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.closeSFTP()

    def openSFTP(self, autoLogin: bool = None, reopen: Optional[bool] = False) -> SFTPClient:
        """ Returns the current sftp or creates an sftp client.

        :param autoLogin: (bool) - This will attempt to have the LTDK create a Paramiko connection if it isn't connected
        :param reopen: (bool)
        :return: (SFTPClient)
        """

        if self.sftp is not None and not reopen:
            return self.sftp
        if autoLogin is None:
            autoLogin = self.ldtk.auto_login
        if self.ldtk.checkConnection() is False and autoLogin:
            self.ldtk.createConnection()
        self.ssh = self.ldtk.sshCon.ssh
        self.sftp = self.ssh.get_transport().open_sftp_client()
        return self.sftp

    def closeSFTP(self) -> None:
        """ This closes the SFTP connection and removes the 'sftp' class variable.

        - :return: None
        """

        if self.sftp:
            self.sftp.close()
        del self.sftp

    @expDec(returnOnExcept=False)
    def put(self, files: Union[AnyStr, IO[bytes]], remotepath: AnyStr, autoLogin: bool = None) -> Any:
        """ Take a local file or multiple files and upload it to a remote location.

        - :param files: single or list of files to upload for a file like object
        - :param remotepath: a full path to a remote directory
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (True)
        """

        return self.openSFTP(autoLogin).putfo(files, remotepath)

    @expDec(returnOnExcept=False)
    def get(self, remotefile: AnyStr, localpath: Union[AnyStr, IO[bytes]], autoLogin: bool = None) -> Any:
        """ Takes a file from a remote server and place it directly on the local machine.

        - :param remotefile: A full path to a file located on a remote machine
        - :param localpath: A full path to a local directory or file like object
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (True)
        """

        return self.openSFTP(autoLogin).getfo(remotefile, localpath)

    @expDec(returnOnExcept=False)
    def chdir(self, path: AnyStr, autoLogin: bool = None) -> Optional[bool]:
        """ This uses the 'chdir' method from the SFTPClient class in the Paramiko package.

        - :param path: (str) – new current working directory
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (bool)
        """

        return self.openSFTP(autoLogin).chdir(path)

    @expDec(returnOnExcept=False)
    def chmod(self, path: AnyStr, mode: int, autoLogin: bool = None) -> Optional[bool]:
        """ This uses the 'chmod' method from the SFTPClient class in the Paramiko package.

        - :param path: (str) – path of the target file or directory
        - :param mode: (int) - new permissions
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (bool)
        """

        return self.openSFTP(autoLogin).chmod(path, mode)

    @expDec(returnOnExcept=False)
    def chown(self, path: AnyStr, uid: int, gid: int, autoLogin: bool = None) -> Optional[bool]:
        """ This uses the 'chown' method from the SFTPClient class in the Paramiko package.

        - :param path: (str) – path of the target file or directory
        - :param uid: (int) - new owner’s uid
        - :param gid: (int) – new group id
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (bool)
        """

        return self.openSFTP(autoLogin).chown(path, uid, gid)

    @expDec(returnOnExcept="")
    def getcwd(self) -> AnyStr:
        """ This uses the 'getcwd' method from the SFTPClient class in the Paramiko package.

        - :return: (str) current working directory
        """

        return self.openSFTP(False).getcwd()

    @expDec(returnOnExcept=[])
    def listdir(self, path: AnyStr = '.', autoLogin: bool = None) -> List:
        """ This uses the 'listdir' method from the SFTPClient class in the Paramiko package.

        - :param path: (str) Default '.' – path of the target directory
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (List)
        """

        return self.openSFTP(autoLogin).listdir(path)

    @expDec(returnOnExcept=False)
    def lstat(self, path: AnyStr, autoLogin: bool = None) -> Type[SFTPAttributes]:
        """ This uses the 'lstat' method from the SFTPClient class in the Paramiko package.
            This differs from stat by not following symbolic links.

        - :param path: (str) – path of the target file
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (SFTPAttributes object)
        """

        return self.openSFTP(autoLogin).lstat(path)

    @expDec(returnOnExcept=False)
    def stat(self, path: AnyStr, autoLogin: bool = None) -> Type[SFTPAttributes]:
        """ This uses the 'stat' method from the SFTPClient class in the Paramiko package.

        - :param path: (str) – path of the target file
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (SFTPAttributes object)
        """

        return self.openSFTP(autoLogin).stat(path)

    @expDec(returnOnExcept=False)
    def mkdir(self, path: AnyStr, mode: int = 511, autoLogin: bool = None) -> Optional[bool]:
        """ This uses the 'mkdir' method from the SFTPClient class in the Paramiko package.

        - :param path: (str) – name of the folder to create
        - :param mode: (int) Default 511 – permissions (posix-style) for the newly-created folder
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (bool)
        """

        return self.openSFTP(autoLogin).mkdir(path, mode)

    @expDec(returnOnExcept="")
    def readlink(self, path: AnyStr, autoLogin: bool = None) -> AnyStr:
        """ This uses the 'readlink' method from the SFTPClient class in the Paramiko package.

        - :param path: (str) – path of the symbolic link file
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (str)
        """

        return self.openSFTP(autoLogin).readlink(path)

    @expDec(returnOnExcept=False)
    def remove(self, path: AnyStr, autoLogin: bool = None) -> Any:
        """ This uses the 'remove' method from the SFTPClient class in the Paramiko package.

        - :param path: (str) – path (absolute or relative) of the file to remove
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return: (bool)
        """

        return self.openSFTP(autoLogin).remove(path)

    @expDec(returnOnExcept=False)
    def rename(self, oldpath: AnyStr, newpath: AnyStr, autoLogin: bool = None) -> Any:
        """ This uses the 'rename' method from the SFTPClient class in the Paramiko package.
            This method implements ‘standard’ SFTP RENAME behavior; those seeking the OpenSSH “POSIX rename”
            extension behavior should use posix_rename.

        - :param oldpath: (str) – existing name of the file or folder
        - :param newpath: (str) – new name for the file or folder, must not exist already
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return:
        """

        return self.openSFTP(autoLogin).rename(oldpath, newpath)

    @expDec(returnOnExcept=False)
    def posix_rename(self, oldpath: AnyStr, newpath: AnyStr, autoLogin: bool = None) -> Any:
        """ This uses the 'posix_rename' method from the SFTPClient class in the Paramiko package.

        - :param oldpath: (str) – existing name of the file or folder
        - :param newpath: (str) – new name for the file or folder, will be overwritten if it already exists
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return:
        """

        return self.openSFTP(autoLogin).posix_rename(oldpath, newpath)

    @expDec(returnOnExcept=False)
    def rmdir(self, path: AnyStr, autoLogin: bool = None) -> Any:
        """ This uses the 'rmdir' method from the SFTPClient class in the Paramiko package.

        - :param path: (str) – name of the folder/directory to remove
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return:
        """

        return self.openSFTP(autoLogin).rmdir(path)

    @expDec(returnOnExcept=False)
    def symlink(self, source: AnyStr, dest: AnyStr, autoLogin: bool = None) -> Any:
        """ This uses the 'symlink' method from the SFTPClient class in the Paramiko package.

        - :param source: (str) – path of the original file
        - :param dest: (str) – path of the newly created symlink
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return:
        """

        return self.openSFTP(autoLogin).symlink(source, dest)

    @expDec(returnOnExcept=False)
    def truncate(self, path: AnyStr, size: int, autoLogin: bool = None) -> Any:
        """ This uses the 'truncate' method from the SFTPClient class in the Paramiko package.

        - :param path: (str) – path of the file to modify
        - :param size: (int) – the new size of the file
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return:
        """

        return self.openSFTP(autoLogin).truncate(path, size)

    @expDec(returnOnExcept=False)
    def unlink(self, path: AnyStr, autoLogin: bool = None) -> Any:
        """ This uses the 'unlink' method from the SFTPClient class in the Paramiko package.

        - :param path: (str) – path (absolute or relative) of the file to remove
        - :param autoLogin: (bool) - Controls if this will attempt a connection if one isn't present.
        - :return:
        """

        return self.openSFTP(autoLogin).unlink(path)
