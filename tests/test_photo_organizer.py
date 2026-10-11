import csv
import os
import shutil
from datetime import datetime

from PIL import Image

import photo_organizer as po

# Utility Functions -------------------------------------------------------------------------------


def make_photo(path, original=None, modified=None, color="red"):
    """Write a small JPEG with optional EXIF dates."""
    img = Image.new("RGB", (8, 8), color)
    exif = Image.Exif()
    if modified:
        exif[po.TAG_DATETIME] = modified
    if original:
        exif.get_ifd(po.EXIF_IFD)[po.TAG_DATETIME_ORIGINAL] = original
    img.save(path, exif=exif)


def read_index(folder, name):
    with open(folder / f"{name}_image_data.csv", newline="") as f:
        return list(csv.DictReader(f))

def make_album_with_duplicate(tmp_path):
    """Album with IMG_1, an exact copy of it, and a different photo."""
    album = tmp_path / "Trip"
    album.mkdir()
    make_photo(album / "IMG_1.jpg", original="2023:05:01 08:15:00", color="red")
    shutil.copy(album / "IMG_1.jpg", album / "IMG_1 copy.jpg")
    make_photo(album / "IMG_2.jpg", original="2023:05:01 08:15:00", color="blue")
    return album


# Tests -------------------------------------------------------------------------------------------

# Purpose: tests to make sure that the original capture time is used
def test_prefers_datetime_original_over_datetime(tmp_path):
    photo = tmp_path / "a.jpg"
    make_photo(photo, original="2023:05:01 08:15:00", modified="2024:01:01 00:00:00")
    taken, source = po.read_capture_time(photo)
    assert taken == datetime(2023, 5, 1, 8, 15, 0)
    assert source == "DateTimeOriginal"

# Purpose: tests that 
def test_falls_back_to_file_time_without_exif(tmp_path):
    photo = tmp_path / "screenshot.png"
    Image.new("RGB", (8, 8)).save(photo)
    os.utime(photo, (0, datetime(2022, 3, 4, 5, 6, 7).timestamp()))
    taken, source = po.read_capture_time(photo)
    assert taken == datetime(2022, 3, 4, 5, 6, 7)
    assert source == "file_modified"

# Purpose: checks that a placeholder date of all zeros is skipped and the next tag is used
def test_malformed_exif_date_is_ignored(tmp_path):
    photo = tmp_path / "a.jpg"
    make_photo(photo, original="0000:00:00 00:00:00", modified="2021:07:08 09:10:11")
    taken, source = po.read_capture_time(photo)
    assert taken == datetime(2021, 7, 8, 9, 10, 11)
    assert source == "DateTime"



# This is the end-to-end test for one album. It checks four things at once:
#     - The output folder gets the right name.
#     - The copies are named in date order.
#     - The text file is ignored.
#     - The CSV lists photos in the right order with the right time format.

def test_album_is_sorted_named_and_indexed(tmp_path):
    album = tmp_path / "Hawaii"
    album.mkdir()
    make_photo(album / "IMG_2.jpg", original="2023:05:02 10:00:00")
    make_photo(album / "IMG_1.jpg", original="2023:05:01 08:15:00")
    (album / "notes.txt").write_text("not a photo")

    out = po.organize_album(album)

    assert out == tmp_path / "hawaiiSorted"
    assert sorted(p.name for p in out.glob("*.jpg")) == [
        "hawaii-2023-05-01-001.jpg",
        "hawaii-2023-05-02-002.jpg",
    ]
    rows = read_index(out, "hawaii")
    assert [r["original_filename"] for r in rows] == ["IMG_1.jpg", "IMG_2.jpg"]
    assert rows[0]["time"] == "08-15-00"


# It compares the copy to the original byte by byte
def test_copies_are_byte_identical(tmp_path):
    album = tmp_path / "Trip"
    album.mkdir()
    make_photo(album / "IMG_1.jpg", original="2023:05:01 08:15:00")
    out = po.organize_album(album)
    copy = out / "trip-2023-05-01-001.jpg"
    assert copy.read_bytes() == (album / "IMG_1.jpg").read_bytes()


# This checks that album detection ignores …Sorted output, hidden folders, and loose files, and returns albums in alphabetical order
def test_find_albums_skips_output_and_hidden_folders(tmp_path):
    for name in ["Hawaii", "hawaiiSorted", ".git", "Graduation"]:
        (tmp_path / name).mkdir()
    (tmp_path / "loose.jpg").write_bytes(b"")
    assert [a.name for a in po.find_albums(tmp_path)] == ["Graduation", "Hawaii"]

# Asserts that the duplicates exist by default
def test_duplicates_are_kept_by_default(tmp_path):
    album = make_album_with_duplicate(tmp_path)
    out = po.organize_album(album)
    assert len(list(out.glob("*.jpg"))) == 3
    assert not (out / "trip_duplicates.csv").exists()

# Asserts that the copies are skipped and the original kept
def test_skip_duplicates_copies_one_and_logs_the_rest(tmp_path):
    album = make_album_with_duplicate(tmp_path)
    out = po.organize_album(album, skip_duplicates=True)

    # The shorter name (the original, not "IMG_1 copy.jpg") is the one kept.
    rows = read_index(out, "trip")
    assert [r["original_filename"] for r in rows] == ["IMG_1.jpg", "IMG_2.jpg"]
    assert len(list(out.glob("*.jpg"))) == 2

    with open(out / "trip_duplicates.csv", newline="") as f:
        dupes = list(csv.DictReader(f))
    assert dupes == [{
        "duplicate_filename": "IMG_1 copy.jpg",
        "kept_filename": "IMG_1.jpg",
        "kept_id": "trip-2023-05-01-001",
    }]
    # Originals are never touched.
    assert (album / "IMG_1.jpg").exists() and (album / "IMG_1 copy.jpg").exists()

# Another test for duplicates 
def test_same_size_different_content_is_not_a_duplicate(tmp_path):
    a, b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    a.write_bytes(b"\x00" * 100)
    b.write_bytes(b"\x01" * 100)
    photos = [po.Photo(a, datetime(2023, 1, 1), "DateTime"),
              po.Photo(b, datetime(2023, 1, 1), "DateTime")]
    unique, duplicates = po.split_duplicates(photos)
    assert unique == photos and duplicates == []
