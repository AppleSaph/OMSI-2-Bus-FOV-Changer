# OMSI 2 Bus FOV Changer

This program changes camera FOV values in OMSI 2 `.bus` files.

## How to run the program on Windows

### 1) Get the release file

Download the Windows release from the project release page.
Put it in any folder on your computer.

The release already includes the program. You do not need Python for this version.

### 2) Start the program

Double-click the Windows executable file (`.exe`) to start the program.

## How to use the program

1. **Choose the source**
   - Select **Folder** if you want to check many `.bus` files.
   - Select **Single File** if you want to edit one file only.

2. **Click Browse**
   - Pick the folder or `.bus` file you want to edit.
   - The program will scan it right away.

3. **Check the camera list**
   - The program shows the driver camera positions it found.
   - Each row has the current FOV and a `New FOV` field.

4. **Change the FOV values**
   - Type a new number in the `New FOV` field for one row.
   - Or select several rows and use the bulk FOV field at the top.

5. **Save the changes**
   - Click **Save Changes** when you are ready.
   - If backup is turned on, the program will make `.bak` files first.

## Small notes

- Use the backup option if you want a copy of the original file.
- The program only changes the driver camera FOV values.
- If you use the Linux or Apple Silicon release, start the provided executable for that system in the same way.

## Camera Descriptions

The tool extracts and displays driver camera descriptions from `.bus` files. Descriptions typically appear on the line immediately before a camera tag and follow a numbering pattern:

```text
	0: Looking leftmost
[add_camera_driver]
-1.5
4.18
1.89
-0.06
55
-170
-5
```


## Development

Install dev dependencies:

```bash
python -m pip install -e .[dev]
```

Run tests:

```bash
python -m pytest -v
```

## Python Version Support

PySide6 currently publishes wheels only for supported CPython releases. If you use an unreleased interpreter (for example 3.15 alpha), install a stable Python version (3.10–3.14) for GUI execution.

## Safety

**Always keep backups of your OMSI files.** While the tool can generate `.bak` files, we recommend independent backups before running batch operations on important files.

**USE AT YOUR OWN CAUTION. I AM NOT RESPONSIBLE FOR LOST OR DAMAGED FILES.**

