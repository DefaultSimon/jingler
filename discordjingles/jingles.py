import pathlib
import logging
from typing import Dict
from json import load

from discordjingles.utilities import Singleton

log = logging.getLogger(__name__)

JINGLES_DIR = pathlib.Path(__file__, "..", "..", "jingles").absolute()
log.info(f"Jingles directory: {JINGLES_DIR}")


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
        self.load_available_jingles()

    def load_available_jingles(self):
        jingles_loaded = 0

        for meta_file in filter(lambda file: file.suffix == ".meta", JINGLES_DIR.iterdir()):
            # For each .meta file, make sure the corresponding jingle exists
            jingle_file = pathlib.Path(JINGLES_DIR, meta_file.name.rstrip(".meta"))

            if not pathlib.Path(JINGLES_DIR, jingle_file).exists():
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
