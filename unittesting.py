import unittest
import os
import json
import warnings
from time import sleep
from functools import partialmethod
from io import StringIO
from PyLinuxDiagnosticToolKit import ldtk, find_modules
from PyLinuxDiagnosticToolKit.libs import ArgumentWrapper
from sshConnector.sshThreader import sshThreader as threadedSSH
from LinuxModules.CommandContainers import CommandContainer
from LinuxModules.genericCmdModule import GenericCmdModule
from PyLinuxDiagnosticToolKit.libs.OSNetworking.PyNIC import NetworkInterfaceCards
from PyLinuxDiagnosticToolKit.libs.OSNetworking.PyRoute import Routes
from PyCustomParsers.GenericParser import BashParser, IndexList

warnings.filterwarnings("ignore", category=DeprecationWarning)

tki = None

testFile = """#!/bin/bash

sleep 1

echo 'this is a test'
"""

testfilePath = "/tmp/testfile.out"

testConfigFile = "unittesting.json"


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


def getConfig():
    with open(testConfigFile) as f:
        config = json.load(f)
    return config


def getArguments():
    config = getConfig()
    args = ArgumentWrapper.arguments().parse_known_args()[0]
    for key, value in config.items():
        if hasattr(args, key):
            setattr(args, key, value)
    args.root = True if config.get('root') else False
    return args


# noinspection PyUnresolvedReferences
class TestAAuthentication(unittest.TestCase):

    def test_a_new_instance(self):
        global tki
        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
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
        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
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

        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_b_confirm_user(self):
        global tki
        standard_check(self)

        with open(testConfigFile) as f:
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
            This assumes testerOne and testerTwo exist on target
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

        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
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

    if getattr(module, 'defaultKwargs', {}).get('preparser', '') == module.doesCommandExistPreParser:
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

        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
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


# noinspection PyUnresolvedReferences
class TestEProcessModules(unittest.TestCase):
    """
        These are CommandModules that either require flags or have special methods that should be tested. Modules that
        do require flags simply confirm they can be created.
    """

    def test_aaa_login(self):
        global tki

        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_aab_ps(self):
        """ Assumes system has systemd """
        global tki
        standard_check(self)

        ps = tki.modules.ps

        output = ps()

        self.assertIsNotNone(output)
        self.assertGreaterEqual(len(ps), 1)

        pidlist = ps.getPIDListByName('systemd')
        self.assertGreaterEqual(len(pidlist), 1)

        topCPU = ps.getTopCPU()
        self.assertEqual(len(topCPU), 10)

        topMem = ps.getTopMem()
        self.assertEqual(len(topMem), 10)

    def test_aac_lsof(self):
        global tki
        standard_check(self)

        lsof = tki.modules.lsof

        output = lsof()

        self.assertIsNotNone(output)
        self.assertGreaterEqual(len(lsof), 1)

        openByFileSystem = lsof.getOpenFilesByFilesystem()
        self.assertIsNotNone(openByFileSystem)
        self.assertGreaterEqual(len(openByFileSystem), 1)

        convertToBytes = lsof.lsofConvertResultsToBytes(output)
        self.assertIsNotNone(convertToBytes)

    def test_aad_which(self):
        global tki
        standard_check(self)

        which = tki.modules.which

        results = which.doesCommandExist('cat')
        self.assertTrue(results)

    def test_zzz_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


# noinspection PyUnresolvedReferences
class TestENetworkModules(unittest.TestCase):
    """
        These are CommandModules that either require flags or have special methods that should be tested. Modules that
        do require flags simply confirm they can be created.
    """

    def test_aaa_login(self):
        global tki

        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_aab_ifconfig(self):
        global tki
        standard_check(self)

        if not tki.modules.which.doesCommandExist('ifconfig'):
            self.skipTest(f"ifconfig command doesn't exist on box skipping")

        ifconfig = tki.modules.ifconfig

        output = ifconfig()

        self.assertIsInstance(output, str)

        allData = ifconfig.getIfconfigAllData()

        self.assertIsInstance(allData, NetworkInterfaceCards)
        self.assertGreaterEqual(len(allData.names), 1)

    def test_aac_ip(self):
        global tki
        standard_check(self)

        ip = tki.modules.ip

        allIPData = ip.getIPShowAllData()
        self.assertIsInstance(allIPData, NetworkInterfaceCards)
        self.assertGreaterEqual(len(allIPData.names), 1)

        allRoutes = ip.getIPRouteData()
        self.assertIsInstance(allRoutes, Routes)
        self.assertGreaterEqual(len(allRoutes.routes), 1)

    def test_aad_ping(self):
        global tki
        standard_check(self)

        ping = tki.modules.ping

        localIPStr = '127.0.0.1'
        localIPDict = {'localhost': '127.0.0.1', 'GoogleDNS': '8.8.8.8'}
        localIPList = ['127.0.0.1', '8.8.8.8']

        results = ping(localIPStr)
        self.assertIsInstance(results, str)

        results = ping(localIPDict)
        self.assertIsInstance(results, dict)
        self.assertEqual(len(results), len(localIPDict))

        results = ping(localIPList)
        self.assertIsInstance(results, dict)
        self.assertEqual(len(results), len(localIPList))

        canPing = ping.canPing(localIPStr)
        self.assertTrue(canPing)

    def test_aad_route(self):
        global tki
        standard_check(self)

        if not tki.modules.which.doesCommandExist('route'):
            self.skipTest(f"route command doesn't exist on box skipping")

        route = tki.modules.route

        allRoutes = route.getRouteData()
        self.assertIsInstance(allRoutes, Routes)
        self.assertGreaterEqual(len(allRoutes.routes), 1)

    def test_aae_hosts(self):
        global tki
        standard_check(self)

        hosts = tki.modules.hosts
        hosts()
        self.assertIsInstance(hosts, BashParser)
        self.assertGreaterEqual(len(hosts), 1)

    def test_zzz_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


