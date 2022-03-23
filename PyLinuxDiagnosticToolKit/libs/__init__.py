import inspect, os, sys
sys.path.append(os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe()))))
import warnings


def ignore_warnings(func):
    def wrapper(self, *args, **kwargs):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", ResourceWarning)
            func(self, *args, **kwargs)
    return wrapper


def dummy_func(*args, **kwargs):
    return kwargs.get('_default', None)
