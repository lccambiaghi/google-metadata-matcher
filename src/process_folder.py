import os
from auxFunctions import searchMedia, adjust_exif, progressBar, setFileCreationTime
import json
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

CLR = "\x1B[0K"
CURSOR_UP_FACTORY = lambda upLines : "\x1B[" + str(upLines) + "A"
CURSOR_DOWN_FACTORY = lambda upLines : "\x1B[" + str(upLines) + "B"

OrientationTagID = 274

piexifCodecs = [k.casefold() for k in ['TIF', 'TIFF', 'JPEG', 'JPG', 'HEIC', 'PNG']]

def get_images_from_folder(folder: str, edited_word: str):
    files: list[tuple[str, str, str]] = []
    folder_entries = list(os.scandir(folder))

    for entry in folder_entries:
        if entry.is_dir():
            files = files + get_images_from_folder(entry.path, edited_word)
            continue

        if entry.is_file():
            (file_name, ext) = os.path.splitext(entry.name)

            if ext == ".json" and file_name != "metadata":
                imgpath, vidpath = searchMedia(folder, file_name, edited_word)
                files.append((entry.path, imgpath, vidpath))

    return files

def get_output_filename(root_folder, out_folder, image_path, timestamp):
    (image_name, ext) = os.path.splitext(os.path.basename(image_path))
    new_image_name = str(timestamp) + ext
    return os.path.join(out_folder, new_image_name)


def processFolder(root_folder: str, edited_word: str, optimize: int, out_folder: str, max_dimension):
    errorCounter = 0
    successCounter = 0

    images = get_images_from_folder(root_folder, edited_word)

    print("Total images found:", len(images))

    for entry in progressBar(images, upLines = 2):
        metadata_path = entry[0]
        image_path = entry[1]
        video_path = entry[2]

        print("\n", "Current file:", image_path, CLR)

        if not image_path:
            print(CURSOR_UP_FACTORY(2), "Missing image for:", metadata_path, CLR, CURSOR_DOWN_FACTORY(2))

            errorCounter += 1
            continue

        (_, ext) = os.path.splitext(image_path)

        # get timestamp from metadata
        with open(metadata_path, encoding="utf8") as f:
            metadata = json.load(f)
        timeStamp = int(metadata['photoTakenTime']['timestamp'])

        # move image
        if image_path and os.path.exists(image_path):
            new_image_path = get_output_filename(root_folder, out_folder, image_path, timeStamp)
            dir = os.path.dirname(new_image_path)
            if not os.path.exists(dir):
                os.makedirs(dir)

            if str.lower(ext) in [".mov", ".mp4", ".m4v"]:
                os.rename(image_path, new_image_path)
            else:
                image = Image.open(image_path, mode="r").convert('RGB')

                image_exif = image.getexif()
                if OrientationTagID in image_exif:
                    orientation = image_exif[OrientationTagID]

                    if orientation == 3:
                        image = image.rotate(180, expand=True)
                    elif orientation == 6:
                        image = image.rotate(270, expand=True)
                    elif orientation == 8:
                        image = image.rotate(90, expand=True)

                if "exif" in image.info:
                    new_exif = adjust_exif(image.info["exif"], metadata)
                    image.save(new_image_path, quality=optimize, exif=new_exif)
                else:
                    image.save(new_image_path, quality=optimize)
            setFileCreationTime(new_image_path, timeStamp)

        # move video (for live photo)
        if video_path and os.path.exists(video_path):
            new_video_path = get_output_filename(root_folder, out_folder, video_path, timeStamp)
            dir = os.path.dirname(new_image_path)
            if not os.path.exists(dir):
                os.makedirs(dir)
            os.rename(video_path, new_video_path)
            setFileCreationTime(new_video_path, timeStamp)

        os.remove(metadata_path)
        successCounter += 1

    print()
    print('Metadata merging has been finished')
    print('Success', successCounter)
    print('Failed', errorCounter)
