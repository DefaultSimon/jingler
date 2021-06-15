from enum import Enum
from discord import VoiceState


class VoiceStateAction(Enum):
    JOINED = "joined"
    LEFT = "left"

    SELF_MUTED = "self_muted"
    SELF_UNMUTED = "self_unmuted"
    SELF_DEAFENED = "self_deafened"
    SELF_UNDEAFENED = "self_undeafened"

    SERVER_MUTED = "server_muted"
    SERVER_UNMUTED = "server_unmuted"
    SERVER_DEAFENED = "server_deafened"
    SERVER_UNDEAFENED = "server_undeafened"

    STARTING_STREAM = "starting_stream"
    ENDING_STREAM = "ending_stream"
    STARTING_VIDEO = "starting_video"
    ENDING_VIDEO = "ending_video"

    AFK = "afk"
    NOT_AFK = "not_afk"

    UNKNOWN = "unknown"


def get_voice_state_change(before: VoiceState, after: VoiceState) -> VoiceStateAction:
    """
    Try to find what action was taken between the two VoiceStates.
    :param before: A snapshot of "before".
    :param after: A snapshot of "after".
    :return: A VoiceStateAction representing the detected action that took place between before and after.
    """
    if before.channel is None and after.channel is not None:
        return VoiceStateAction.JOINED
    if before.channel is not None and after.channel is None:
        return VoiceStateAction.LEFT

    elif not before.mute and after.mute:
        return VoiceStateAction.SERVER_MUTED
    elif before.mute and not after.mute:
        return VoiceStateAction.SERVER_UNMUTED
    elif not before.deaf and after.deaf:
        return VoiceStateAction.SERVER_DEAFENED
    elif before.deaf and not after.deaf:
        return VoiceStateAction.SERVER_UNDEAFENED

    elif not before.self_mute and after.self_mute:
        return VoiceStateAction.SELF_MUTED
    elif before.self_mute and not after.self_mute:
        return VoiceStateAction.SELF_UNMUTED
    elif not before.self_deaf and after.self_deaf:
        return VoiceStateAction.SELF_DEAFENED
    elif before.self_deaf and not after.self_deaf:
        return VoiceStateAction.SELF_UNDEAFENED

    elif not before.self_stream and after.self_stream:
        return VoiceStateAction.STARTING_STREAM
    elif before.self_stream and not after.self_stream:
        return VoiceStateAction.ENDING_STREAM

    elif not before.self_video and after.self_video:
        return VoiceStateAction.STARTING_VIDEO
    elif before.self_video and not after.self_video:
        return VoiceStateAction.ENDING_VIDEO

    elif not before.afk and after.afk:
        return VoiceStateAction.AFK
    elif before.afk and not after.afk:
        return VoiceStateAction.NOT_AFK

    else:
        return VoiceStateAction.UNKNOWN
