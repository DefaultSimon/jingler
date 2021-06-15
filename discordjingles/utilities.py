import uuid


def generate_id(length: int = 18):
    """
    Generate a pseudo-random ID.
    :param length: Length of the requested ID.
    :return: Generated id.
    """
    return str(uuid.uuid4().hex)[:length]


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._instances[cls]