# noinspection PyUnresolvedReferences
class TestEDiskModules(unittest.TestCase):
    """
        These are CommandModules that either require flags or have special methods that should be tested. Modules that
        do require flags simply confirm they can be created.
    """

    def test_aaa_login(self):
        global tki

        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_aab_df(self):
        global tki
        standard_check(self)

        df = tki.modules.df

        output = df()

        self.assertIsNotNone(output)

        results = df.isBelowPercentThreshold(threshold=99, mountpoint='/')
        self.assertIsNotNone(results)
        self.assertGreaterEqual(len(results), 1)

        results = df.isBelowMBThreshold(threshold=1000000000, mountpoint='/')
        self.assertIsNotNone(results)
        self.assertGreaterEqual(len(results), 1)

        before = len(output)
        results = df.dfConvertResultsToBytes()
        self.assertIsNotNone(results)
        self.assertEqual(before, len(results))

    def test_aab_du(self):
        global tki
        standard_check(self)

        du = tki.modules.du

        output = du('/tmp')
        self.assertIsInstance(output, BashParser)

    def test_aac_findfs(self):
        """ Requires *.json config file to include findfs_test_uuid, findfs_test_label, findfs_test_value keys  """
        global tki
        standard_check(self)

        config = getConfig()
        uuid_str = config.get('findfs_test_uuid', '')
        label_str = config.get('findfs_test_label', '')
        correct_value = config.get('findfs_test_value', 'error')

        findfs = tki.modules.findfs

        results = findfs.convertUUID(uuid_str)
        self.assertIsInstance(results, str)
        self.assertEqual(results.strip(), correct_value)

        results = findfs.convertLABEL(label_str)
        self.assertIsInstance(results, str)
        self.assertEqual(results.strip(), correct_value)

    def test_aad_findmnt(self):
        global tki
        standard_check(self)

        findmnt = tki.modules.findmnt

        output = findmnt()
        self.assertIsNotNone(output)

        results = findmnt.isMountBind('/')
        self.assertFalse(results)

    def test_zzz_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


