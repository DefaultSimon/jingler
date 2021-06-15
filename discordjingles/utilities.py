import uuid


def generate_id(length: int = 18):
    """
    Generate a pseudo-random ID.
    :param length: Length of the requested ID.
    :return: Generated id.
    """
    return str(uuid.uuid4().hex)[:length]
