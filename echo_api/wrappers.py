import functools


def wrap_method(cls, name, wrapper_method_name):
    # This unbound method will be pulled from the superclass.
    wrapped = getattr(cls, name, wrapper_method_name)

    @functools.wraps(wrapped)
    def wrapper(self, *args, **kwargs):
        wrapper_method = getattr(self, wrapper_method_name)
        return wrapper_method(wrapped.__get__(self, cls), *args, **kwargs)

    return wrapper


def wrap_methods(cls):
    for wrapper_method_name in cls.WRAPPER_METHOD_NAMES:
        for name in cls.WRAPPED_METHODS:
            setattr(cls, name, wrap_method(cls, name, wrapper_method_name))
    return cls