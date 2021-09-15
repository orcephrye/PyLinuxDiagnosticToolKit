#!/usr/bin/env python
# -*- coding=utf-8 -*-
#
# Author: Timothy Nodine, Ryan Henrichson

# Version: 0.5.0
# Date: 10/13/14
# Description: This is the 4th class in the sshConnector. This is a focus on changing users in a persistent ssh
# connection. It allows someone to change the user after logging in and keeps track to what user you are and have
# been.


import re
import traceback
import logging
from time import sleep
from io import StringIO
from typing import Callable, Optional, Union
from LDTKExceptions import _becomeUser, _errorChannel
from sshConnector.sshBufferControl import sshBufferControl
from sshConnector.sshLibs import dummyFunction
from sshConnector.sshLibs.sshChannelEnvironment import sshEnvironment


log = logging.getLogger('sshEnvironmentControl')


class sshEnvironmentControl(sshBufferControl):

    # Regex's used to pull command tags.
    matchRe = re.compile(r'(?<=^CMDSTART).+', flags=re.MULTILINE | re.DOTALL)
    # clean up any errors or other data that may appear before the start tag
    startSubRe = re.compile(r'.*?(?=^CMDSTART)', flags=re.MULTILINE | re.DOTALL)
    # clean up all data after the end tag
    endSubRe = re.compile(r'CMDEND.*', flags=re.MULTILINE | re.DOTALL)

    def __init__(self, arguments, **kwargs):
        """ init function for sshEnvironmentControl.
            This class has methods that control the state of a shell environment that the Paramiko Channel object is
            connected too. It can do things such as user escalation, change shell type, export variables and so on.

        - :param arguments: If this is not passed then sshUserControl simply moves along to its super class sshCommand.
        - :param kwargs: Exists to help safely deal with inheritance.
        - :return: This is a __init__ class and doesn't have a return.
        """

        super(sshEnvironmentControl, self).__init__(arguments=arguments, **kwargs)

        if self.checkConnection():
            self.mainEnvironment.push("su -", name=arguments.username, additionalInput=arguments.password)
            self._promptWait(self.mainEnvironment, StringIO(), timeout=10, iotime=2)
            if arguments.root:
                self.becomeRoot()
            else:
                self.escalate(escalationCmd='bash', escalationArgs='-norc', name='BASH', console=True, unsafe=True)

    def escalate(self, *args, env: bool = False, console: bool = False, **kwargs) -> Union[sshEnvironment, bool]:
        """ The default escalation method. This can handle console or environment changes. It uses the console
            and env bool parameters to control what type of console change will happen. If both are false the method
            will call the 'becomeUser' method.

        - :param args: (tuple) - passed on
        - :param env: (bool) default False - This will be checked first and will call 'environmentChange' method.
        - :param console: (bool) default False - This will be checked second and will call 'consoleEscalation' method.
        - :param kwargs: (dict) - passed on
        - :return: Either 'sshEnvironment' (success) or False (Failure)
        """

        if kwargs.get('environment', self.mainEnvironment):
            if env:
                return self.environmentChange(*args, **kwargs)
            elif console:
                return self.consoleEscalation(*args, **kwargs)
            else:
                return self.becomeUser(*args, **kwargs)
        return False

    def becomeRoot(self, loginCmd: Optional[str] = None, password: Optional[str] = None, verifyUser: bool = True,
                   environment: sshEnvironment = None, **kwargs) -> bool:
        """ Helpful tool for quickly escalating to the root user. This method can be called without any use of it's
            parameters as it can get these from 'self'. However, passing a specific environment is necessary to
            escalate to root on that environment.

        - :param loginCmd: (str) default None - This is usually 'su -' or 'sudo'.
        - :param password: (str) default None - This can be filled by 'self.rootpwd' which is itself is populated by the
            value of the argument '--rootpwd'.
        - :param verifyUser: (bool) default True - This will run a whoami check after escalation to make sure the
            environment has been escalated to root. It will return False if the user escalation too root failed.
        - :param environment: (sshEnvironment) default None - replaced with 'self.mainEnvironment' if left empty.
        - :param kwargs: passed on to the escalate command.
        - :return: (bool)
        """

        environment = environment or self.mainEnvironment
        if loginCmd is None:
            loginCmd = self.rootLogin
        if password is None:
            password = self.rootpwd
        kwargs['reCapturePrompt'] = kwargs.get('reCapturePrompt', True)

        log.debug(f"Env ID: {environment._id} - Prompt: {environment.prompt} - Whoami: {environment.whoami}")
        self.becomeUser(loginCmd, 'root', loginPasswd=password, verifyUser=verifyUser,
                        environment=environment, **kwargs)
        log.debug(f"Env ID: {environment._id} - Prompt: {environment.prompt} - Whoami: {environment.whoami}")

        if verifyUser:
            return True
        if self.whoami(environment=environment) == 'root':
            return True

        environment.getPrompt(reCapturePrompt=True)
        return False

    def becomeUser(self, loginCmd: str, userName: str, loginPasswd: Optional[str] = None,
                   environment: Optional[sshEnvironment] = None, userEscalation: bool = False, verifyUser: bool = True,
                   reCapturePrompt: bool = True, unsafe: bool = True) -> Union[sshEnvironment, bool]:
        """ This manages the current user and will either escalate or de-escalate to the requested user.

        - :param loginCmd: (str) - This is typically 'su -' or 'sudo su -'. Do NOT add the username to this, since it
                will automatically be appended via the 'userName' parameter.
        - :param userName: (str) - This is appended with a space after the 'loginCmd' param.
        - :param loginPasswd: (str) default None - If not passed the login password will attempt to be populated using
                existing authentication information.
        - :param environment: (sshEnvironment) default None - The sshEnvironment that this method will act on.
        - :param userEscalation: This is a boolean that will change the behavior of becomeUser. If you want to be a user
                that you already are, the default behavior is to de-escalate to that user. This states that no
                de-escalation will occur if you want to become a user, rather it will attempt to escalate again.
                IE: login as default user ie: 'server', then escalate to root, then become 'server' again by
                logging out as root. However, if userEscalation is True it would look like server -> root -> server.
        - :param verifyUser: (bool) default True - Effects the behavior of becomeUser by deciding whether or not to
                check and see if the loginCmd was or was not successful when becoming the user in question. It does
                this by running the 'whoami' command and comparing the output to the 'userName' variable.
        - :param reCapturePrompt: (bool) default True - This will re-populate the 'prompt' variable in the
                sshEnvironment class with the new prompt after the escalation is complete.
        - :param unsafe: (bool) default False - This tells the sshBufferControl to run in 'unsafe' mode. This changes
                how to tell when to stop reading the buffer. It is necessary for most user escalation methods.

        - :return: Either 'sshEnvironment' (success) or False (Failure)
        """

        strBuffer: StringIO = StringIO()

        environment = environment or self.mainEnvironment

        if not self.checkConnection(environment):
            # log.debug("The connection is closed!")
            return False

        # Checks to see if you are attempting to become a user you already are.
        if userName is environment.whoami:
            # log.debug("You are attempting to escalate to the user currently logged in as. Skipping")
            return False
        # Checks to see if you are attempting to become a user that you have already been and could simple deescalate
        # too. We will only deescalate if the 'userEscalation' flag is False which is default. If true this logic will
        # not run and the function will simply proceed as normal and attempt to login as the new user.
        if userName in environment.userList:
            # log.debug("You are attempting to escalate to a user you already have logged in as in the past. "
            #           "This is just a warning")
            if not userEscalation:
                return self._becomePreviousUser(userName, strBuffer, environment)

        # We need to us the '-k' flag in order to clear previous uses of sudo from the cache. This fixes issues with
        # capturing password prompts as it makes sudo ignore previous successful attempts.
        loginCmd = self.processRootLogin(loginCmd)

        while environment.recv_ready() is not True and environment.send_ready() is not True:
            if environment.closed:
                environment.get_transport().close()
                raise _errorChannel('Unable to create SSH channel...')
            sleep(.5)

        channel = False

        # We handle logging into root differently then logging in as any other user. We 'may' attempt to retry using a
        # different login command. This retry depends on the "verifyUser" variable.
        try:
            if not environment.prompt:
                environment.getPrompt(reCapturePrompt=True)
            channel = self._escalateUser(loginCmd=loginCmd, loginPasswd=loginPasswd, userName=userName,
                                         environment=environment, verifyUser=verifyUser, buffer=strBuffer,
                                         unsafe=unsafe)
        except _becomeUser as e:
            if self.arguments.rootLoginExplicit:
                raise e
            log.warning(f"Unable to become user will try again: {e}")
            if 'sudo' in loginCmd:
                log.info(f"Failed to escalate to user: {userName} with command: {loginCmd}. Trying command: 'su -'")
                self._clearLoginAttempt(environment)
                channel = self._escalateUser(loginCmd='su -', loginPasswd=loginPasswd, userName=userName,
                                             environment=environment, verifyUser=verifyUser, buffer=strBuffer,
                                             unsafe=unsafe, prompt=environment.prompt)
            elif 'su -' in loginCmd:
                newLoginCmd = '/usr/bin/sudo -k; /usr/bin/sudo su -'
                log.info(f"Failed to escalate to user: {userName} with command: {loginCmd}. "
                         f"Trying command: {newLoginCmd}")
                self._clearLoginAttempt(environment)
                channel = self._escalateUser(loginCmd=newLoginCmd, loginPasswd=loginPasswd, userName=userName,
                                             environment=environment, verifyUser=verifyUser, buffer=strBuffer,
                                             unsafe=unsafe, prompt=environment.prompt)
        except Exception as e:
            log.error(f"Unknown ERROR while user escalation: {e}")
            log.debug(f"[DEBUG]: {traceback.format_exc()}")
        finally:
            if not environment.isPromptDefault(reCapturePrompt=reCapturePrompt):
                if reCapturePrompt and self.arguments.useBashnorc:
                    self.escalate(environment=environment, escalationCmd='bash', escalationArgs='-norc', name='BASH',
                                  console=True, unsafe=True, reCapturePrompt=True)
            # environment.getPrompt(reCapturePrompt=reCapturePrompt)

        return channel or environment

    def consoleEscalation(self, escalationCmd: str, escalationArgs: str = "", escalationInput: Optional[str] = None,
                          escalationType: str = "console", escalationHook: Optional[Callable] = None,
                          name: Optional[str] = None, environment: Optional[sshEnvironment] = None,
                          **kwargs) -> Union[sshEnvironment, bool]:
        """ This function differs from 'becomeUser' as it designed to change the environment from BASH to for example
            mysql shell or a sqlpluss shell.

        :param escalationCmd: (str) - The command such as sqlpluss or zsh
        :param escalationArgs: (str) default "" - Additional args such as '-h localhost'.
        :param escalationInput: (str) default None - This is used if the command will require input such as a password.
        :param escalationType: (str) default "console" - This is used to record the escalation type in sshEnvironment.
        :param escalationHook: (Callable) default None - a method to call instead of the default escalation method.
        :param name: (str) defualt None - What to call this console change. This can be useful when searching if a
                sshEnvironment has already escalated to a specific environment.
        :param environment: sshEnvironment object
        :return: Either 'sshEnvironment' (success) or False (Failure)
        """

        reCapturePrompt = kwargs.get('reCapturePrompt', True)
        strBuffer: StringIO = StringIO()

        environment = environment or self.mainEnvironment

        while environment.recv_ready() is not True and environment.send_ready() is not True:
            if environment.closed:
                environment.get_transport().close()
                raise _errorChannel('Unable to create SSH channel...')
            sleep(.5)

        if name is None:
            name = escalationCmd

        environment = self._performEscalation(environment, loginCmd=escalationCmd, loginPasswd=escalationInput,
                                              userName=escalationArgs, buffer=strBuffer, console=True,
                                              escalationHook=escalationHook, **kwargs)
        
        environment.getPrompt(reCapturePrompt=reCapturePrompt)
            
        environment.push(escalationCmd + escalationArgs, name=name, additionalInput=escalationInput, 
                         escalationType=escalationType)
        
        return environment

    def environmentChange(self, *args, **kwargs) -> Union[sshEnvironment, bool]:
        """ Changes the state of the environment in some way other then user or console escalation. This method
            depends on 'consoleEscalation'. It simply adjusted the 'escalationType' and 'reCapturePrompt' parameters
            to work for changing the environment. This method is helpful if you want to record the fact that this
            sshEnvironment has special variables/settings set. Such as editing its PATH or the use of export. That way
            it is easy to run future commands on that particular environment.

        - :param: args - Passed to 'consoleEscalation'
        - :param: kwargs - Passed to 'consoleEscalation'
        - :return: Either 'sshEnvironment' (success) or False (Failure)
        """

        kwargs['escalationType'] = 'env'
        kwargs['reCapturePrompt'] = kwargs.get('reCapturePrompt', False)
        return self.consoleEscalation(*args, **kwargs)

    def resetEnvironment(self, environment: Optional[sshEnvironment] = None) -> None:
        """ As noted by the name this resets the values for the sshEnvironment class. *BE CAREFUL* this doesn't run
            commands on the ssh channel environment meaning the actual environment on the target machine hasn't
            changed. This only clears the values recorded on the sshEnvironment class.

        :param environment: (sshEnvironment) default None - the sshEnvironment to run 'resetEnvironment' against.
        :return: None
        """

        getattr(environment or self.mainEnvironment, 'resetEnvironment', dummyFunction)()

    def logoutCurrentUser(self, environment: Optional[sshEnvironment] = None, junkOut: Optional[StringIO] = None,
                          reCapturePrompt: bool = True) -> Union[sshEnvironment, bool]:
        """ Runs the command 'exit' once on a specified environment. Effectively logging out of a user or other
            escalation.

        - :param environment: (sshEnvironment) default None -
        - :param junkOut: (StringIO) default None -
        - :param reCapturePrompt: (bool) default True -
        - :return: Either 'sshEnvironment' (success) or False (Failure)
        """
        
        environment = environment or self.mainEnvironment

        if not self.checkConnection(environment):
            return environment

        if environment.consoleStack is None or len(environment.consoleStack) == 0:
            return environment

        if not junkOut:
            junkOut: StringIO = StringIO()

        self._bufferControl(environment, 'exit', junkOut, unsafe=True)
        environment.pull()
        if self.checkConnection(environment):
            log.info(f"Connection still valid on: {environment._id} - Num Escalations: {environment.numEscalations}")
            self.getPrompt(environment=environment, reCapturePrompt=reCapturePrompt)
        else:
            log.info(f"Connection closed on: {environment._id}")
            
        return environment

    def logoutConsole(self, logoutCmd: Optional[str] = None, environment: Optional[sshEnvironment] = None) -> bool:
        """ This reverses through past environment changes until it undoes the previous console escalation.

        :param logoutCmd: (str) (default None) This is a custom command to leave the console. For example 'exit' or
            'quit'.
        :param environment: (sshEnvironment/Paramiko Channel)
        :return:
        """

        environment = environment or self.mainEnvironment

        if not logoutCmd:
            logoutCmd = "exit"

        self._bufferControl(environment, 'exit', StringIO(), unsafe=True)

        if environment.pull()[0] != environment.__CONSOLE_ESCALATION__:
            return self.logoutConsole(logoutCmd, environment)
        environment.getPrompt(reCapturePrompt=True)
        return environment.checkConnection()

    def disconnect(self, environment: Optional[sshEnvironment] = None) -> None:
        """ This attempts to graceful log out by exiting/de-escalating through all previous console escalations on a
            given sshEnvironment.

        - :param environment: (sshEnvironment) default None -
        - :return: None
        """

        environment = environment or self.mainEnvironment
        for x in range(environment.numEscalations):
            self.logoutCurrentUser(environment, reCapturePrompt=False)
        if environment.isMain:
            super(sshEnvironmentControl, self).disconnect()

    def whoami(self, environment: Optional[sshEnvironment] = None) -> str:
        """ This returns the 'whoami' of the provided sshEnvironment. If an environment is not provided it pulls this
            from the main Environment. Sense this is looking at a variable this is not always reliable because the
            variable may become de-synced with its actual environment. Also calling this from a thread may also result
            in the wrong information if the environment is also being acted upon. For accurate information use the
            'checkWhoAmI' method as this runs the 'whoami' command on sshEnvironment.

        - :param environment: (sshEnvironment) default None -
        - :return (str)
        """

        return getattr(environment or self.mainEnvironment, 'whoami', '')

    def checkWhoAmI(self, environment: Optional[sshEnvironment] = None) -> str:
        """ This is the slow but sure fire way to find out what the current user is. This function can be called with a
            custom channel to determine the user of that channel. If calling from a thread it is required that you pass
            the channel or else you will get the whoami information for the master channel.
            Note: When called from a thread this function runs the command directly on the sshCommand buffer. This means
            that the calling thread has to wait until this is complete. Keep that in mind when using this function.

        - :param environment: (sshEnvironment) default None -
        - :return: (str)
        """

        def _checkWhoAmIHelper(cmdResults) -> str:
            try:
                cmdOutputRe = sshEnvironmentControl.matchRe.search(
                    sshEnvironmentControl.startSubRe.sub('', cmdResults, count=1))
                if cmdOutputRe:
                    return sshEnvironmentControl.endSubRe.sub('', cmdOutputRe.group(), count=1).strip() or ''
                return ''
            except Exception as e:
                log.error(f'error in _checkWhoAmIHelper: {e}')
                log.debug(f'[DEBUG] for _checkWhoAmIHelper: {traceback.format_exc()}')
                return ''

        return _checkWhoAmIHelper(self.executeOnEnvironment(environment=environment or self.mainEnvironment,
                                                            cmd='echo CMDSTART; whoami; echo CMDEND', prompt=''))

    def getPrompt(self, environment: sshEnvironment, reCapturePrompt: bool = False) -> Optional[str]:
        """ This captures the current prompt which is used to improve the performance of the buffer.

        - :param environment: sshEnvironment object
        - :return: str or None
        """
        # log.debug(f"ID: {environment._id} - Cached Prompt: {environment.prompt} - reCapturePrompt: {reCapturePrompt}")
        if environment.prompt is not None and reCapturePrompt is False:
            return environment.prompt
        environment.prompt = self._capturePrompt(environment, StringIO()) or None
        return environment.prompt

    def _escalateUser(self, loginCmd: str, userName: str, loginPasswd: str, environment: sshEnvironment,
                      verifyUser: bool, buffer: StringIO, unsafe: bool, **kwargs) -> sshEnvironment:
        """ Used as a helper function for becomeUser

        - :param loginCmd: (str)
        - :param userName: (str)
        - :param loginPasswd: (str)
        - :param environment: (sshEnvironment)
        - :param verifyUser: (bool)
        - :param buffer: (StringIO)
        - :param unsafe: (bool)
        - :param kwargs: gets passed along
        - :return: sshEnvironment
        """

        kwargs.update({'noUserPrompt': self._noUserPromptParser(environment, **kwargs)})

        environment = self._performEscalation(environment, loginCmd=loginCmd, loginPasswd=loginPasswd,
                                              userName=userName, buffer=buffer, unsafe=unsafe, **kwargs)
        if verifyUser:
            if not self._verifyLogin(environment, userName, buffer):
                raise _becomeUser(f'Unable to become user {userName}')
        environment.push(loginCmd, name=userName, additionalInput=loginPasswd, escalationType='user')
        return environment

    def _becomePreviousUser(self, userName: str, buffer: StringIO, environment: sshEnvironment) -> sshEnvironment:
        """ Used as a helper function for becomeUser

        - :param userName: (str)
        - :param buffer: (StringIO)
        - :param environment: (sshEnvironment)
        - :return: (sshEnvironment)
        """

        environment = self.logoutCurrentUser(environment, junkOut=buffer)

        if userName == environment.whoami:
            if not self._verifyLogin(environment, userName=userName, out=buffer):
                log.debug("Failed to de-escalate to the correct user")
                self.checkConnection(environment)
        elif userName != environment.whoami and userName in environment.userList:
            self._becomePreviousUser(userName, buffer, environment)
        return environment

    def _performEscalation(self, environment: sshEnvironment, loginCmd: str, loginPasswd: str, userName: str,
                           buffer: StringIO, **kwargs) -> sshEnvironment:
        """ Used as a helper function for multiple methods within sshEnvironmentControl

        - :param environment: (sshEnvironment)
        - :param loginCmd: (str)
        - :param loginPasswd: (str)
        - :param userName: (str)
        - :param buffer: (StringIO)
        - :param kwargs: gets passed along
        - :return: (sshEnvironment)
        """

        console = kwargs.get('console', False)
        escalationHook = kwargs.get('escalationHook', None)
        cmd = loginCmd + " " + userName
        if isinstance(escalationHook, Callable):
            self._bufferControl(environment, cmd, buffer, unsafe=kwargs.get('unsafe', False),
                                prompt=kwargs.get('prompt', None))
            escalationHook(self, cmd, loginPasswd, environment, userName, buffer, console)
        elif console is True:
            self._bufferControl(environment, cmd, buffer, unsafe=kwargs.get('unsafe', False),
                                prompt=kwargs.get('prompt', None))
            if loginPasswd:
                self._bufferControl(environment, loginPasswd, buffer, unsafe=True)
        elif loginPasswd or 'sudo' in cmd:
            self._bufferControl(environment, cmd, buffer, unsafe=kwargs.get('unsafe', True))
            self._insertPassword(cmd, loginPasswd, environment, buffer, prompt=kwargs.get('noUserPrompt', None))
        else:
            self._bufferControl(environment, cmd, buffer, unsafe=kwargs.get('unsafe', False))
        return environment

    def _insertPassword(self, cmd: str, loginPasswd: str, environment: sshEnvironment,
                        out: StringIO, prompt: str) -> None:
        """ Used as a helper function for multiple methods within sshEnvironmentControl

        - :param cmd: (str)
        - :param loginPasswd: (str)
        - :param environment: (sshEnvironment)
        - :param out: (StringIO)
        - :param prompt: (str)
        - :return: None
        """

        if environment.whoami != 'root':
            wait = self._passwdWait(environment, out, cmd)
            lastline = out.getvalue().splitlines()[-1].strip()
            if 'assword' not in lastline and lastline.endswith(self.promptTextTuple):
                log.debug("Found a prompt skipping inserting password")
                return None
            if "sudo" in cmd:
                if self.arguments.password:
                    loginPasswd = self.arguments.password
                if 'assword for root' in lastline:
                    loginPasswd = self.arguments.rootpwd
                elif 'assword for' in lastline:
                    requestedName = re.search('assword for(.*):', lastline)
                    if requestedName:
                        requestedName = requestedName.group(1).strip()
                        loginPasswd = environment.getPasswordFor(requestedName)
                elif prompt in lastline or lastline.endswith(self.promptTextTuple):
                    return None
            if wait is not False:
                self._bufferControl(environment, loginPasswd, out, unsafe=True)
                self._promptWait(environment, out, cmd, insertNewLine=1)

    def _verifyLogin(self, environment: sshEnvironment, userName: str, out: StringIO) -> bool:
        """ Used as a helper function for multiple methods within sshEnvironmentControl

        - :param environment: (sshEnvironment)
        - :param userName: (str)
        - :param out: (StringIO)
        - :return: bool
        """

        if len(out.getvalue()) > 0 and 'assword' in out.getvalue().splitlines()[-1]:
            self._promptWait(environment, out, insertNewLine=3, timeout=30)

        results = self.checkWhoAmI(environment=environment)

        if results is not None and userName in results:
            return True
        return False

    def _clearLoginAttempt(self, environment: sshEnvironment) -> bool:
        """ Used by becomeUser method

        - :param environment:
        - :return: (bool)
        """

        try:
            prompt = self._noUserPromptParser(environment, prompt=environment.prompt, currentUser=environment.whoami)
            lastline = ""
            for i in range(5):
                lastline = self._noUserPromptParser(environment,
                                                    prompt=str(self._capturePrompt(environment, StringIO())),
                                                    currentUser=environment.whoami)
                if lastline and prompt in lastline:
                    return True
                sleep(1)
            if lastline.strip().endswith(self.promptTextTuple):
                return True
            return False
        except Exception as e:
            log.error(f'error in _clearLoginAttempt: {e}')
            log.debug(f'[DEBUG] for _clearLoginAttempt: {traceback.format_exc()}')
            return False

    def _noUserPromptParser(self, environment: sshEnvironment, prompt: Optional[str] = None, **kwargs) -> Optional[str]:
        """ Used by multiple different private helper methods.

        - :param environment: (sshEnvironmnet)
        - :param prompt: (str) default None
        - :param kwargs: possibly contains 'currentUser'
        - :return: (str/None)
        """

        if not prompt:
            prompt = self.getPrompt(environment, reCapturePrompt=False)
        if not prompt:
            return None
        currentUser = kwargs.get('currentUser', environment.whoami) or ''
        return str(prompt).replace(currentUser, '').strip()
