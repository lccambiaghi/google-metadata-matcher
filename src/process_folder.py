import os
from auxFunctions import *
import json
from PIL import Image

piexifCodecs = [k.casefold() for k in ['TIF', 'TIFF', 'JPEG', 'JPG']]

def get_images_from_folder(folder: str, edited_word: str):
    files = []
    folder_entries = list(os.scandir(folder))

    for entry in folder_entries:
        if entry.is_dir():
            files = files + get_images_from_folder(entry.path, edited_word)
            continue

        if entry.is_file():
            (file_name, ext) = os.path.splitext(entry.name)

            if ext == ".json":
                file = searchMedia(folder, file_name, edited_word)
                files.append((entry.path, file))

    return files

def get_output_filename(root_folder, out_folder, image_path):
    image_name = os.path.basename(image_path)
    new_image_name = image_name + ".jpg"
    image_path_dir = os.path.dirname(image_path)
    relative_to_new_image_folder = os.path.relpath(image_path_dir, root_folder)
    return os.path.join(out_folder, relative_to_new_image_folder, new_image_name)

def processFolder(root_folder: str, edited_word: str, optimize: int, out_folder: str):
    errorCounter = 0
    successCounter = 0

    images = get_images_from_folder(root_folder, edited_word)

    for entry in images:
        metadata_path = entry[0]
        image_path = entry[1]

        if not image_path:
            print("Image for metadata: "+ metadata_path + " not found")
            errorCounter += 1
            continue

        with open(metadata_path, encoding="utf8") as f: 
            data = json.load(f)

        timeStamp = int(data['photoTakenTime']['timestamp'])

        print('Metadata:', metadata_path)

        (_, ext) = os.path.splitext(image_path)

        if not ext[1:].casefold() in piexifCodecs:
            print('Photo format is not supported:', image_path)
            errorCounter += 1
            continue
        
        im = Image.open(image_path, mode="r")

        new_image_path = get_output_filename(root_folder, out_folder, image_path)

        dir = os.path.dirname(new_image_path)

        if not os.path.exists(dir):
            os.makedirs(dir)

        im.save(new_image_path, quality=optimize)
        setFileCreationTime(new_image_path, timeStamp)

        try:
            set_EXIF(image_path, data['geoData']['latitude'], data['geoData']['longitude'], data['geoData']['altitude'], timeStamp)
        except Exception as e: 
            print("Inexistent EXIF data for " + image_path)
            print(e)
            errorCounter += 1
            continue

        successCounter += 1

    print('Process finished')
    print('Success', successCounter)
    print('Failed', errorCounter)
