import csv
import os
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

