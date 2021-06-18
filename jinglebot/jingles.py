import logging
from typing import Dict, Optional, List
from json import load, dump

import pathvalidate
from discord import Enum
from mutagen import File
from pathlib import Path

from jinglebot.utilities import Singleton

log = logging.getLogger(__name__)

JINGLES_DIR = (Path(__file__).parent / "../jingles").resolve()
log.info(f"Jingles directory: {JINGLES_DIR}")


class JingleMode(Enum):
    DISABLED = "disabled"
    SINGLE = "single"
    RANDOM = "random"


def format_jingles_for_pagination(jingle_manager: "JingleManager") -> List[str]:
    """
    Generate a list of formatted jingles.
    Format: "[Jingle ID](Jingle filename) Jingle title"
    :param jingle_manager: JingleManager instance to use.
    :return: A list of formatted jingles.
    """
    return [
        f"[{jingle.id}]({jingle.path.name}) {jingle.title}"
        for index, jingle in enumerate(jingle_manager.jingles_by_id.values())
    ]


def get_audio_file_length(file_path: Path) -> Optional[float]:
    """
    Return the audio file length
    :param file_path: Path to the audio file.
    :return: Length in seconds, or None if couldn't determine.
    """
    audio_file = File(str(file_path.absolute()))
    if audio_file is None:
        return None

    return round(audio_file.info.length, 1)


def save_jingle_meta(jingle_file: Path, jingle_title: str, jingle_id: str):
    """
    Save jingle metadata to "<jingle_audio_filename>.meta".
    :param jingle_file: A pathlib.Path to the jingle audio file.
    :param jingle_title: Desired title for the jingle.
    :param jingle_id: Jingle's new ID.
    """
    # TODO store actual lengths instead and add 0.2 when playing if that's really needed
    jingle_length = round(get_audio_file_length(jingle_file) + 0.2, 1)

    metadata = {
        "id": jingle_id,
        "title": jingle_title,
        "length": jingle_length,
    }

    jingle_meta_file = jingle_file.parent / (jingle_file.name + ".meta")

    with open(str(jingle_meta_file.resolve()), "w", encoding="utf8") as jingle_meta:
        dump(metadata, jingle_meta, indent=2, ensure_ascii=False)

    log.info(
        f"Saved jingle meta for: title=\"{jingle_title}\" path=\"{str(jingle_file)}\", ID=\"{jingle_id}\"."
    )


def sanitize_jingle_path(base_jingle_dir: Path, jingle_name: str) -> Path:
    """
    Clean up the jingle name (prevents weird characters, absolute paths and .. escapes).
    :param base_jingle_dir: Base jingle directory that where the jingle will reside.
    :param jingle_name: Jingle name.
    :return: A complete absolute path to the jingle.
    """
    # Clean up weird parts of the path and only allow a name, no subdirectories
    jingle_name_only: str = Path(jingle_name).name
    sanitized_jingle_name: str = pathvalidate.sanitize_filename(jingle_name_only, replacement_text="_")
    return (base_jingle_dir / Path(sanitized_jingle_name)).resolve()


class Jingle:
    __slots__ = (
        "path", "id", "title", "length"
    )

    def __init__(self, path: Path, id_: str, title: str, length: float):
        self.path = path
        self.id = id_
        self.title = title
        self.length = length


class JingleManager(metaclass=Singleton):
    def __init__(self):
        self.jingles_by_id: Dict[str, Jingle] = {}
        self.reload_available_jingles()

    def reload_available_jingles(self):
        # Reset jingles
        self.jingles_by_id = {}

        jingles_loaded = 0

        for meta_file in filter(lambda file: file.suffix == ".meta", JINGLES_DIR.iterdir()):
            # For each .meta file, make sure the corresponding jingle exists
            jingle_file = JINGLES_DIR / meta_file.name.rstrip(".meta")

            if not jingle_file.exists():
                log.warning(f"Meta file \"{jingle_file}\" does not have a corresponding jingle file, skipping.")
                continue

            # Load .meta JSON file
            with open(str(meta_file), "r", encoding="utf8") as meta_file_obj:
                meta = load(meta_file_obj)

            meta_id = meta.get("id")
            meta_title = meta.get("title")
            meta_length = float(meta.get("length"))
            if meta_id is None:
                log.warning(f"Meta file \"{jingle_file}\" is missing the \"id\" field.")
                continue
            if meta_title is None:
                log.warning(f"Meta file \"{jingle_file}\" is missing the \"title\" field.")
                continue
            if meta_length is None:
                log.warning(f"Meta file \"{jingle_file}\" is missing the \"length\" field.")
                continue

            jingle: Jingle = Jingle(jingle_file, meta_id, meta_title, meta_length)
            self.jingles_by_id[jingle.id] = jingle
            jingles_loaded += 1

        log.info(f"Loaded {jingles_loaded} jingles.")

    def get_jingle_by_id(self, jingle_id: str) -> Optional[Jingle]:
        """
        Return the Jingle by ID, if it exists.
        :param jingle_id: Jingle ID to find.
        :return: Jingle or None if not found.
        """
        return self.jingles_by_id.get(jingle_id)
