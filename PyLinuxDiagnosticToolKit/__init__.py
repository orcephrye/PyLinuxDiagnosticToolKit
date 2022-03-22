import inspect, os, sys
sys.path.append(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
# A requirement for portray
# sys.path.append(
#     f"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))}"
#     f"/PyCustomCollections")
# sys.path.append(
#     f"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))}"
#     f"/PyCustomParsers")
# sys.path.append(
#     f"{os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))))}"
#     f"/PyMultiTasking")
# End requirement
import PyLinuxDiagnosticToolKit.libs
import PyLinuxDiagnosticToolKit.sshConnector
import PyLinuxDiagnosticToolKit.LinuxModules


def find_modules(workingDir=None, moduleSubDir=None):
    """
        Function for unit testing purposes. This is used to find all existing modules for PyLDTK
    """
    if workingDir:
        startingPath = workingDir.strip('/') + '/' + 'LinuxModules/'
    else:
        startingPath = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))) + '/LinuxModules/'

    if moduleSubDir:
        startingPath += moduleSubDir.strip('/') + '/'

    def _isDirFilter(item):
        return os.path.isdir(startingPath+item) and not item.startswith('__')

    def _isModule(item):
        return item.count('module') > 0 and item.endswith('.py')

    output = []
    directories = list(filter(_isDirFilter, os.listdir(startingPath)))
    while directories:
        newDirectories = []
        for dir in directories:
            files = [f'{dir}/{file}' for file in os.listdir(startingPath+dir)]
            for file in filter(_isModule, files):
                output.append(file.split('/')[-1][:-9])
            newDirectories.extend(list(filter(_isDirFilter, files)))
        directories = newDirectories

    return output
