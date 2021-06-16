import pathlib
import logging
from typing import Dict, Optional
from json import load, dump

from mutagen import File

from jinglebot.utilities import Singleton, generate_id

log = logging.getLogger(__name__)

JINGLES_DIR = pathlib.Path(__file__, "..", "..", "jingles").resolve()
log.info(f"Jingles directory: {JINGLES_DIR}")


def generate_jingle_meta(jingle_file: pathlib.Path, jingle_title: str):
    """
    Generate and save jingle metadata.
    :param jingle_file: A pathlib.Path to the jingle file.
    :param jingle_title: Desired title for the jingle.
    """
    jingle_id = generate_id()

    audio_file = File(str(jingle_file.absolute()))
    jingle_length = round(audio_file.info.length, 1) + 0.2

    metadata = {
        "id": jingle_id,
        "title": jingle_title,
        "length": jingle_length,
    }

    jingle_meta_file = jingle_file.parent / (jingle_file.name + ".meta")

    with open(str(jingle_meta_file.resolve()), "w", encoding="utf8") as jingle_meta:
        dump(metadata, jingle_meta, indent=2, ensure_ascii=False)


class Jingle:
    __slots__ = (
        "path", "id", "title", "length"
    )

    def __init__(self, path: pathlib.Path, id_: str, title: str, length: float):
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
