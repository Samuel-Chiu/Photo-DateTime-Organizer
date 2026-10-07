# Photo Organizer Script

A Python script that turns folders of loosely named photos into chronologically ordered, consistently named copies, plus a CSV index mapping each new ID back to its original file.

## Running it

```sh
pip install -r requirements.txt   # first time only
```

Put the script in a parent folder, with one subfolder of photos per album:

```
my-photos/
  photoOrganizerScript.py
  Hawaii/        IMG_4821.jpg, IMG_4822.jpg, …
  Graduation/    DSC_0001.jpg, …
```

Then run it:

```sh
python photoOrganizerScript.py
```

Each album gets a sorted copy next to it. The originals are never modified:

```
my-photos/
  hawaiiSorted/
    hawaii-2023-05-01-001.jpg
    hawaii-2023-05-01-002.jpg
    hawaii-2023-05-02-003.jpg
    hawaii_image_data.csv
  graduationSorted/
    …
```

## How it works

1. Loads every image in each subfolder with OpenCV.
2. Reads the date taken from the photo's EXIF data (`DateTime`, `DateTimeOriginal`, or `DateTimeDigitized`) with Pillow.
3. Sorts the album by date and time.
4. Saves a copy of each photo named `<album>-<yyyy-mm-dd>-<###>.jpg`. The `###` counter runs across the whole album in chronological order.
5. Writes `<album>_image_data.csv` with one row per photo:

| Column | Example |
| --- | --- |
| `date` | `2023-05-01` |
| `time` | `08-15-00` |
| `original_filename` | `IMG_4821.jpg` |
| `id` | `hawaii-2023-05-01-001` |

## Notes

- **Every photo needs an EXIF date.** Screenshots, downloaded images, or edited exports that have lost their metadata will stop the script.
- **Only top-level subfolders are albums.** Images sitting next to the script are ignored, and subfolders nested inside an album are not supported.
- **Copies are re-encoded as `.jpg` without EXIF metadata,** because they are written with OpenCV. The CSV keeps the date and time.
- Formats OpenCV can't read (such as HEIC) are skipped.
- Folders whose names end in `Sorted` are skipped, so it's safe to rerun. Reruns overwrite the previous sorted copies.
