from accessible_output2.outputs.auto import Auto

class Speech:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = Auto()
        return cls._instance

    @classmethod
    def speak(cls, text, interrupt=True):
        """Speak text. If interrupt=True, cancel any previous speech first."""
        try:
            cls.get().speak(text, interrupt=interrupt)
        except Exception:
            pass