# noinspection PyUnresolvedReferences
class TestEFileModules(unittest.TestCase):
    """
        These are CommandModules that either require flags or have special methods that should be tested. Modules that
        do require flags simply confirm they can be created.
    """

    def test_aaa_login(self):
        global tki

        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_aab_touch(self):
        global tki
        global testfilePath
        standard_check(self)

        touch = tki.modules.touch

        results = touch.isWritable('/tmp/')
        self.assertTrue(results)

        results = touch(testfilePath)
        self.assertTrue(results)

    def test_aac_cp(self):
        global tki
        global testfilePath
        standard_check(self)

        cp = tki.modules.cp

        if not tki.modules.touch(testfilePath):
            self.skipTest(f'Touch failed to make test file for cp tset: {testfilePath}')

        results = cp.makeBackup(testfilePath, '/tmp', '.bck', wait=10)
        self.assertTrue(results)

    def test_aad_cat(self):
        global tki
        global testfilePath
        standard_check(self)

        cat = tki.modules.cat
        rm = tki.modules.rm

        results = cat.makeFile(testfilePath)
        self.assertTrue(results)

        results = cat.appendFile(testfilePath, 'test test test', testfilePath + '.bck')
        self.assertTrue(results)

        results = cat(testfilePath, rerun=True)
        self.assertEqual(results, 'test test test')

        results = cat.replaceFile(testfilePath, 'another test', backupRerun=True, backupPath=testfilePath + '.bck2')
        self.assertTrue(results)

        results = cat(testfilePath, rerun=True)
        self.assertEqual(results, 'another test')

        results = cat(testfilePath + '.bck2', rerun=True)
        self.assertEqual(results, 'test test test')

        rm(testfilePath)
        rm(testfilePath + '.bck')
        rm(testfilePath + '.bck2')

    def test_aae_echo(self):
        global tki
        global testfilePath
        standard_check(self)

        echo = tki.modules.echo
        cat = tki.modules.cat
        rm = tki.modules.rm

        results = echo.makeFile(testfilePath)
        self.assertTrue(results)

        results = echo.appendFile(testfilePath, 'test test test', testfilePath + '.bck')
        self.assertTrue(results)

        results = cat(testfilePath, rerun=True)
        self.assertEqual(results, 'test test test')

        results = echo.replaceFile(testfilePath, 'another test', backupRerun=True, backupPath=testfilePath + '.bck2')
        self.assertTrue(results)

        results = cat(testfilePath, rerun=True)
        self.assertEqual(results, 'another test')

        results = cat(testfilePath + '.bck2', rerun=True)
        self.assertEqual(results, 'test test test')

        rm(testfilePath)
        rm(testfilePath + '.bck')
        rm(testfilePath + '.bck2')

    def test_aaf_chmod_chown(self):
        global tki
        global testfilePath
        standard_check(self)

        chmod = tki.modules.chmod
        chown = tki.modules.chown

        if not tki.modules.touch(testfilePath):
            self.skipTest(f'Touch failed to make test file for chmod/chown test: {testfilePath}')

        results = chmod(f'664 {testfilePath}')
        self.assertTrue(results)

        results = chown(f'root:root {testfilePath}')
        self.assertTrue(results)

    def test_aag_find(self):
        global tki
        standard_check(self)

        find = tki.modules.find

        results = find.listLargestFilesOnFilesystem('/tmp', head=10, sort=True, wait=30)
        self.assertIsInstance(results, BashParser)
        self.assertGreaterEqual(len(results), 1)

    def test_aah_getfalc(self):
        global tki
        global testfilePath
        standard_check(self)

        getfacl = tki.modules.getfacl
        if not tki.modules.touch(testfilePath):
            self.skipTest(f'Touch failed to make test file for getfalc test: {testfilePath}')

        results = getfacl.isFacl(testfilePath)
        self.assertFalse(results)

        tki.modules.rm(testfilePath)

    def test_aaj_stat(self):
        global tki
        global testfilePath
        standard_check(self)

        stat = tki.modules.stat
        chmod = tki.modules.chmod
        chown = tki.modules.chown
        if not tki.modules.touch(testfilePath):
            self.skipTest(f'Touch failed to make test file for stat test: {testfilePath}')

        if not chmod(f'664 {testfilePath}'):
            self.skipTest(f'chmod failed to change test file for stat test: {testfilePath}')

        if not chown(f'root:root {testfilePath}'):
            self.skipTest(f'chown failed to change test file for stat test: {testfilePath}')

        results = stat.getOwner(testfilePath)
        self.assertEqual(results, 'root')

        results = stat.getPermission(testfilePath)
        self.assertEqual(results, '664')

        tki.modules.rm(testfilePath)

    def test_aak_ll(self):
        global tki
        global testfilePath
        standard_check(self)

        ll = tki.modules.ll

        if not tki.modules.touch(testfilePath):
            self.skipTest(f'Touch failed to make test file for ll test: {testfilePath}')

        output = ll('/tmp')
        self.assertIsInstance(output, BashParser)

        results = ll.fileExist(testfilePath)
        self.assertTrue(results)

        results = ll.isFileEmpty(testfilePath)
        self.assertTrue(results)

        tki.modules.rm(testfilePath)

    def test_zzz_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


# noinspection PyUnresolvedReferences
class TestEUserModules(unittest.TestCase):
    """
        These are CommandModules that either require flags or have special methods that should be tested. Modules that
        do require flags simply confirm they can be created.
    """

    def test_aaa_login(self):
        global tki

        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_aab_id(self):
        global tki
        standard_check(self)

        idM = tki.modules.id

        myUserID = idM()
        self.assertTrue(hasattr(myUserID, 'uid'))

    def test_zzz_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


