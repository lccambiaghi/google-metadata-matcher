import os
import json
from PIL import Image
from pillow_heif import register_heif_opener
import time
from datetime import datetime
import piexif
from fractions import Fraction

register_heif_opener()

CLR = "\x1B[0K"
CURSOR_UP_FACTORY = lambda upLines : "\x1B[" + str(upLines) + "A"
CURSOR_DOWN_FACTORY = lambda upLines : "\x1B[" + str(upLines) + "B"

OrientationTagID = 274

piexifCodecs = [k.casefold() for k in ['TIF', 'TIFF', 'JPEG', 'JPG', 'HEIC', 'PNG']]


# Credit: https://stackoverflow.com/questions/3173320/text-progress-bar-in-terminal-with-block-characters
def progressBar(iterable, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r", upLines = 0):
    UP = "\x1B[" + str(upLines + 1) + "A"

    total = len(iterable)
    # Progress Bar Printing Function
    def printProgressBar (iteration):
        percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
        filledLength = int(length * iteration // total)
        bar = fill * filledLength + '-' * (length - filledLength)

        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Initial Call
    printProgressBar(0)
    # Update Progress Bar
    for i, item in enumerate(iterable):
        yield item
        print(UP)
        printProgressBar(i + 1)
    # Print New Line on Complete
    print()

# Function to search media associated to the JSON
def searchMedia(path, title, editedWord):
    title = fixTitle(title)

    (file_name, ext) = os.path.splitext(title)

    possible_titles = [
        title,
        title + ".jpg",
        title + ".JPG",
        str(file_name + "-" + editedWord + "." + ext),
        str(file_name + "(1)." + ext),
    ]

    for title in possible_titles:
        imgpath = os.path.join(path, title)

        if os.path.exists(imgpath):
            vidpath = os.path.join(path, file_name + ".MP4")
            if os.path.exists(vidpath):
                return imgpath, vidpath
            else:
                return imgpath, None

    return None, None

# Supress incompatible characters
def fixTitle(title):
    return str(title).replace("%", "").replace("<", "").replace(">", "").replace("=", "").replace(":", "").replace("?","").replace(
        "¿", "").replace("*", "").replace("#", "").replace("&", "").replace("{", "").replace("}", "").replace("\\", "").replace(
        "@", "").replace("!", "").replace("¿", "").replace("+", "").replace("|", "").replace("\"", "").replace("\'", "")

# Recursive function to search name if its repeated
def checkIfSameName(title, titleFixed, matchedFiles, recursionTime):
    if titleFixed in matchedFiles:
        (file_name, ext) = os.path.splitext(titleFixed)
        titleFixed = file_name + "(" + str(recursionTime) + ")" + "." + ext
        return checkIfSameName(title, titleFixed, matchedFiles, recursionTime + 1)
    else:
        return titleFixed

def setFileCreationTime(filepath, timeStamp):
    date = datetime.fromtimestamp(timeStamp)
    modTime = time.mktime(date.timetuple())
    os.utime(filepath, (modTime, modTime))

def to_deg(value, loc):
    """convert decimal coordinates into degrees, munutes and seconds tuple
    Keyword arguments: value is float gps-value, loc is direction list ["S", "N"] or ["W", "E"]
    return: tuple like (25, 13, 48.343 ,'N')
    """
    if value < 0:
        loc_value = loc[0]
    elif value > 0:
        loc_value = loc[1]
    else:
        loc_value = ""
    abs_value = abs(value)
    deg = int(abs_value)
    t1 = (abs_value - deg) * 60
    min = int(t1)
    sec = round((t1 - min) * 60, 5)
    return (deg, min, sec, loc_value)


def change_to_rational(number):
    """convert a number to rational
    Keyword arguments: number
    return: tuple like (1, 2), (numerator, denominator)
    """
    f = Fraction(str(number))
    return (f.numerator, f.denominator)

def set_geo_exif(exif_dict, lat, lng, altitude):
    lat_deg = to_deg(lat, ["S", "N"])
    lng_deg = to_deg(lng, ["W", "E"])

    exiv_lat = (change_to_rational(lat_deg[0]), change_to_rational(lat_deg[1]), change_to_rational(lat_deg[2]))
    exiv_lng = (change_to_rational(lng_deg[0]), change_to_rational(lng_deg[1]), change_to_rational(lng_deg[2]))

    altitudeRef = 1 if altitude > 0 else 0

    gps_ifd = {
        piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
        piexif.GPSIFD.GPSAltitudeRef: altitudeRef,
        piexif.GPSIFD.GPSAltitude: change_to_rational(round(abs(altitude), 2)),
        piexif.GPSIFD.GPSLatitudeRef: lat_deg[3],
        piexif.GPSIFD.GPSLatitude: exiv_lat,
        piexif.GPSIFD.GPSLongitudeRef: lng_deg[3],
        piexif.GPSIFD.GPSLongitude: exiv_lng,
    }

    exif_dict['GPS'] = gps_ifd

def set_date_exif(exif_dict, timestamp):
    dateTime = datetime.fromtimestamp(timestamp).strftime("%Y:%m:%d %H:%M:%S")
    exif_dict['0th'][piexif.ImageIFD.DateTime] = dateTime
    exif_dict["0th"][piexif.ImageIFD.Orientation] = 1
    exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = dateTime
    exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = dateTime

def adjust_exif(exif_info, metadata):
    timeStamp = int(metadata['photoTakenTime']['timestamp'])

    exif_dict = piexif.load(exif_info)

    lat = metadata['geoData']['latitude']
    lng = metadata['geoData']['longitude']
    altitude = metadata['geoData']['altitude']

    set_date_exif(exif_dict, timeStamp)
    set_geo_exif(exif_dict, lat, lng, altitude)

    return piexif.dump(exif_dict)


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
