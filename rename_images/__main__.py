from .rename_images_pipeline import rename_all_images_from_apple_photos_library, rename_all_timestamped_images


def main(input_folder: str, output_folder: str):
    # rename_all_images_from_apple_photos_library(input_folder, output_folder)
    rename_all_timestamped_images(input_folder, output_folder)

if __name__ == "__main__":
    main(
        # input_folder="/Users/cambiaghiluca/Pictures/Photos Library.photoslibrary/originals",
        input_folder="/Users/cambiaghiluca/git/google-metadata-matcher/output",
        output_folder="/Users/cambiaghiluca/git/google-metadata-matcher/output"
    )