# noinspection PyUnresolvedReferences
class TestESystemModules(unittest.TestCase):
    """
        These are CommandModules that either require flags or have special methods that should be tested. Modules that
        do require flags simply confirm they can be created.
    """

    def test_aaa_login(self):
        global tki

        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_aab_journalctl(self):
        global tki
        standard_check(self)

        journalctl = tki.modules.journalctl

        output = journalctl()
        self.assertIsInstance(output, str)

        output = journalctl.journalctlWithFlags('--list-boots', wait=60)
        self.assertIsInstance(output, str)

    def test_aac_lspci(self):
        global tki
        standard_check(self)

        lspci = tki.modules.lspci

        devices = lspci()
        self.assertIsInstance(devices, str)
        deviceList = [device.split() for device in devices.splitlines()]

        results = lspci.hasDevice(deviceList[0][0])
        self.assertTrue(results)

    def test_aad_messages(self):
        """ '/var/log/messages' log file needs to be present on target device """
        global tki
        standard_check(self)

        messages = tki.modules.messages

        if tki.modules.ll.fileExist('/var/log/messages', rerun=True) is False:
            self.skipTest(f'/var/log/messages file not present on the target OS skipping messages test')

        output = messages()
        self.assertIsInstance(output, str)
        self.assertGreaterEqual(len(output.splitlines()), 1)

        messages.makeLogEntry('this is a test')

        sleep(2)  # Gives time for remote logging agent to write to disk. If the disk IO is busy this could fail

        results = messages.getLogsWithinTimeRange(trange='1 minute ago')
        self.assertIsInstance(results, str)
        self.assertGreaterEqual(len(results.splitlines()), 1)
        self.assertIn('this is a test', results)

    def test_aae_os(self):
        global tki
        standard_check(self)

        os = tki.modules.os

        output = os()
        self.assertIsInstance(output, tuple)

        results = os.getOSInfo()
        self.assertIsInstance(results, tuple)

        results = os.isOSSupported()
        self.assertIsInstance(results, bool)

        results = os.getCluster()
        self.assertIsInstance(results, bool)

        results = os.getUptime()
        self.assertIsInstance(results, str)

    def test_aaf_uname(self):
        global tki
        standard_check(self)

        uname = tki.modules.uname

        results = uname()
        self.assertIsInstance(results, str)

        results = uname.getKernelVersion()
        self.assertIsInstance(results, str)

        results = uname.getHostName()
        self.assertIsInstance(results, str)

        results = uname.getArch()
        self.assertIsInstance(results, str)

    def test_aag_uptime(self):
        global tki
        standard_check(self)

        uptime = tki.modules.uptime

        output = uptime()
        self.assertIsInstance(output, str)

        results = uptime.getUptimeViaProc(parse=True)
        self.assertIsInstance(results, str)

        results = uptime.getUptimeViaProc(parse=False)
        self.assertIsInstance(results, str)
        float(results)

    def test_aah_vmstat(self):
        global tki
        standard_check(self)

        vmstat = tki.modules.vmstat

        output = vmstat()
        self.assertIsInstance(output, str)

        self.assertIsNotNone(vmstat.totalMemory)

    def test_aaj_timedatectl(self):
        global tki
        standard_check(self)

        timedatectl = tki.modules.timedatectl

        output = timedatectl()
        self.assertIsInstance(output, str)

        results = timedatectl.getTimezone()
        self.assertIsInstance(results, str)

    def test_zzz_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


# noinspection PyUnresolvedReferences
class TestFMySQLModule(unittest.TestCase):
    """
        This is for MySQL/MariaDB. Currently, this assumes that mysqld is visible in PATH and that root user has
        access to the database without the need for a password
    """

    def test_aaa_login(self):
        global tki

        tki = ldtk.ToolKitInterface(arguments=getArguments(), auto_login=False)
        self.assertIsInstance(tki, ldtk.ToolKitInterface)
        conn = tki.createConnection()
        self.assertIsInstance(conn, threadedSSH)
        self.assertTrue(tki.checkConnection())

    def test_aab_mysql(self):
        """ This assumes that root user can access MySQL server without prompting for password """
        global tki
        standard_check(self)

        mysql = tki.modules.mysql

        output = mysql.isMySQLClientInstalled(wait=10)
        self.assertIsInstance(output, (bool, str))

        if output is False:
            self.skipTest('MySQL Client is not installed on test target skipping... ')

        output = mysql.isMySQLServerInstalled(wait=10)
        self.assertIsInstance(output, (bool, str))

        if output is False:
            self.skipTest('MySQL Server is not installed on test target skipping... ')

        output = mysql.isMySQLRunning(wait=10)
        self.assertIsInstance(output, bool)

        if output is False:
            self.skipTest('MySQL server is not running on test target skipping... ')

        output = mysql.getMySQLStatus(wait=20)
        self.assertIsInstance(output, IndexList)

    def test_zzz_disconnect(self):
        global tki
        standard_check(self)
        tki.disconnect()
        self.assertFalse(tki.checkConnection())


if __name__ == '__main__':
    # use 'export UnitTestingConfigFile="unittesting_centos.json"; python3 unittesting.py' to change the config file
    # to unittesting_centos.json or whatever desired file
    testConfigFile = os.getenv('UnitTestingConfigFile', 'unittesting.json')
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
