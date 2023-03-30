import os
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass(frozen=True)
class File:
    img_path: Optional[str] = None
    vid_path: Optional[str] = None


def get_files_from_folder(input_folder: str) -> List[File]:
    files: List[File] = []
    already_added: List[str] = []

    folder_entries = list(os.scandir(input_folder))

    for entry in folder_entries:
        if entry.is_dir():
            files = files + get_files_from_folder(entry.path)
            continue

        if entry.is_file():
            if entry.path in already_added:
                continue

            root_path, ext = os.path.splitext(entry.path)

            # process image
            if str.lower(ext) in [".heic", ".jpg", ".jpeg", ".png"]:
                # try to find associated video
                vid_path = root_path + "_3" + ".mov"
                if os.path.exists(vid_path):
                    files.append(File(img_path=entry.path, vid_path=vid_path))
                    already_added.append(vid_path)
                else:
                    files.append(File(img_path=entry.path))

            # process video
            elif str.lower(ext) in [".mov", ".mp4"]:
                # try to find associated image
                img_path = root_path[:-2] + ".heic"
                if os.path.exists(img_path):
                    files.append(File(img_path=img_path, vid_path=entry.path))
                    already_added.append(img_path)
                else:
                    files.append(File(vid_path=entry.path))

            elif str.lower(ext) in [".aae"]:
                continue

            else:
                raise ValueError(f"Unexpected extension: {ext}")

    return files


def get_timestamp(path: str) -> int:
    return int(os.path.getmtime(path))


def rename_all_images_from_apple_photos_library(input_folder: str, output_folder: str) -> None:
    """
    Main function to bulk-rename files in an Apple Photos library, to
    be given as `input_folder`
    """
    files = get_files_from_folder(input_folder)

    for file in files:
        timestamp = get_timestamp(file.img_path if file.img_path else file.vid_path)
        dt = datetime.fromtimestamp(timestamp)

        output_subfolder = os.path.join(output_folder, str(dt.year), str(dt.month))
        if not os.path.exists(output_subfolder):
            os.makedirs(output_subfolder)

        for path in [p for p in [file.img_path, file.vid_path] if p is not None]:
            _, ext = os.path.splitext(path)
            new_path = os.path.join(output_subfolder, f"{timestamp}{ext}")

            os.rename(path, new_path)

    return None


def rename_all_timestamped_images(input_folder: str, output_folder: str) -> None:
    """
    Ad-hoc main function used to bulk-rename already timestamped files
    all residing in one folder, output of the 'apply_metadata'
    pipeline on the Google Photos takeout exports
    """
    entries = list(os.scandir(input_folder))
    entries = [e for e in entries if not e.is_dir()]

    for entry in entries:
        timestamp = get_timestamp(entry.path)
        dt = datetime.fromtimestamp(timestamp)

        output_subfolder = os.path.join(output_folder, str(dt.year), str(dt.month))
        if not os.path.exists(output_subfolder):
            os.makedirs(output_subfolder)

        _, ext = os.path.splitext(entry.path)
        new_path = os.path.join(output_subfolder, f"{timestamp}{ext}")

        os.rename(entry.path, new_path)

    return None
