import os
import argparse
import pathlib
import sys
import shutil
import time
import configparser


# Remove quotes from the path
def clean_path(path):
    if path.endswith('"'):
        path = path[:-1]
    if path.startswith('"'):
        path = path[1:]
    return path


# recursivly get a list of subfolders
def get_subfolders(folder, root_folder=None):
    if not root_folder:
        root_folder = folder
    subfolders = []
    for item in folder.iterdir():
        if item.is_dir():
            subfolders.append(item.parts[len(root_folder.parts) :])
            subfolders.extend(get_subfolders(item, root_folder=root_folder))
    return subfolders


# recuresivly get a list of files in a given folder
# files are returned as an array of parts
# eg. ['folder1', 'folder2', 'file.txt']
def recursivly_get_files(folder):
    folderpartslen = len(folder.parts)
    found_files = []
    for root, dirs, files in folder.walk():
        for file in files:
            found_files.append(root.joinpath(file).parts[folderpartslen:])
    return set(found_files)


def sync_files(source_folder, destination_folder, new_folders, dry_run=False):
    source_files = recursivly_get_files(source_folder)
    dest_files = recursivly_get_files(destination_folder)

    files_to_copy = source_files - dest_files
    num_files_to_copy = len(files_to_copy)
    strlen = len(str(num_files_to_copy))

    prevFile = ""
    currFile = ""

    if len(files_to_copy) == 0:
        print("No new files to copy.")
        return

    print(f"There are {num_files_to_copy} files to copy.")
    if input("Do you want to copy the new files? (y/N): ").lower() != "y":
        return

    start_time = time.time()
    for i, f in enumerate(files_to_copy):
        try:
            sys.stdout.flush()
            if not dry_run:
                elapsed_time = time.time() - start_time
                file_number = str.rjust(str(i + 1), strlen, "0")
                file_count = str.rjust(str(num_files_to_copy), strlen)

                avg_time = elapsed_time / (i + 1)
                remaining_time = avg_time * (num_files_to_copy - i - 1)
                # format remaining_time
                remaining_time = time.strftime("%H:%M:%S", time.gmtime(remaining_time))
                sys.stdout.write(
                    f"\r copying file {file_number} of {file_count}  - approx remaining time {remaining_time} - hit <ctrl>+c to cancel                    "
                )
                # copy2 preserves metadata
                prevFile = currFile
                currFile = destination_folder.joinpath(*f)
                shutil.copy2(
                    source_folder.joinpath(*f), destination_folder.joinpath(*f)
                )
            else:
                print(
                    f"Would copy file: {source_folder.joinpath(*f)} -> {destination_folder.joinpath(*f)}"
                )
        except KeyboardInterrupt:
            print("\n\nUser cancelled operation")
            print(f"   Copying file: {currFile} \n   Previous file was {prevFile}")
            exit(1)


def sync_modified_files(source_folder, destination_folder, dry_run=False):
    source_files = recursivly_get_files(source_folder)
    dest_files = recursivly_get_files(destination_folder)
    modified_files = []

    for i, f in enumerate(source_files):
        source_file = source_folder.joinpath(*f)
        dest_file = destination_folder.joinpath(*f)

        if source_file.stat().st_mtime > dest_file.stat().st_mtime:
            print(f"Modified file: {source_file} -> {dest_file}")
            modified_files.append([source_file, dest_file])

    if len(modified_files) == 0:
        print("No modified files found.")
        return

    print(f"There are {len(modified_files)} modified files.")
    if input("Do you want to copy the changes? (y/N): ").lower() != "y":
        return

    for filepair in modified_files:
        source_file = filepair[0]
        dest_file = filepair[1]

        if not dry_run:
            print(f"Copy file: {source_file} -> {dest_file}")
            shutil.copy2(source_file, dest_file)
        else:
            print(f"Would copy file: {source_file} -> {dest_file}")


