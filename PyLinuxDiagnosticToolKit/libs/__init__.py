import inspect
import os
import sys
import warnings

sys.path.append(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))


def ignore_warnings(func):
    def wrapper(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            func(self, *args, **kwargs)
    return wrapper
