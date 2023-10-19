#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.5.0
# Date: 12/10/14
# Description: This is the second class in the sshConnector chain. Here we are simply adding the ability to run commands
# on a Linux box via SSH. This is necessary to progress to user management and threading.


import logging
import socket
import re
import time
import warnings
import traceback
from time import sleep
from sshConnector.sshConnect import sshConnect as sshCon
from paramiko import Channel
from sshConnector.sshLibs.sshChannelEnvironment import EnvironmentControls
from io import StringIO
from PyLinuxDiagnosticToolKit.libs.LDTKExceptions import ClosedBufferException, RecvReady, BetweenBitException, \
    TimeToFirstBitException, SSHExceptionConn
from typing import Any, AnyStr, Optional, Union, Tuple, Type


log = logging.getLogger('sshBufferControl')
warnings.filterwarnings("ignore", category=ResourceWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)


class sshBufferControl(sshCon):
    promptTextTuple = ('$', '>', '#', '@', ']', '~')
    escapeChars = re.compile(r'((\x9B|\x1B\[)[0-?]*[ -\/]*[@-~]|[\x00|\x0e-\x1f])')

    def __init__(self, arguments, **kwargs):
        """ init function for sshBufferControl.

        - :param arguments: (NameSpaceDict)
        - :param kwargs: This is only here to satisfy recommended class inheritance issues.
        """

        super(sshBufferControl, self).__init__(arguments, **kwargs)

    def executeOnEnvironment(self, environment: EnvironmentControls, cmd: AnyStr,
                             prompt: Optional[Union[AnyStr, Tuple]] = None, unsafe: bool = False,
                             reCapturePrompt: bool = False, **kwargs) -> AnyStr:
        """ This injects the string into the buffer while trying to ensure there is a prompt. As the prompt is used to
            quickly determine the end of the buffer. The prompt can be a string or it can be a tuple of strings that
            attempt to match the end of the line. Unsafe ignores the prompt and simply executes the command and only
            waits a short time before leaving not caring if it got output of the command. This is unsafe as it can leave
            a buffer open ready to dump more output. This method also takes the output from the command and attempts to
            decode it to utf-8 while removing all null and escape characters.

        - :param channel: (Paramiko Channel/sshEnvironment) -
        - :param cmd: (str) -
        - :param prompt: (tuple or str) -
        - :param unsafe: (bool) default False -
        - :param kwargs:
        - :return: (str)
        """

        def _parseOutput(tmpOut, tmpPrompt):
            try:
                # print(f'=== parseOutput in executeOnEnvironment\n{tmpOut}\n')
                tmpOut = sshBufferControl._decodeStringEscape(tmpOut)
            except (UnicodeDecodeError, UnicodeEncodeError) as e:
                log.error(f'ERROR: for method _parseOutput: {e}')
                log.debug(f"[DEBUG] for _parseOutput: {traceback.format_exc()}")
                try:
                    tmpOut = sshBufferControl._decodeStringEscape(tmpOut, encoding='latin1')
                except (UnicodeDecodeError, UnicodeEncodeError) as e:
                    if 'CMDSTART' in tmpOut and 'CMDEND' in tmpOut:
                        log.debug('Another parse failure within _parseOutput method. However, ignoring sense string'
                                  'contains CMDSTART and CMDEND this may be parsed successfully by CC')
                    else:
                        raise e
            tmpOut = sshBufferControl.escapeChars.sub('', tmpOut).strip()
            return tmpOut.replace(tmpPrompt, '').replace(cmd, '').strip()

        if not super(sshBufferControl, self).checkConnection(sshChannel=environment):
            log.error("There is not a valid connection.")
            return ''

        log.debug(f"Attempting to exec command[s]: {cmd}")

        out = StringIO()
        output = ""
        if isinstance(prompt, str):
            prompt = sshBufferControl._decodeStringEscape(prompt)
        if prompt is None and unsafe is False:
            prompt = environment.getPrompt(reCapturePrompt=reCapturePrompt)

        try:
            self._bufferControl(environment, cmd, out, prompt=prompt, unsafe=unsafe, **kwargs)
            output = _parseOutput(out.getvalue(), prompt)
        except RecvReady:
            log.error(f"The timeout of {self.runTimeout} was reached while waiting for prompt on buffer.")
            log.debug(f"[DEBUG] for executeOnEnvironment: {traceback.format_exc()}")
            output = _parseOutput(out.getvalue(), prompt)
            environment.close()
        except socket.timeout:
            log.error("Timeout exception found.")
            output = '[COMMAND_IO_LIMIT_TIMED_OUT]'
            environment.close()
        except Exception as e:
            log.error(f'ERROR: generic Exception for method executeOnEnvironment: {e}')
            log.info('This error will be passed onto the Command Container')
            log.debug(f'This error occurred while executing: {cmd}  on: {environment}')
            log.debug(f'[DEBUG] for method executeOnEnvironment: {traceback.format_exc()}')
            raise e
        finally:
            out.truncate(0)
            del out
            # log.debug(f"The output of the cmd: {cmd} is: \n===\n{output}\n===")
            # print(f"The output of the cmd: {cmd} is: \n===\n{output}\n===")
            return output

    def _bufferControl(self, channel: EnvironmentControls, cmd: AnyStr, out: StringIO,
                       prompt: Optional[Union[AnyStr, Tuple]] = False, unsafe: bool = False, **kwargs) -> None:
        """
            Controls Sending and Receiving Data Through Paramiko SSH Channels.
            It is recommended that this method not be touched.
        """
        runTimeout, firstBitTimeout, betweenBitTimeout, delay = self._parseTimeouts(**kwargs)

        try:

            while channel.recv_ready():
                log.debug('There is old data left in the Channel Buffer. Clearing...')
                channel.recv(65536)
                sleep(.1)

            # log.debug(f'Waiting to send for channel: [{cmd}] : [{str(channel)[18:20]}]  Closed: {channel.closed}')
            while channel.send_ready() is not True:
                # log.debug(f"Channel rec: {channel.recv(65536)}")
                if channel.isClosed:
                    log.debug(f'Channel closed while waiting to send command: [{cmd}] : [{str(channel)[18:20]}]')
                    return
                sleep(.1)

            # log.debug(f'Send buffer ready to receive... '
            #           f'For channel: [{cmd}] : [{str(channel)[18:20]}]  Closed: {channel.isClosed}')
            self._bufferSendWait(data=f'{cmd}', channel=channel)

            # loop through and record all data in recv buffer
            # log.debug(f'Receive buffer ready...  Fetching output data from receive buffer for '
            #           f'channel: [{cmd}] : [{str(channel)[18:20]}]  Closed: {channel.isClosed}')
            if prompt:  # if prompt was captured use prompt as terminator
                log.debug(f"Executing on {channel._id} cmd: {cmd} with prompt: {prompt}")
                self._bufferGenerator(channel=channel, out=out, runTimeout=runTimeout,
                                      firstBitTimeout=firstBitTimeout, betweenBitTimeout=betweenBitTimeout,
                                      delay=delay, endText=prompt, cmd=cmd)
            elif unsafe:
                log.debug(f"Executing on {channel._id} cmd: {cmd} with unsafe mode")
                # log.debug(f'Fetching data in unsafe mode for channel: '
                #           f'[{cmd}] : [{str(channel)[18:20]}]  Closed: {channel.closed}')
                sshBufferControl._bufferTimeToFirstBit(channel, time.time() + 1, delay)
                while channel.recv_ready() is True:
                    if channel.isClosed:
                        return
                    out.write(channel.recv(65536).decode('utf-8'))
                    sleep(.1)
            else:
                if 'echo CMDEND' in cmd:
                    endText = 'CMDEND'
                else:
                    endText = ('$', '>', '#', '@', ']', '~')
                log.debug(f"Executing on {channel._id} cmd: {cmd} with END TEXT: {endText}")
                try:
                    self._bufferGenerator(channel=channel, out=out, runTimeout=runTimeout,
                                          firstBitTimeout=firstBitTimeout, betweenBitTimeout=betweenBitTimeout,
                                          delay=delay, endText=endText, cmd=cmd)

                except BetweenBitException:
                    log.debug("noprompt execution has returned a timeout failure for BetweenBit. Ignoring")
                except TimeToFirstBitException:
                    log.debug("noprompt execution has returned a timeout failure for Time To First Bit. Ignoring")

            # log.debug(f'Channel releasing buffer: [{str(channel)[18:20]}]  Closed: {channel.closed}')
        except socket.error as e:
            log.debug(f'An error occurred: {e}')
            channel.get_transport().close()
            raise SSHExceptionConn(f"Connection Error: {e}") from e

    def _capturePrompt(self, channel: Channel, out: StringIO) -> Union[bool, AnyStr]:
        """
            Captures Shell Prompt to be used in _bufferControl.
        """

        log.info(" === Attempting to capture prompt via BufferControl")
        out.truncate(0)
        log.info(f'Capturing Shell Prompt for channel: [{str(channel)[18:20]}]')
        self._bufferControl(channel, ' ', out, unsafe=True)
        # match prompt on the last line of output to account for failed logins
        prompt = out.getvalue().splitlines()
        # log.debug(f" === The prompt raw value is: {prompt}\n")
        if prompt:
            prompt = re.search('[\\w\\W].+', prompt[-1])
        if prompt:
            prompt = prompt.group().strip()
            log.debug(f" === The search prompt value is: {prompt}")
            return sshBufferControl.escapeChars.sub('', sshBufferControl._decodeStringEscape(prompt)).strip()
        return False

    def _passwdWait(self, channel: Channel, out: StringIO, cmd: AnyStr = '', **kwargs) -> Optional[bool]:
        """
            Wait for the password prompt before inputting the password.
        """

        try:
            return self._bufferWait(channel=channel, out=out, runTimeout=kwargs.get("runTimeout", self.runTimeout),
                                    firstBitTimeout=0,
                                    betweenBitTimeout=kwargs.get("betweenBitTimeout", self.betweenBitTimeout),
                                    delay=kwargs.get("delay", self.delay),
                                    endText=('assword', 'assword:') + sshBufferControl.promptTextTuple,
                                    cmd=cmd)
        except BetweenBitException:
            log.debug("_passwdWait execution has returned a timeout failure for BetweenBit. Ignoring")
        except TimeToFirstBitException:
            log.debug("_passwdWait execution has returned a timeout failure for Time To First Bit. Ignoring")
        return None

    def _promptWait(self, channel: Channel, out: StringIO, cmd: AnyStr = '',
                    clear: bool = True, **kwargs) -> Optional[bool]:
        """
            Waits for Login Attempt to Return Prompt.
        """

        try:
            if clear:
                out.truncate(0)
            for _ in range(int(kwargs.get('insertNewLine', 0))):
                sleep(0.01)
                self._bufferControl(channel, '', out, unsafe=True)
            return self._bufferWait(channel=channel, out=out, runTimeout=kwargs.get("runTimeout", self.runTimeout),
                                    firstBitTimeout=0,
                                    betweenBitTimeout=kwargs.get("betweenBitTimeout", self.betweenBitTimeout),
                                    delay=kwargs.get("delay", self.delay),
                                    endText=kwargs.get('endText', sshBufferControl.promptTextTuple), cmd=cmd,
                                    exitOnAnything=True)
        except BetweenBitException:
            log.debug("_promptWait execution has returned a timeout failure for BetweenBit. Ignoring")
        except TimeToFirstBitException:
            log.debug("_promptWait execution has returned a timeout failure for Time To First Bit. Ignoring")
        return False

    def _parseTimeouts(self, **kwargs) -> Tuple[int, int, int, float]:
        """ This parses custom timeouts for different commands running through the sshBufferControl.

        - :param kwargs:
        - :return: (tuple) (int, int, int, float)
        """

        runTimeout = kwargs.get('runTimeout', self.runTimeout)
        firstBitTimeout = kwargs.get('firstBitTimeout', self.firstBitTimeout)
        betweenBitTimeout = kwargs.get('betweenBitTimeout', self.betweenBitTimeout)
        delay = kwargs.get('delay', self.delay)
        if firstBitTimeout > runTimeout:
            firstBitTimeout = int(runTimeout * 0.8)
        if betweenBitTimeout > runTimeout:
            betweenBitTimeout = int(runTimeout * 0.1)
        if delay > int((runTimeout / 5)):
            delay = 0.2
        # log.debug(f'runTimeout: {runTimeout}, firstBitTimeout: {firstBitTimeout}, '
        #           f'betweenBitTimeout: {betweenBitTimeout}, delay: {delay}')
        return runTimeout, firstBitTimeout, betweenBitTimeout, delay

    @staticmethod
    def _decodeStringEscape(s: AnyStr, encoding: AnyStr = 'utf-8') -> AnyStr:
        # print(f'String:\n======\n{s}\n=======\n\n\nString type: {type(s)}\n')

        try:
            return (s.encode('latin1')  # To bytes, required by 'unicode-escape'
                    .decode('unicode-escape')  # Perform the actual octal-escaping decode
                    .encode('latin1')  # 1:1 mapping back to bytes
                    .decode(encoding))  # Decode original encoding`
        except:
            return (s.encode('unicode-escape')
                    .decode('utf-8')
                    .encode('latin1')
                    .decode('unicode-escape')
                    .encode('latin1')
                    .decode(encoding))


    @staticmethod
    def _processString(s: AnyStr, encoding: AnyStr = 'utf-8') -> AnyStr:
        return sshBufferControl.escapeChars.sub('', sshBufferControl._decodeStringEscape(s.strip(), encoding)).strip()

    @staticmethod
    def _bufferTimeToFirstBit(channel: Channel, fbEnd: float, delay: float) -> True:
        """ This is a helper tool used by _bufferGenerator and _bufferWait to use the time to first bit timeout value.
            Please review those method's doc strings for more information.

        - :param channel:
        - :param fbEnd:
        - :param delay:
        - :return:
        """

        while time.time() <= fbEnd:
            if channel.recv_ready() is True:
                return True
            if channel.closed:
                raise ClosedBufferException("Channel closed while attempting to get first bit!")
            sleep(delay)
        raise TimeToFirstBitException("Time to First Bit exceeded timeout: %s" % str(fbEnd))

    @staticmethod
    def _bufferBetweenBitWait(channel: Channel, bbEnd: float, delay: float) -> Any:
        """ This is a helper tool used by _bufferGenerator and _bufferWait to use the betweenBitTimeout value.
            Please review those method's doc strings for more information.

        :param channel: (Channel)
        :param bbEnd: (float)
        :param delay: (float)
        :return:
        """

        while time.time() <= bbEnd:
            try:
                if channel.recv_ready() is True:
                    return channel.recv(65536).decode('utf-8')
            except socket.timeout as e:
                if channel.closed:
                    raise ClosedBufferException("Channel closed while attempting to read from it!") from e
            except Exception as e:
                log.error(f'ERROR: for method _bufferBetweenBitWait: {e}')
                log.debug(f'[DEBUG] for method _bufferBetweenBitWait: {traceback.format_exc()}')
            sleep(delay)
        raise BetweenBitException(f"IO Timeout: waited for {str(bbEnd)}")

    @staticmethod
    def _bufferSendWait(data: AnyStr, channel: EnvironmentControls) -> None:
        try:
            channel.sendall(data)
            channel.sendall('\n')
        except socket.timeout as e:
            if channel.isClosed:
                raise ClosedBufferException('Channel closed while attempting to send data to it!') from e


    @staticmethod
    def _endTextParser(endText: Union[Tuple, AnyStr]) -> Tuple[Type, Union[Tuple, AnyStr]]:
        """ This gets the endTextType so it doens't need to be parsed more then once. If it is a string then it also
            removes escape characters from it. Escape characters can be found in the endtext when the prompt was
            captured as use for the end text.

        :param endText: (Tuple or Str)
        :return: tuple
        """

        endTextType = type(endText)
        # log.debug(f"endText before: {repr(endText)}")
        if endTextType is str:
            endText = sshBufferControl.escapeChars.sub('', endText).strip()
        # log.debug(f"endText after: {repr(endText)}")
        return endTextType, endText

    @staticmethod
    def _endTextAnalyzer(outValue: AnyStr, endText: Union[Tuple, AnyStr],
                         endTextType: Type, cmd: Optional[AnyStr] = None) -> bool:
        """ This is a helper tool used by _bufferGenerator and _bufferWait to help deal with the 'endText' value.
            Please review those method's doc strings for more information.

        - :param outValue:
        - :param endText:
        - :param endTextType:
        - :param cmd:
        - :return:
        """

        # print(f"\n==== _endTextAnalyzer\ncmd: {cmd}\noutValue: \n{outValue}\n\n"
        #       f"endText: {repr(endText)}\nendTextType: {endTextType}\n====\n")
        if not outValue:
            return True
        if not endText:
            return True
        if cmd and cmd in outValue.splitlines()[-1]:
            return True
        if endTextType is tuple:
            line = sshBufferControl.escapeChars.sub('', outValue.splitlines()[-1]).strip()
            for item in endText:
                if len(item) == 1 and line.endswith(item):
                    return False
                elif len(item) > 1 and item in line:
                    return False
            return True
        if endTextType is str:
            if endText == 'CMDEND':
                for line in (sshBufferControl._processString(line.strip())
                             for line in outValue.splitlines() if cmd not in line and endText in line):
                    if line == endText:
                        return False
            # print(f"\n=== Compare: {repr(endText)} - {repr(outValue.splitlines()[-1])}")
            return endText not in outValue.splitlines()[-1]
        return True

    @staticmethod
    def _bufferGenerator(channel: Channel, out: StringIO, runTimeout: int, firstBitTimeout: int, betweenBitTimeout: int,
                         delay: float, endText: Union[Tuple, AnyStr] = "", closeOnFailure: bool = False,
                         cmd: Optional[AnyStr] = None) -> None:
        """ This is a tool designed to yield data from a Paramiko Channel buffer with several timeout controls

        - :param channel: The Paramiko Channel
        - :param runTimeout: (int/float) A positive number that determines how long the method should wait to complete the
            command.
        - :param firstBitTimeout: (int/float) A positive number that determines how long the method should wait for the first
            bit to arrive.
        - :param betweenBitTimeout: (int/float) A positive number that determines how long the method should wait inbetween
            bits of data on the buffer before assuming that the command isn't going to return any.
        - :param delay: (float) A positive number that determines how long the method should wait inbetween trying to listen
            for activity on the Paramiko Channel Buffer.
        - :param endText: (string/tuple) A string or tuple of strings that the method will look for in the strings that come
            from the buffer. If found then the method will assume the end of the buffer. This can be the prompt or 'CMDEND'
            or an example of the tuple is: ('$', '>', '#', '@', ']', '~')
        - :return:
        """

        # print(f"\n==== BufferGenerator\nRun Timeout: {runTimeout}\nFirst Bit Timeout: {firstBitTimeout}\n"
        #       f"Between Bit Timeout: {betweenBitTimeout}\nDelay: {delay}\n")
        # print(f"\n==== The endText is: {endText}\n")
        outValue = ""
        endTextType, endText = sshBufferControl._endTextParser(endText)
        endTime = time.time() + runTimeout
        sshBufferControl._bufferTimeToFirstBit(channel, time.time() + firstBitTimeout, delay)
        while time.time() <= endTime and not channel.closed and sshBufferControl._endTextAnalyzer(outValue, endText,
                                                                                                  endTextType, cmd=cmd):
            outValue = sshBufferControl._bufferBetweenBitWait(channel, time.time() + betweenBitTimeout, delay)
            # print(f'outValue: {outValue}')
            out.write(outValue)
        if sshBufferControl._endTextAnalyzer(outValue, endText, endTextType,
                                             cmd=cmd) and not channel.closed and closeOnFailure:
            if time.time() > endTime:
                log.debug(f'Buffer wait expired before all data was gathered and prompt '
                          f'appeared: [{str(channel)[18:20]}]: Closed: {channel.closed}')
            else:
                log.debug(f'Buffer timeout expired attempting to gather the next piece '
                          f'of data: [{str(channel)[18:20]}]: Closed: {channel.closed}')
            channel.close()

    @staticmethod
    def _bufferWait(channel: Channel, out: StringIO, runTimeout: int, firstBitTimeout: int, betweenBitTimeout: int,
                    delay: float, endText: Union[Tuple, AnyStr], cmd: AnyStr = '',
                    exitOnAnything: bool = False) -> Optional[bool]:
        """ This is a tool designed to write to a StringIO from a Paramiko Channel buffer. It has multiple time controls

        - :param channel: The Paramiko Channel
        - :param out: StringIO object
        - :param runTimeout: (int/float) A positive number that determines how long the method should wait to complete the
            command.
        - :param firstBitTimeout: (int/float) A positive number that determines how long the method should wait for the first
            bit to arrive.
        - :param betweenBitTimeout: (int/float) A positive number that determines how long the method should wait inbetween
            bits of data on the buffer before assuming that the command isn't going to return any.
        - :param delay: (float) A positive number that determines how long the method should wait inbetween trying to listen
            for activity on the Paramiko Channel Buffer.
        - :param endText: (string/tuple) A string or tuple of strings that the method will look for in the strings that come
            from the buffer. If found then the method will assume the end of the buffer. This can be the prompt or 'CMDEND'
            or an example of the tuple is: ('$', '>', '#', '@', ']', '~')
        - :param cmd: (string) OPTIONAL. If provided this method will simply confirm that the cmd string is not in the
            returning value and thus assumes that command has been executed and doesn't attempt to pull any additional bits
            from the Paramiko Channel buffer.
        - :param exitOnAnything: (bool) OPTIONAL. If provided this will exit one any bits are received.
        - :return: None if 'cmd' is used, True if 'exitOnAnything' is used, False for anything else.
        """

        # print(f"\n==== BufferWait\nRun Timeout: {runTimeout}\nFirst Bit Timeout: {firstBitTimeout}\n"
        #       f"Between Bit Timeout: {betweenBitTimeout}\nDelay: {delay}\n")
        outValue = out.getvalue()
        endTextType, endText = sshBufferControl._endTextParser(endText)
        endTime = time.time() + runTimeout
        if firstBitTimeout:
            sshBufferControl._bufferTimeToFirstBit(channel, time.time() + firstBitTimeout, delay)
        while time.time() <= endTime and not channel.closed and sshBufferControl._endTextAnalyzer(outValue, endText,
                                                                                                  endTextType, cmd=cmd):
            if exitOnAnything and len(outValue) > 0:
                if len(cmd) > 0 and cmd in outValue.splitlines()[-1]:
                    continue
                return None
            out.write(sshBufferControl._bufferBetweenBitWait(channel, time.time() + betweenBitTimeout, delay))
            outValue = out.getvalue()
        if time.time() > endTime or channel.closed or len(outValue) == 0:
            return False
        if endTextType is tuple:
            return sshBufferControl.escapeChars.sub('', outValue.splitlines()[-1]).strip().endswith(endText)
        if endTextType is str:
            return endText not in outValue.splitlines()[-1]
        return None
