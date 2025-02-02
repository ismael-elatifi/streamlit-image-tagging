import os

import streamlit as st
from pages.step_2_annotate_images import BackupFilesRetriever, AnnotationsPerImage, DEFAULT_BACKUP_FOLDER


HEIGHT_TEXT_INPUT = 400


def split_strip_lines_and_remove_blank_lines(text: str) -> list[str]:
    return [line_stripped for line in text.split("\n") if (line_stripped := line.strip())]


def main():
    st.set_page_config(layout="wide")
    folder_backup = st.text_input("Enter folder for backup file(s) :", value=DEFAULT_BACKUP_FOLDER)
    os.makedirs(folder_backup, exist_ok=True)
    col1, col2 = st.columns(2)
    with col1:
        tags_str = st.text_area("Copy-paste tags here (one per line) :", height=HEIGHT_TEXT_INPUT)
    with col2:
        image_urls_str = st.text_area("Copy-paste image paths/URLs here (one per line) :", height=HEIGHT_TEXT_INPUT)
    tags = split_strip_lines_and_remove_blank_lines(tags_str)
    image_urls = split_strip_lines_and_remove_blank_lines(image_urls_str)
    if not tags or not image_urls:
        return

    backup_file_path = BackupFilesRetriever(folder_backup).create_new_backup_file_path(
            n_images_annotated=0, n_images_total=len(image_urls), n_tags=len(tags)
    )
    empty_annotations = AnnotationsPerImage(
        backup_file_path_created_from=backup_file_path,
        all_tags=tags,
        annotations=[{"image_URL": image_url, "tags": []} for image_url in image_urls],
        current_image_index=0
    )
    if st.button("Create initial backup file"):
        empty_annotations.save_to_yaml_file(backup_file_path)
        st.success(f"Successfully created initial backup file `{backup_file_path}`")
        st.success(f"Select this file in `annotate images` page to start annotating.")


if __name__ == '__main__':
    main()