def delete_files(source_folder, destination_folder, dry_run=False):
    source_files = recursivly_get_files(source_folder)
    dest_files = recursivly_get_files(destination_folder)

    files_to_delete = dest_files - source_files

    print(f"There are {len(files_to_delete)} files to delete.")

    choice = input(
        "Do you want to delete the files? (y)es (N)o Show (L)ist of files (y/N/l): "
    )
    if choice.lower() == "y":
        print("Deleting Files")
    elif choice.lower() == "l":
        for f in files_to_delete:
            delete_file = destination_folder.joinpath(*f)
            print(f"Will delete file: {delete_file}")
        if input("Do you want to continue? (y/N): ").lower() != "y":
            return
    else:
        return

    for f in files_to_delete:
        delete_file = destination_folder.joinpath(*f)

        if not dry_run:
            print(f"Deleting file: {delete_file}")
            delete_file.unlink()
        else:
            print(f"Would delete file: {delete_file}")


def sync_folders(source_folder, destination_folder, dry_run=False):
    # Get subfolders
    source_subfolders = set(get_subfolders(source_folder))
    destination_subfolders = set(get_subfolders(destination_folder))
    folders_to_create = source_subfolders - destination_subfolders
    folders_to_delete = destination_subfolders - source_subfolders

    new_folders = []

    # sort in order of length so that we create the parent folders first
    for folder in sorted(folders_to_create, key=len):
        new_folder = destination_folder.joinpath(*folder)
        old_folder = source_folder.joinpath(*folder)
        new_folders.append(new_folder)
        if not dry_run:
            print(f"Creating folder: {new_folder}")
            new_folder.mkdir()
            # setting modtime to the source folder's modtime but this does not work because the file copy
            # which occurs later updates the modtime set here
            # TODO: consider keeping a list of folders created and setting the modtime after all files are copied
            modtime = old_folder.stat().st_mtime
            os.utime(new_folder, (modtime, modtime))
        else:
            print(f"Would create folder: {new_folder}")

    # sort in order of length reversed so that we delete the child
    # folders first
    for folder in sorted(folders_to_delete, key=len, reverse=True):
        delete_folder = destination_folder.joinpath(*folder)
        if not dry_run:
            print(f"Deleting folder: {delete_folder}")
            delete_folder.rmdir()
        else:
            print(f"Would delete folder: {delete_folder}")

    return new_folders


def main():
    help_epilog = """Common usage is somthing along the lines of 
    \r\n\r\n
    python localfilesync.py /path/to/source /path/to/destination --dry-run --modified --delete

"""
    parser = argparse.ArgumentParser(
        description="Folder synchronization tool", epilog=help_epilog
    )

    parser.add_argument(
        "--config",
        help="Path to the configuration file",
        default="localfilesync.ini",
    )

    parser.add_argument(
        "source_folder",
        help="Path to the source folder",
    )
    parser.add_argument("destination_folder", help="Path to the destination folder")
    parser.add_argument("--dry-run", help="Dry run", action="store_true")
    parser.add_argument("--modified", help="Sync modified files", action="store_true")
    parser.add_argument(
        "--delete",
        help="Delete files in 'destination' which were deleted in 'source'",
        action="store_true",
    )

    args = parser.parse_args()

    source_folder = pathlib.Path(clean_path(args.source_folder))
    destination_folder = pathlib.Path(clean_path(args.destination_folder))

    # Check if source folder exists
    if not source_folder.exists():
        print(f"Source folder '{source_folder}' does not exist.")
        return

    # Check if destination folder exists
    if not destination_folder.exists():
        print(f"Destination folder '{destination_folder}' does not exist.")
        return

    print(
        f"Source folder: {source_folder}",
        f"Destination folder: {destination_folder}",
        sep="\n",
    )
    print("dry run mode:        ", args.dry_run)
    print("sync modified files: ", args.modified)
    print("delete files:        ", args.delete)
    if input("Do you want to continue? (y/N): ").lower() != "y":
        return

    new_folders = sync_folders(source_folder, destination_folder, dry_run=args.dry_run)
    sync_files(source_folder, destination_folder, new_folders, dry_run=args.dry_run)

    if args.modified:
        sync_modified_files(source_folder, destination_folder, dry_run=args.dry_run)

    if args.delete:
        delete_files(source_folder, destination_folder, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
