import os
from tkinter import Tk, filedialog, simpledialog, messagebox


def get_files(folder, only_buses):
    if only_buses:
        return [f for f in os.listdir(folder) if f.endswith('.bus') and not f.endswith('.bak')]
    else:
        return [f for f in os.listdir(folder) if not f.endswith('.bak')]


def replace_fov(file, number, backup):
    file_changed = False
    file_lines_changed = []
    # read
    try:
        with open(file, 'r', encoding='utf-8') as f:
            original_lines = f.readlines()
        lines = original_lines.copy()
    except FileNotFoundError:
        messagebox.showerror("File Not Found", f"File not found: {file}")
        return []
    except PermissionError:
        messagebox.showerror("Permission Error", f"Permission denied: {file}")
        return []
    # replace
    line_index = 0
    while line_index < len(lines):
        line = lines[line_index]
        if "[add_camera_driver]" in line:
            file_changed = True
            line_index += 5
            if line_index >= len(lines):
                print(f"Unexpected end of file {file} after [add_camera_driver]")
                break
            old_value = lines[line_index].replace('\r', '').replace('\n', '')
            print(f"Replaced FOV from {old_value} to {number} on line {line_index} in file {file}")
            file_lines_changed.append(f"Replaced FOV from {old_value} to {number} on line {line_index} in file {file}")
            lines[line_index] = str(number) + '\n'
        line_index += 1
    # write
    if file_changed:
        if backup:
            with open(file + '.bak', 'w', encoding='utf-8') as f:
                f.writelines(original_lines)
        with open(file, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    else:
        print(f"No FOV found in file {file}")
    return file_lines_changed


def replace_in_files(folder, files, number, backup):
    all_lines_changed = []
    for filename in files:
        file_path = os.path.join(folder, filename)
        file_lines_changed = replace_fov(file_path, number, backup)
        all_lines_changed.extend(file_lines_changed)
    return all_lines_changed


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
    if number is None or number.strip() == "":
        messagebox.showinfo("No number entered", "No number entered. Program will exit")
        exit(1)
    # Validate FOV input is a number (int or float)
    try:
        float(number)
    except ValueError:
        messagebox.showinfo("Invalid input", "FOV must be a valid number. Program will exit")
        exit(1)
    # ask for boolean with windows pop up
    only_buses = messagebox.askyesno("Only buses", "Do you want to only include buses?")
    # ask for backup with windows pop up
    backup = messagebox.askyesno("Backup", "Do you want to backup the files?")
    # get all files in folder and subfolders that end with .bus if only_buses is true
    files = get_files(folder, only_buses)
    print(files)
    if len(files) == 0:
        messagebox.showinfo("No files found", "No files found in the folder")
    # replace the fov in all files
    lines_changed = replace_in_files(folder, files, number, backup)
    messagebox.showinfo("Finished", f"Finished replacing FOV in {len(files)} files.\n\n{lines_changed}")
