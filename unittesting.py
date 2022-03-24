import unittest
import os
import json
from functools import partialmethod
from io import StringIO
from PyLinuxDiagnosticToolKit import ldtk, find_modules
from PyLinuxDiagnosticToolKit.libs import ArgumentWrapper
from sshConnector.sshThreader import sshThreader as threadedSSH
from LinuxModules.CommandContainers import CommandContainer
from LinuxModules.genericCmdModule import GenericCmdModule


tki = None


testFile = """#!/bin/bash

sleep 1

echo 'this is a test'
"""


# noinspection PyUnresolvedReferences
def standard_check(testObj):
    global tki
    if tki is None:
        testObj.skipTest("The ToolKitInterface failed to instantiate skipping...")
    if not tki.checkConnection():
        testObj.skipTest("The ToolKitInterface does not have a valid connection...")


def letters_generator():
    for s in range(97, 123):
        for m in range(97, 123):
            for e in range(97, 123):
                yield f'{chr(s)}{chr(m)}{chr(e)}'


# noinspection PyUnresolvedReferences
class TestAAuthentication(unittest.TestCase):

    def test_a_new_instance(self):
        global tki
        with open('unittesting.json') as f:
            config = json.load(f)
        args = ArgumentWrapper.arguments().parse_known_args()[0]
        args.host = config.get('host')
        args.username = config.get('username')
        args.password = config.get('password')
        args.root = True if config.get('root') else False
        args.rootpwd = config.get('rootpwd')
        tki = ldtk.ToolKitInterface(arguments=args, auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)

    def test_b_ssh(self):
        global tki
        if tki is None:
            self.skipTest("The ToolKitInterface failed to instantiate skipping...")
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)

    def test_c_confirm_conn(self):
        global tki
        if tki is None:
            self.skipTest("The ToolKitInterface failed to instantiate skipping...")
        self.assertTrue(tki.checkConnection())

    def test_z_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


