import uuid
from typing import Any, Union


def generate_id(length: int = 18):
    """
    Generate a pseudo-random ID.
    :param length: Length of the requested ID.
    :return: Generated id.
    """
    return str(uuid.uuid4().hex)[:length]


def generate_jingle_id():
    """
    Generate a 6-character-long ID containing hex chars.

    Collision probability when generating 5k IDs is around
    1 - e^((-5000*4999)/(2*(16)^6)) = 0.525
    That's good enough.
    """
    return uuid.uuid4().hex.upper()[:6]


def sanitize_jingle_code(content: str) -> str:
    return str(content).strip().upper()


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


def get_nth_with_default(list_: Union[list, tuple], n: int, default: Any = None) -> Any:
    """
    Return the n-th element of a list, or default if the list does not have the n-th element.
    :param list_: List or tuple to get from.
    :param n: Index to get.
    :param default: In case the list is not long enough, return this default.
    :return: n-th element of the list, or the default if there is no n-th element in the list.
    """
    if n < 0 or n >= len(list_):
        return default
    else:
        return list_[n]


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)

        return cls._instances[cls]
