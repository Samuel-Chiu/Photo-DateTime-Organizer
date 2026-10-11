"""Sort albums of photos into chronologically named copies.

Each immediate subfolder of the root directory is treated as an album. For
every album, the photos are ordered by the date they were taken and copied to
a sibling folder named ``<album>Sorted`` as ``<album>-<yyyy-mm-dd>-<###>.<ext>``.
A CSV index maps each new ID back to its original file. Originals are never
modified.

With --skip-duplicates, byte-identical copies within an album are left out of
the sorted folder and listed in ``<album>_duplicates.csv`` instead.

Usage:
    python photo_organizer.py [ROOT] [--skip-duplicates]

ROOT defaults to the folder this script lives in.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError

# Constants ---------------------------------------------------------------------------------------

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".gif", ".bmp"}
SORTED_SUFFIX = "Sorted"
CSV_FIELDS = ["date", "time", "original_filename", "id", "date_source"]
DUPLICATE_FIELDS = ["duplicate_filename", "kept_filename", "kept_id"]
HASH_CHUNK_BYTES = 1024 * 1024  # read files 1 MB at a time when hashing


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


# Takes in: file path
# Returns: the file's SHA-256 hash as a hex string
# Purpose: Fingerprint a file's exact bytes so identical copies can be detected

def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(HASH_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


# Takes in: list of Photo objects, already sorted
# Returns: (photos to keep, list of (duplicate, kept photo) pairs)
# Purpose: Find byte-identical copies. From each identical set, the photo with the shortest
#          filename is kept, since copies usually gain a suffix ("IMG_1 copy.jpg", "IMG_1 (1).jpg").
#          Only files that share a size are hashed, since different sizes can't match.

def split_duplicates(photos: list[Photo]) -> tuple[list[Photo], list[tuple[Photo, Photo]]]:
    size_counts = Counter(p.path.stat().st_size for p in photos)

    groups: dict[tuple[int, str], list[Photo]] = {}
    for photo in photos:
        size = photo.path.stat().st_size
        if size_counts[size] > 1:
            groups.setdefault((size, file_hash(photo.path)), []).append(photo)

    keeper_of: dict[Path, Photo] = {}
    for group in groups.values():
        keeper = min(group, key=lambda p: (len(p.path.name), p.path.name))
        for photo in group:
            keeper_of[photo.path] = keeper

    unique, duplicates = [], []
    for photo in photos:
        keeper = keeper_of.get(photo.path, photo)
        if keeper is photo:
            unique.append(photo)
        else:
            duplicates.append((photo, keeper))

    return unique, duplicates


# Takes in: album folder path, and whether to skip byte-identical copies
# Returns: the output folder path, or None if the album had no images
# Purpose: Copy one album into its sorted folder with new names and write the CSV index

def organize_album(album: Path, skip_duplicates: bool = False) -> Path | None:
    prefix = album.name.lower()
    photos = load_album(album)

    if not photos:
        print(f"{album.name}: no images found, skipping")
        return None

    duplicates = []
    if skip_duplicates:
        photos, duplicates = split_duplicates(photos)

    output_dir = album.parent / f"{prefix}{SORTED_SUFFIX}"
    output_dir.mkdir(exist_ok=True)

    rows = []
    ids_by_path = {}
    for number, photo in enumerate(photos, start=1):
        photo_id = f"{prefix}-{photo.taken:%Y-%m-%d}-{number:03d}"
        ids_by_path[photo.path] = photo_id

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

    # Log skipped duplicates; clear a stale log from an earlier run if there are none now.
    duplicates_path = output_dir / f"{prefix}_duplicates.csv"
    if duplicates:
        with duplicates_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=DUPLICATE_FIELDS)
            writer.writeheader()
            writer.writerows(
                {
                    "duplicate_filename": dup.path.name,
                    "kept_filename": kept.path.name,
                    "kept_id": ids_by_path[kept.path],
                }
                for dup, kept in duplicates
            )
    else:
        duplicates_path.unlink(missing_ok=True)

    notes = []
    fallback = sum(r["date_source"] == "file_modified" for r in rows)
    if fallback:
        notes.append(f"{fallback} dated by file time, no EXIF")
    if duplicates:
        plural = "s" if len(duplicates) != 1 else ""
        notes.append(f"{len(duplicates)} duplicate{plural} skipped")
    note = f" ({'; '.join(notes)})" if notes else ""
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
    parser.add_argument(
        "--skip-duplicates",
        action="store_true",
        help="leave byte-identical copies out of the sorted folder and list them in "
             "<album>_duplicates.csv",
    )
    args = parser.parse_args()
    root = args.root.resolve()

    albums = find_albums(root)
    if not albums:
        print(f"No album folders found in {root}")
        return

    for album in albums:
        organize_album(album, skip_duplicates=args.skip_duplicates)
    


if __name__ == "__main__":
    main()