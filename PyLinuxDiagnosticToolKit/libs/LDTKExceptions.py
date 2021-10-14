#!/usr/bin/env python
# -*- coding=utf-8 -*-

# Author: Tim Nodine, Ryan Henrichson

# Version: 0.1
# Date: 06-09-2016
# Description: This is a place holder for all the custom exceptions used by LDTK resources.


import traceback
import logging
from functools import wraps
from typing import Optional, Any


# logging.basicConfig(format='%(asctime)s %(levelname)s %(name)s %(funcName)s %(lineno)s %(message)s',
#                     level=logging.DEBUG)
log = logging.getLogger('LDTK_Decorator')


def exceptionDecorator(returnOnExcept: Optional[Any] = None, raiseExcept: Optional[bool] = False) -> Any:
    def wrapper(func):
        """ Decorator for exception handling """
        @wraps(func)
        def wrapped(*args, **kwargs):
            try:
                try:
                    args_repr = [repr(a) for a in args]
                    kwargs_repr = ["{%s}={%s}" % (k, repr(v)) for k, v in kwargs.items()]
                    signature = ", ".join(args_repr + kwargs_repr)
                    log.info(f'Calling function <{func.__name__}> with signature: {signature}')
                except:
                    log.info(f'Calling function <{func.__name__}>:')
                return func(*args, **kwargs)
            except Exception as e:
                log.error(f'An exception occurred in {func.__name__}: {e}')
                log.debug(f'[DEBUG] exception in {func.__name__}: {traceback.format_exc()}')
                if raiseExcept:
                    if isinstance(returnOnExcept, Exception):
                        raise returnOnExcept
                    elif type(returnOnExcept) is type and issubclass(returnOnExcept, BaseException):
                        raise returnOnExcept() from e
                    raise
                return returnOnExcept
        return wrapped
    return wrapper


class LDTKBaseException(Exception):
    """ Used as the Default Exception for PyLinuxDiagnosticToolKit specific errors """
    pass


class LDTKCommandException(LDTKBaseException):
    """ Used specifically as part of the CommandContainer class to record errors in executing commands """
    pass


class LDTKSSHException(LDTKBaseException):
    """ Used to wrap Paramiko SSH errors into other SSH related errors built into PyLinuxDiagnosticToolKit """
    pass


class SSHExceptionAuth(LDTKSSHException):
    """  paramiko.AuthenticationException """
    pass


class SSHExceptionConn(LDTKSSHException):
    """  socket.error """
    pass


class SSHExceptionUnknown(LDTKSSHException):
    """  sshConnector unknown errors """
    pass


class SSHExceptionChannel(LDTKSSHException):
    """  paramkio.ChannelException """
    pass


class LDTKBufferException(LDTKSSHException):
    """ Generic exception for handling the buffer inherited by other more specific Buffer related Exceptions """
    pass


class ClosedBufferException(LDTKSSHException):
    """ The Buffer closed unexpectedly """
    pass


class TimeToFirstBitException(LDTKSSHException):
    """ sshBufferControl._bufferTimeToFirstBit method when it takes too long to get the first bit from the buffer """
    pass


class RecvReady(LDTKSSHException):
    """  sshBufferControl failure to detect the prompt after a certain amount of time """
    pass


class BetweenBitException(LDTKSSHException):
    """ sshBufferControl._bufferBetweenBitWait method when it takes too long to get the next bit from the buffer """
    pass


class LDTKUserException(LDTKBaseException):
    """ Used for handling user escalations/escalations and environment changes. """
    pass


class BecomeUserException(LDTKUserException):
    """  sshUserControl failure to become user """
    pass


# Command and Command Container/Object Exceptions
class CommandObjectException(LDTKBaseException):
    """ Custom exceptions collector that outputs a single combine exception """

    baseException = None

    def __init__(self, *args, **kwargs):
        self.baseException = kwargs.pop('baseException', None) or None
        if isinstance(self.baseException, CommandObjectException) or not type(self.baseException) is list:
            self.baseException = [self.baseException.__repr__().replace(',)', ')')]
        super(CommandObjectException, self).__init__(*args)


class RequirementsException(CommandObjectException):
    pass


class PreparserException(CommandObjectException):
    pass


class ExecutionException(CommandObjectException):
    pass


class PostParserException(CommandObjectException):
    pass


class SetFailureException(CommandObjectException):
    pass


class CompletionTaskException(CommandObjectException):
    pass


class TimeoutException(CommandObjectException):
    pass


class DataFormatException(CommandObjectException):
    pass


class ForceCompleteException(CommandObjectException):
    pass
