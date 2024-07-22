import os
from tkinter import Tk, filedialog, simpledialog, messagebox

lines_changed = []


def get_files(folder, only_buses):
    if only_buses:
        return [f for f in os.listdir(folder) if f.endswith('.bus') and not f.endswith('.bak')]
    else:
        return [f for f in os.listdir(folder) if not f.endswith('.bak')]


def replace_fov(file, number, backup):
    file_changed = False
    # read
    with open(file, 'r') as f:
        lines = f.readlines()
    # replace
    i = 0
    while i < len(lines):
        line = lines[i]
        if "[add_camera_driver]" in line:
            file_changed = True
            i += 5
            old_value = lines[i].replace('\r', '').replace('\n', '')
            print(f"Replaced FOV from {old_value} to {number} on line {i} in file {file}")
            lines_changed.append(f"Replaced FOV from {old_value} to {number} on line {i} in file {file}")
            lines[i] = str(number) + '\n'
        i += 1
    # write
    if file_changed:
        if backup:
            with open(file + '.bak', 'w') as f:
                f.writelines(lines)
        with open(file, 'w') as f:
            f.writelines(lines)
    else:
        print(f"No FOV found in file {file}")


def replace_in_files(folder, files, number, backup):
    for f in files:
        file = os.path.join(folder, f)
        replace_fov(file, number, backup)


if __name__ == '__main__':
    root = Tk()
    root.withdraw()
    #     ask for folder with windows pop up
    folder = filedialog.askdirectory()
    if folder is None or folder == "":
        messagebox.showinfo("No folder selected", "No folder selected. Program will exit")
        exit(1)
    # ask for number with windows pop up
    number = simpledialog.askstring("FOV selection", "Enter the desired FOV")
    if number is None or number == "":
        messagebox.showinfo("No number entered", "No number entered. Program will exit")
        exit(1)
    # ask for boolean with windows pop up
    only_buses = messagebox.askyesno("Only buses", "Do you want to only include buses?")
    if only_buses is None:
        messagebox.showinfo("No selection made", "No selection made. Program will exit")
        exit(1)
    # ask for backup with windows pop up
    backup = messagebox.askyesno("Backup", "Do you want to backup the files?")
    if backup is None:
        messagebox.showinfo("No selection made", "No selection made. Program will exit")
        exit(1)
    # get all files in folder and subfolders that end with .bus if only_buses is true
    files = get_files(folder, only_buses)
    print(files)
    if len(files) == 0:
        messagebox.showinfo("No files found", "No files found in the folder")
    # replace the fov in all files
    replace_in_files(folder, files, number, backup)
    messagebox.showinfo("Finished", f"Finished replacing FOV in {len(files)} files.\n\n{lines_changed}")
