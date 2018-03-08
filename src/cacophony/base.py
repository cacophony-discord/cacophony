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
