"""Sort albums of photos into chronologically named copies.

Each immediate subfolder of the root directory is treated as an album. For
every album, the photos are ordered by the date they were taken and copied to
a sibling folder named ``<album>Sorted`` as ``<album>-<yyyy-mm-dd>-<###>.<ext>``.
A CSV index maps each new ID back to its original file. Originals are never
modified.

Usage:
    python photo_organizer.py [ROOT]

ROOT defaults to the folder this script lives in.
"""

from __future__ import annotations

import argparse
import csv
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError

# Constants ---------------------------------------------------------------------------------------

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".gif", ".bmp"}
SORTED_SUFFIX = "Sorted"
CSV_FIELDS = ["date", "time", "original_filename", "id", "date_source"]

# EXIF tag IDs. DateTimeOriginal and DateTimeDigitized live in the Exif
# sub-IFD; DateTime (last modified) lives in the main IFD.
EXIF_IFD = 0x8769
TAG_DATETIME_ORIGINAL = 0x9003
TAG_DATETIME_DIGITIZED = 0x9004
TAG_DATETIME = 0x0132
EXIF_DATE_FORMAT = "%Y:%m:%d %H:%M:%S"


# Data Structures ---------------------------------------------------------------------------------

@dataclass
class Photo:
    path: Path
    taken: datetime
    date_source: str  # which EXIF tag the date came from, or "file_modified"


# Def Section -------------------------------------------------------------------------------------

# Takes in: image file path
# Returns: the capture datetime and the name of the tag it came from
# Purpose: Read when a photo was taken. Prefers DateTimeOriginal, then DateTimeDigitized,
#          then DateTime, and falls back to the file's modification time if none are usable.

def read_capture_time(path: Path) -> tuple[datetime, str]:
    with Image.open(path) as img:
        exif = img.getexif()

    candidates = [
        ("DateTimeOriginal", exif.get_ifd(EXIF_IFD).get(TAG_DATETIME_ORIGINAL)),
        ("DateTimeDigitized", exif.get_ifd(EXIF_IFD).get(TAG_DATETIME_DIGITIZED)),
        ("DateTime", exif.get(TAG_DATETIME)),
    ]

    for source, raw in candidates:
        if not raw:
            continue
        try:
            return datetime.strptime(str(raw).strip("\x00 "), EXIF_DATE_FORMAT), source
        except ValueError:
            continue  # malformed value, e.g. "0000:00:00 00:00:00"

    return datetime.fromtimestamp(path.stat().st_mtime), "file_modified"


# Takes in: album folder path
# Returns: list of Photo objects sorted by capture time
# Purpose: Read the capture date of every image in an album without loading the pixels

def load_album(album: Path) -> list[Photo]:
    photos = []

    for path in sorted(album.iterdir()):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
            continue

        try:
            taken, source = read_capture_time(path)
        except (UnidentifiedImageError, OSError) as err:
            print(f"  skipping {path.name}: {err}")
            continue

        photos.append(Photo(path, taken, source))

    # Filename breaks ties so reruns always produce the same order.
    photos.sort(key=lambda p: (p.taken, p.path.name))
    return photos


# Takes in: album folder path
# Returns: the output folder path, or None if the album had no images
# Purpose: Copy one album into its sorted folder with new names and write the CSV index

def organize_album(album: Path) -> Path | None:
    prefix = album.name.lower()
    photos = load_album(album)

    if not photos:
        print(f"{album.name}: no images found, skipping")
        return None

    output_dir = album.parent / f"{prefix}{SORTED_SUFFIX}"
    output_dir.mkdir(exist_ok=True)

    rows = []
    for number, photo in enumerate(photos, start=1):
        photo_id = f"{prefix}-{photo.taken:%Y-%m-%d}-{number:03d}"

        # copy2 keeps the original bytes and metadata; nothing is re-encoded.
        shutil.copy2(photo.path, output_dir / f"{photo_id}{photo.path.suffix.lower()}")

        rows.append({
            "date": f"{photo.taken:%Y-%m-%d}",
            "time": f"{photo.taken:%H-%M-%S}",
            "original_filename": photo.path.name,
            "id": photo_id,
            "date_source": photo.date_source,
        })

    csv_path = output_dir / f"{prefix}_image_data.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    fallback = sum(r["date_source"] == "file_modified" for r in rows)
    note = f" ({fallback} dated by file time, no EXIF)" if fallback else ""
    print(f"{album.name}: {len(rows)} photos -> {output_dir.name}/{note}")
    return output_dir


# Takes in: root folder path
# Returns: list of album folder paths
# Purpose: Find the immediate subfolders to process, skipping previous output and hidden folders

def find_albums(root: Path) -> list[Path]:
    return sorted(
        d for d in root.iterdir()
        if d.is_dir() and not d.name.endswith(SORTED_SUFFIX) and not d.name.startswith(".")
    )


# Main --------------------------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="folder containing one subfolder per album (default: this script's folder)",
    )
    root = parser.parse_args().root.resolve()

    albums = find_albums(root)
    if not albums:
        print(f"No album folders found in {root}")
        return

    for album in albums:
        organize_album(album)


if __name__ == "__main__":
    main()