# noinspection PyUnresolvedReferences
class TestBSimpleExecution(unittest.TestCase):

    def test_a_login(self):
        global tki
        with open('unittesting.json') as f:
            config = json.load(f)
        args = ArgumentWrapper.arguments().parse_known_args()[0]
        args.host = config.get('host')
        args.username = config.get('username')
        args.password = config.get('password')
        args.root = True if config.get('root') else False
        args.rootpwd = config.get('rootpwd')
        tki = ldtk.ToolKitInterface(arguments=args, auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_b_execute_nonthreaded(self):
        global tki
        standard_check(self)
        output = tki.execute('echo test_str', threading=False)
        self.assertIsInstance(output, str, "The execute method didn't return a string")
        self.assertEqual(output.strip(), 'test_str', f"The string should equal test_string but is instead: {output}")

    def test_c_execute_threaded(self):
        global tki
        standard_check(self)
        output = tki.execute('echo test_str', threading=True)
        self.assertIsInstance(output, CommandContainer, "The execute method didn't return a CommandContainer")
        output.waitForResults()
        results = output.results
        self.assertEqual(results.strip(), 'test_str', f"The string should equal test_string but is instead: {output}")

    def test_z_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


# noinspection PyUnresolvedReferences
class TestCUserEscalation(unittest.TestCase):

    def test_a_login(self):
        global tki

        with open('unittesting.json') as f:
            config = json.load(f)
        args = ArgumentWrapper.arguments().parse_known_args()[0]
        args.host = config.get('host')
        args.username = config.get('username')
        args.password = config.get('password')
        args.root = True if config.get('root') else False
        args.rootpwd = config.get('rootpwd')

        tki = ldtk.ToolKitInterface(arguments=args, auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_b_confirm_user(self):
        global tki
        standard_check(self)

        with open('unittesting.json') as f:
            config = json.load(f)
        args = ArgumentWrapper.arguments().parse_known_args()[0]
        args.username = config.get('username')
        args.root = True if config.get('root') else False

        userNotThreaded = tki.execute('whoami', threading=False)
        self.assertIsInstance(userNotThreaded, str, "The execute method didn't return a string")
        cc = tki.execute('whoami', threading=True)
        userThreaded = cc.waitForResults()
        self.assertIsInstance(userThreaded, str, "The execute method didn't return a string")
        self.assertEqual(userNotThreaded.strip(), userThreaded.strip())
        userShouldBe = 'root' if args.root else args.username
        self.assertEqual(userThreaded.strip(), userShouldBe)

    def test_c_su_escalation_in_cc(self):
        global tki
        standard_check(self)

        def _su_escalate_test(*args, **kwargs):
            this = kwargs.get('this')
            env = this.EnvironmentObject
            if env.becomeRoot():
                return env.escalate(loginCmd='su -', userName='tester')
            return False

        cc = tki.execute('whoami', preparser=_su_escalate_test)
        userThreaded = cc.waitForResults()
        self.assertIsInstance(userThreaded, str, "The execute method didn't return a string")
        self.assertEqual(userThreaded.strip(), 'tester')

    def test_d_su_escalation_in_channel(self):
        global tki
        standard_check(self)

        env = tki.sshCon.getEnvironment()

        self.assertTrue(env.becomeRoot())

        env.escalate(loginCmd='su -', userName='testerOne')
        username = tki.sshCon.checkWhoAmI(environment=env)
        self.assertEqual(username, 'testerOne')

        env.logoutCurrentUser()
        username = tki.sshCon.checkWhoAmI(environment=env)
        self.assertEqual(username, 'root')
        self.assertEqual(env.userList[-1], 'root')

    def test_e_sudo_escalation_in_channel(self):
        """
            This assumes that sudo will ask for the root password!
        """
        global tki
        standard_check(self)

        env = tki.sshCon.getEnvironment()

        self.assertTrue(env.becomeRoot())

        env.escalate(loginCmd='sudo', userName='testerOne')
        username = tki.sshCon.checkWhoAmI(environment=env)
        self.assertEqual(username, 'testerOne')

        env.escalate(loginCmd='sudo', userName='testerTwo')
        username = tki.sshCon.checkWhoAmI(environment=env)
        self.assertEqual(username, 'testerTwo')

        self.assertEqual(env.numUsers, 4)

        self.assertTrue(env.becomeRoot())
        username = tki.sshCon.checkWhoAmI(environment=env)
        self.assertEqual(username, 'root')
        self.assertEqual(env.userList[-1], 'root')

    def test_f_escalation_with_envid(self):
        global tki
        standard_check(self)

        def _su_escalate_test(*args, **kwargs):
            this = kwargs.get('this')
            env = this.EnvironmentObject
            if env.becomeRoot():
                return env.escalate(loginCmd='su -', userName='testerOne')
            return False

        env = tki.createEnvironment(label='test')

        cc = tki.execute("echo test", lable='test', preparser=_su_escalate_test)

        cc.waitForResults()

        username = tki.sshCon.checkWhoAmI(environment=env)

        self.assertEqual(username, 'testerOne')

        self.assertEqual(cc.EnvironmentObject._id, env._id)

    def test_z_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


# noinspection PyUnresolvedReferences
class TestDCommandModulesNoFlags(unittest.TestCase):
    """
        These are CommandModules that do not require flags. Modules that do require flags simply confirm they
        can be created.
    """

    def test_aaa_login(self):
        global tki

        with open('unittesting.json') as f:
            config = json.load(f)
        args = ArgumentWrapper.arguments().parse_known_args()[0]
        args.host = config.get('host')
        args.username = config.get('username')
        args.password = config.get('password')
        args.root = True if config.get('root') else False
        args.rootpwd = config.get('rootpwd')

        tki = ldtk.ToolKitInterface(arguments=args, auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_zzz_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


def _test_dummy(self, moduleName=None):
    if moduleName is None:
        self.skipTest("The is a dummy test skipping...")

    global tki
    standard_check(unittest.TestCase)

    module = tki.getModules(moduleName)

    self.assertIsInstance(module, GenericCmdModule)

    moduleTwo = getattr(tki.modules, moduleName, None)

    self.assertIsInstance(moduleTwo, GenericCmdModule)

    self.assertIs(module, moduleTwo)

    if module.requireFlags is True:
        return None

    output = module()

    self.assertIsNotNone(output)


# noinspection PyUnresolvedReferences
class TestESFTPandSCP(unittest.TestCase):
    """
        These are CommandModules that do not require flags. Modules that do require flags simply confirm they
        can be created.
    """

    def test_a_login(self):
        global tki

        with open('unittesting.json') as f:
            config = json.load(f)
        args = ArgumentWrapper.arguments().parse_known_args()[0]
        args.host = config.get('host')
        args.username = config.get('username')
        args.password = config.get('password')
        args.root = True if config.get('root') else False
        args.rootpwd = config.get('rootpwd')

        tki = ldtk.ToolKitInterface(arguments=args, auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_b_sftp(self):
        global testFile
        global tki
        standard_check(self)

        sftpClient = tki.getSFTPClient()

        rm, ll = tki.getModules('rm', 'll')

        localIO = StringIO(testFile)

        if ll.fileExist('/tmp/testFile.txt', rerun=True):
            rm('/tmp/testFile.txt')

        with sftpClient as sftp:
            sftp.put(localIO, '/tmp/testFile.txt')

        doesExist = ll.fileExist('/tmp/testFile.txt', rerun=True)
        self.assertTrue(doesExist)

        if os.path.exists("testFile.txt"):
            os.remove("testFile.txt")

        with sftpClient as sftp:
            sftp.get('/tmp/testFile.txt', 'testFile.txt')
            sftp.put('testFile.txt', '/tmp/testFileTwo.sh')

        doesExistTwo = ll.fileExist('/tmp/testFileTwo.sh', rerun=True)
        self.assertTrue(doesExistTwo)

        output = tki.execute('bash /tmp/testFileTwo.sh', threading=False)

        self.assertEqual(output, 'this is a test')

        if doesExist:
            rm('/tmp/testFile.txt')
        if doesExistTwo:
            rm('/tmp/testFileTwo.sh')
        if os.path.exists("testFile.txt"):
            os.remove("testFile.txt")

    def test_c_scp(self):
        global testFile
        global tki
        standard_check(self)

        scpClient = tki.getSCPClient()

        rm, ll = tki.getModules('rm', 'll')

        localIO = StringIO(testFile)

        if ll.fileExist('/tmp/testFile.txt', rerun=True):
            rm('/tmp/testFile.txt')

        with scpClient as scp:
            scp.put(localIO, '/tmp/testFile.txt')

        doesExist = ll.fileExist('/tmp/testFile.txt', rerun=True)
        self.assertTrue(doesExist)

        if os.path.exists("testFile.txt"):
            os.remove("testFile.txt")

        with scpClient as scp:
            scp.get('/tmp/testFile.txt', 'testFile.txt')
            scp.put('testFile.txt', '/tmp/testFileTwo.sh')

        doesExistTwo = ll.fileExist('/tmp/testFileTwo.sh', rerun=True)
        self.assertTrue(doesExistTwo)

        output = tki.execute('bash /tmp/testFileTwo.sh', threading=False)

        self.assertEqual(output, 'this is a test')

        if doesExist:
            rm('/tmp/testFile.txt')
        if doesExistTwo:
            rm('/tmp/testFileTwo.sh')
        if os.path.exists("testFile.txt"):
            os.remove("testFile.txt")

    def test_zzz_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


if __name__ == '__main__':
    modules = find_modules(moduleSubDir='CommandModules')
    maxLength = 17572
    letterGen = letters_generator()
    next(letterGen)
    for module in modules:
        letter = next(letterGen)
        funcName = f"test_{letter}_{module}"
        if hasattr(TestDCommandModulesNoFlags, funcName):
            maxLength -= 1
            continue
        setattr(TestDCommandModulesNoFlags, funcName, partialmethod(_test_dummy, *(), **{'moduleName': module}))
        maxLength -= 1
        if maxLength <= 0:
            break
    unittest.main()
