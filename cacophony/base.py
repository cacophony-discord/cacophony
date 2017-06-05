from collections import ChainMap


class DispatcherMeta(type):
    def __new__(mcs, name, bases, attrs):
        callbacks = ChainMap()
        maps = callbacks.maps
        for base in bases:
            if isinstance(base, DispatcherMeta):
                maps.extend(base.__callbacks__.maps)

        attrs['__callbacks__'] = callbacks
        attrs['dispatcher'] = property(lambda obj: callbacks)
        cls = super().__new__(mcs, name, bases, attrs)
        return cls

    def set_callback(cls, key, callback):
        cls.__callbacks__[key] = callback
        return callback

    def register(cls, key):
        def wrapper(callback):
            return cls.set_callback(key, callback)
        return wrapper


class CacophonyDispatcher(metaclass=DispatcherMeta):
    def dispatch(self, key, default=None):
        return self.dispatcher.get(key, default)


class Cacophony:
    def __init__(self, logger, name, markov_brain, channels=None,
                 chattyness=0.1, *args, **kwargs):
        self.chattyness = chattyness
        self._name = name
        self._brain = markov_brain
        self._is_mute = False
        self._channels = channels or list()  # Should be a list

    def mute(self):
        self._is_mute = True

    def unmute(self):
        self._is_mute = False

    @property
    def is_mute(self):
        return self._is_mute

    @property
    def brain(self):
        return self._brain

    @property
    def name(self):
        return self._name

    @property
    def channels(self):
        return self._channels
