#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.5.0
# Date: 12/10/14
# Description: This is the base class for sshConnector ToolKit. The sshConnector ToolKit is the backend necessary
# for the Linux Diagnostic Tool Kit to allow it to be able to connect via SSH to Linux Machines.
# This is the base class inherited by other classes within the sshConnect package. This class servers only one purpose,
# too connect to a Linux machine via SSH.

import socket
import logging
import traceback
import paramiko
from paramiko import PKey, SSHClient, Channel
from paramiko.transport import Transport
from paramiko.proxy import ProxyCommand
from io import StringIO, TextIOWrapper
from sshConnector.sshLibs.sshChannelEnvironment import sshChannelWrapper, sshEnvironment, EnvironmentControls
from PyLinuxDiagnosticToolKit.libs.LDTKExceptions import LDTKSSHException, SSHExceptionAuth, SSHExceptionConn, \
    SSHExceptionUnknown, SSHExceptionChannel
from typing import AnyStr, Optional, Union


# turn off debug for paramiko
_ptlog = logging.getLogger('paramiko.transport')
_ptlog.setLevel(logging.WARNING)
_pclog = logging.getLogger('paramiko.channel')
_pclog.setLevel(logging.WARNING)
log = logging.getLogger('sshConnect')


class sshConnect(object):

    ssh: SSHClient = None
    _mainEnvironment: Channel = None
    arguments = None

    def __init__(self, arguments, **kwargs):
        """ The normal use of this init function is to have args passed and to make a connection.
            This class should be called around a 'try' block if args are passed.

        - :param arguments: (NameSpaceDict)
        - :param kwargs: This is only here to satisfy recommended class inheritance issues.
        """

        log.debug("Creating the sshConnect class")

        self.arguments = arguments
        self.host = arguments.host
        self.port = arguments.port or 22
        self.key = arguments.key
        self.username = arguments.username
        self.password = arguments.password
        self.root = arguments.root
        self.rootLogin = sshConnect.processRootLogin(arguments.rootLogin)
        self.rootpwd = arguments.rootpwd
        self.connTimeout = arguments.connTimeout
        self.proxyUser = arguments.proxyUser
        self.proxyServer = arguments.proxyServer
        self.runTimeout = arguments.runTimeout
        self.firstBitTimeout = arguments.firstBitTimeout
        self.betweenBitTimeout = arguments.betweenBitTimeout
        self.delay = arguments.delay
        self.ioTimeout = arguments.ioTimeout
        self.ssh = self.createConn()
        self._mainEnvironment = self._openChannel(self._createTransport())
        self._mainEnvironment.__MAIN__ = True

    # noinspection PyTypeChecker
    def createConn(self, host: Optional[AnyStr] = None, port: Optional[int] = None, username: Optional[AnyStr] = None,
                   password: Optional[AnyStr] = None, connTimeout: Optional[float] = None) -> SSHClient:
        """ Creates SSH Object and Opens Connection To Server All the parameters are optional. If a parameter isn't
            passed it will pull from the Class variable of the same name. If the parameter is passed it will override
            the class variable before connecting.

        - :param host: (str) - Optional hostname/ip address of the box.
        - :param port: (int) - Optional port to attempt to make the tcp connection.
        - :param username: (str) - Optional and will use the class stored variable if not passed.
        - :param password: (str) - Optional and will use the class stored variable if not passed.
        - :param connTimeout: (float) - Optional and will use the class stored variable if not passed.
        - :return: Paramiko SSHClient object. Otherwise known as SSH Connection.
        """

        ssh = None

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            if host:
                self.host = host
            if port:
                self.port = port
            if username:
                self.username = username
            if password:
                self.password = password
            if connTimeout:
                self.connTimeout = connTimeout

            ssh.connect(self.host,
                        port=int(self.port),
                        pkey=self._handleSSHKey(self.key, self.password),
                        username=self.username,
                        password=self.password,
                        timeout=float(self.connTimeout),
                        look_for_keys=False,
                        allow_agent=False,
                        banner_timeout=60.0,
                        sock=self._makeSockProxy())
        except socket.error as e:
            if ssh:
                ssh.close()
            raise LDTKSSHException('Connection Error for User %s: %s' % (self.username, e)) from e
        except (paramiko.AuthenticationException, paramiko.BadAuthenticationType, paramiko.BadHostKeyException,
                paramiko.PasswordRequiredException, paramiko.ssh_exception.PartialAuthentication) as e:
            if ssh:
                ssh.close()
            raise SSHExceptionAuth('Authentication Error for User %s: %s' % (self.username, e)) from e
        except (paramiko.ssh_exception.ConfigParseError, paramiko.ProxyCommandFailure,
                paramiko.ssh_exception.CouldNotCanonicalize, paramiko.ssh_exception.NoValidConnectionsError) as e:
            raise SSHExceptionConn('Could not connect to remove machine for User %s: %s' % (self.username, e)) from e
        except paramiko.SSHException as e:
            if ssh:
                ssh.close()
            raise SSHExceptionUnknown('Generic Paramiko Exception for User %s: %s' % (self.username, e)) from e
        except Exception as e:
            if ssh:
                ssh.close()
            raise LDTKSSHException('Unknown Error for User %s: %s' % (self.username, e)) from e
        else:
            self.ssh = ssh
            return self.ssh

    def checkConnection(self, sshChannel: Optional[Channel] = None) -> bool:
        """ Creates ssh key object or returns None.

        - :param: (Channel): None or Paramiko channel
        - :return: (bool)
        """

        if sshChannel is None:
            sshChannel = self.mainEnvironment

        if self.ssh is None:
            return False

        if not sshChannel:
            return False

        return sshChannel.get_transport().is_active() and not sshChannel.closed

    def disconnect(self) -> None:
        """ Get the underlying transport for the active channel and close it out,
            thereby closing the channel and all associated channels to that transport.
        """

        try:
            self.mainEnvironment.get_transport().close()
            self.ssh.close()
        except Exception as e:
            log.error(f'Disconnect failed: {e}')
            log.debug(f'[DEBUG]: Disconnect failure reason: {traceback.format_exc()}')

    def _makeSockProxy(self) -> Optional[ProxyCommand]:
        """ Use a proxy to ssh into a server.

        - :return: (Socket like object)
        """

        if not self.proxyUser or not self.proxyServer:
            return None
        controlPath = '~/.ssh/master-%r@%h:%p'
        flags = "-F '/dev/null' -o ControlMaster='auto' -o ControlPath='%s' -o TCPKeepAlive='yes' " \
                "-o ServerAliveInterval=300" % controlPath
        proxycommand = f"ssh {flags} -A {self.proxyUser}@{self.proxyServer} 'nc {self.host} {self.port}'"
        try:
            return paramiko.ProxyCommand(proxycommand)
        except Exception as e:
            log.debug(f'Error occurred setting up proxy command: {e}')
            log.debug(f"[DEBUG] for _makeSockProxy: {traceback.format_exc()}")
            raise SSHExceptionConn(f'Failed setting up SSH ProxyCommand: {e}') from e

    def _createTransport(self) -> Optional[Transport]:
        """
            Creates the transport object.
        """
        if not self.ssh:
            raise LDTKSSHException('There is not SSH object which implies Paramiko is not connected!')
        try:
            sshTransport = self.ssh.get_transport()
            sshTransport.set_keepalive(10)
            sshTransport.use_compression()
            return sshTransport
        except Exception as e:
            log.debug(f'Error occurred creating transport object: {e}')
            log.debug(f"[DEBUG] for _createTransport: {traceback.format_exc()}")
            if self.checkConnection():
                self.ssh.close()
            raise SSHExceptionChannel(f'Failed create SSH Transport: {e}') from e

    def _openChannel(self, sshTransport: Transport, **kwargs) -> EnvironmentControls:
        """ Creates SSH Channel using existing SSH Transport Object.

        - :return: (Channel)
        """

        try:
            channel = sshTransport.open_session()
            channel.settimeout(self.ioTimeout)
            channel.get_pty()
            channel.invoke_shell()
            kwargs.update({'sshParent': self})
            return EnvironmentControls(sshEnvironment(sshChannelWrapper(channel, **kwargs), **kwargs), **kwargs)
        except paramiko.ChannelException as e:
            log.debug(f'Error occurred when opening channel: {e}')
            log.debug(f"[DEBUG] for _openChannel: {traceback.format_exc()}")
            if sshTransport:
                sshTransport.close()
            raise SSHExceptionChannel(f'Failed to open SSH Channel: {e}') from e

    @staticmethod
    def _handleSSHKey(key: Union[AnyStr, TextIOWrapper], passphrase: AnyStr = None) -> Optional[PKey]:
        """ Creates ssh key object or returns None.

        - :param key: (Str/File Like Object)
        - :param passphrase: (str) default None
        - :return: (PKey base object)
        """

        if not key:
            return None

        try:
            sshKeyFile = StringIO()
            if isinstance(key, TextIOWrapper):
                sshKeyFile.write(key.read())
            else:
                sshKeyFile.write(key)
        except Exception as e:
            log.debug("There was a failure to read the provied SSH key file!")
            log.debug(f"[DEBUG] for _handleSSHKey: {traceback.format_exc()}")
            return None

        def _rsaHelper():
            try:
                sshKeyFile.seek(0)
                return paramiko.RSAKey.from_private_key(sshKeyFile, password=passphrase)
            except Exception as e:
                log.error(f'RSA Key failed: {e}')
                log.debug(f"[DEBUG] for _rsaHelper: {traceback.format_exc()}")

        def _dssKey():
            try:
                sshKeyFile.seek(0)
                return paramiko.DSSKey.from_private_key(sshKeyFile, password=passphrase)
            except Exception as e:
                log.error(f'DSS Key failed: {e}')
                log.debug(f"[DEBUG] for _dssKey: {traceback.format_exc()}")

        def _ECDSAKey():
            try:
                sshKeyFile.seek(0)
                return paramiko.ECDSAKey.from_private_key(sshKeyFile, password=passphrase)
            except Exception as e:
                log.error(f'ECDSA Key failed: {e}')
                log.debug(f"[DEBUG] for _ECDSAKey: {traceback.format_exc()}")

        sshKey = _rsaHelper()
        if sshKey:
            return sshKey
        sshKey = _dssKey()
        if sshKey:
            return sshKey
        sshKey = _ECDSAKey()
        if sshKey:
            return sshKey

        log.warning(f'Unable to translate SSH private SSH key for use.')
        return None

    @staticmethod
    def processRootLogin(loginMethod: str) -> str:
        if 'sudo' in loginMethod:
            return '/usr/bin/sudo -k; /usr/bin/sudo su -'
        return 'su -'

    @property
    def mainEnvironment(self):
        if self.ssh is None:
            return None
        if self._mainEnvironment is None:
            self._mainEnvironment = self._openChannel(self._createTransport())
            self._mainEnvironment.__MAIN__ = True
        return self._mainEnvironment
