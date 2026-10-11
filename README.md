# Photo DateTime Organizer

[![tests](https://github.com/Samuel-Chiu/Photo-DateTime-Organizer/actions/workflows/tests.yml/badge.svg)](https://github.com/Samuel-Chiu/Photo-DateTime-Organizer/actions/workflows/tests.yml)

A Python tool that turns folders of loosely named photos into chronologically ordered, consistently named copies—preserving original EXIF metadata and logging a full tracking index in CSV.

```
my-photos/                                 my-photos/
├── Hawaii/                                ├── Hawaii/
│   ├── IMG_4821.jpg                       │   ├── IMG_4821.jpg
│   └── IMG_4822.jpg                       │   └── IMG_4822.jpg
│                                          │
└── Graduation/                            ├── hawaiiSorted/
    └── DSC_0001.jpg       ───────►        │   ├── hawaii-2023-05-01-001.jpg
                                           │   ├── hawaii-2023-05-01-002.jpg
                                           │   └── hawaii_image_data.csv
                                           │
                                           └── Graduation/
                                               └── ...

```

---

## Quick start

### Setup & Execution

```sh
pip install -r requirements.txt
python photoOrganizerScript.py

```

### Input & Output Folder Layout

Place `photoOrganizerScript.py` inside your main working folder alongside individual album subfolders:

```
my-photos/
├── photoOrganizerScript.py
├── Hawaii/               # Album folder
│   ├── IMG_4821.jpg
│   └── IMG_4822.jpg
└── Graduation/           # Album folder
    └── DSC_0001.jpg

```

For every target album subfolder, a new sorted directory named `<album>Sorted/` is generated right next to it. Original files and folders remain completely untouched.

---

## How it works

1. **Album Detection:** Automatically processes top-level subfolders in the root directory. Hidden directories (starting with `.`) and existing output directories ending in `Sorted` are automatically skipped.
2. **Date Source Priority:** Determines the exact capture date and time by evaluating metadata in the following hierarchy:
    1. EXIF `DateTimeOriginal`
    2. EXIF `DateTimeDigitized`
    3. EXIF `DateTime`
    4. File system creation/modification time (fallback when EXIF data is missing)

3. **Sort Order:** Sorts images chronologically by capture time. If multiple photos share the exact same timestamp, the original filename is used as a tie-breaker.
4. **Naming & Byte-for-Byte Copying:** Performs a lossless byte-for-byte copy (preserving original EXIF metadata) using the structure:
```
<album>-<yyyy-mm-dd>-<###>.<ext>

```


*The `<###>` sequence counter runs sequentially across the entire album in chronological order.*

5. **CSV Indexing:** Generates `<album>_image_data.csv` inside each sorted output directory to map transformed files back to their source metadata:

| Column | Example | Description |
| --- | --- | --- |
| `date` | `2023-05-01` | Image capture date (`YYYY-MM-DD`) |
| `time` | `08:15:00` | Image capture time (`HH:MM:SS`) |
| `original_filename` | `IMG_4821.jpg` | Source filename before organizing |
| `id` | `hawaii-2023-05-01-001` | Unique generated file identifier |
| `output_filename` | `hawaii-2023-05-01-001.jpg` | Final organized filename on disk |

--- 

## Skipping duplicates

With `--skip-duplicates`, files in the same album that are byte-for-byte identical are copied only once. Two files count as duplicates only if every byte matches (compared by SHA-256 hash), so an edited or re-exported version of a photo is kept.

From each set of identical files, the one with the shortest filename is kept, since copies usually gain a suffix (`IMG_1 copy.jpg`, `IMG_1 (1).jpg`). The skipped files are listed in `<album>_duplicates.csv`:

| Column | Example |
| --- | --- |
| `duplicate_filename` | `IMG_1 (1).jpg` |
| `kept_filename` | `IMG_1.jpg` |
| `kept_id` | `hawaii-2023-05-01-001` |

Nothing is deleted from the original album; delete the files listed in the CSV yourself if you want them gone. Without the flag, every file is copied, duplicates included.

---


## Notes

* **Supported Formats:** Works with standard image formats (e.g., JPEG, PNG, TIFF, WebP).
* **Nested Folders:** Only immediate top-level subfolders are treated as albums. Subfolders nested deeper inside an album are not scanned.
* **Rerun Behavior:** If an output folder `<album>Sorted/` already exists, remove or clear it before rerunning to prevent stale file accumulation or duplicate processing.

---

## Development

### Setup Dev Environment & Run Tests

```sh
pip install -r requirements-dev.txt
pytest

```

### Test Coverage & CI

The test suite validates:

* Correct album detection and folder filtering.
* EXIF date metadata extraction, priority fallback ordering, and file time handling.
* Chronological sorting accuracy and filename tie-breaking.
* File naming conventions and byte-for-byte copy fidelity.
* CSV index file generation and column structure integrity.

Continuous Integration (CI) automatically executes the entire test suite on every `git push`.



