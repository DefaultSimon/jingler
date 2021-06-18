from typing import Tuple, List

import pathlib
from json import dump

import mutagen
from jingler.jingles import JINGLES_DIR
from jingler.utilities import generate_id

files_with_missing_meta: List[Tuple[pathlib.Path, pathlib.Path]] = []
for non_meta_file in filter(lambda file: file.suffix not in [".meta", ".disabled", ".old"], JINGLES_DIR.iterdir()):
    # List every file that is missing .meta
    meta_file = JINGLES_DIR / (non_meta_file.name + ".meta")

    if not meta_file.exists():
        files_with_missing_meta.append((non_meta_file, meta_file))


potential_jingles_formatted = "\n".join([
    f"[{index}] {audio_file.name}" for index, (audio_file, meta_file) in enumerate(files_with_missing_meta)
])

print("---- JINGLE METADATA GENERATOR ----")
print("Select jingle to generate .meta for:")
print()
print(potential_jingles_formatted)
print()

target_index = int(input("Enter index > "))
if target_index < 0 or target_index >= len(files_with_missing_meta):
    print("Invalid index.")
    exit(1)

target_audio_path, target_meta_path = files_with_missing_meta[target_index]

jingle_id = generate_id()
jingle_title = input("Enter title: ")

audio = mutagen.File(str(target_audio_path))
jingle_length = round(audio.info.length, 1) + 0.2
print(f"Length: {jingle_length}s")

print(f"Saving into {target_meta_path}")
with open(str(target_meta_path), "w", encoding="utf8") as target_meta_file:
    dump({
        "id": jingle_id,
        "title": jingle_title,
        "length": jingle_length,
    }, target_meta_file, indent=2, ensure_ascii=False)

print("DONE")
