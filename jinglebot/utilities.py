import uuid


def generate_id(length: int = 18):
    """
    Generate a pseudo-random ID.
    :param length: Length of the requested ID.
    :return: Generated id.
    """
    return str(uuid.uuid4().hex)[:length]


def truncate_string(string: str, max_length: int) -> str:
    """
    Truncate a string to a specified maximum length.
    :param string: String to truncate.
    :param max_length: Maximum length of the output string.
    :return: Possibly shortened string.
    """
    if len(string) <= max_length:
        return string
    else:
        return string[:max_length]


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._instances[cls]
