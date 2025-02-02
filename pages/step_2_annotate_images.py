import glob
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import streamlit as st
import yaml
from loguru import logger
from streamlit_shortcuts import button

DEFAULT_IMAGE_WIDTH = 400
DEFAULT_BACKUP_FOLDER = "backups"
DEFAULT_BACKUP_EVERY_N_IMAGES = 5


def add_empty_rows(n_rows: int):
    for _ in range(n_rows):
        st.text(" ")


def show_image(url: str, img_width: int) -> None:
    st.image(url, caption=url, width=img_width)


class BidirectionalURLsIterator:

    def __init__(self, image_urls: list[str], current_image_index: int = 0):
        assert image_urls
        self._image_urls = image_urls
        self.current_image_index = current_image_index

    def previous(self):
        if self.current_image_index == 0:
            return
        self.current_image_index -= 1

    def next(self):
        if self.current_image_index == len(self._image_urls) - 1:
            return
        self.current_image_index += 1

    def current_image_url(self) -> str:
        return self._image_urls[self.current_image_index]

class AnnotationsPerImage:
    ANNOTATIONS_STATE_KEY = 'annotations'

    def __init__(
            self,
            backup_file_path_created_from: str,
            all_tags: list[str],
            annotations: list[dict],
            current_image_index: int,
    ):
        image_urls = [obj["image_URL"] for obj in annotations]
        assert len(set(image_urls)) == len(image_urls), f"Image URLs are not unique"
        self.dict_img_url_to_tags = {obj["image_URL"]: (obj["tags"] or []) for obj in annotations}
        self.check_tags_of_images(all_tags, self.dict_img_url_to_tags)
        self.backup_file_path_created_from = backup_file_path_created_from
        self.all_tags = all_tags
        assert len(set(all_tags)) == len(all_tags), f"tags {all_tags} are not unique"
        self.image_iterator = BidirectionalURLsIterator(image_urls, current_image_index)
        self.n_images_annotated_in_last_backup = self.get_number_of_images_annotated()

    @staticmethod
    def check_tags_of_images(all_tags, dict_img_url_to_tags:dict[str, list[str]]):
        for tags in dict_img_url_to_tags.values():
            assert set(tags).issubset(all_tags), f"tags {tags} are not a subset of declared tags {all_tags}"

    @classmethod
    def create_singleton_instance(cls,
                                  backup_file_path: str,
                                  all_tags: list[str],
                                  annotations: list[dict],
                                  current_image_index: int,
                                  ) -> "AnnotationsPerImage":
        if cls.ANNOTATIONS_STATE_KEY not in st.session_state or (
                backup_file_path != st.session_state[cls.ANNOTATIONS_STATE_KEY].backup_file_path_created_from
        ):
            # we create a new object if no object is in the session state yet or if config file has changed
            st.session_state[cls.ANNOTATIONS_STATE_KEY] = AnnotationsPerImage(
                backup_file_path, all_tags, annotations, current_image_index
            )
            logger.info(f"Created new object AnnotationsPerImage from backup file {backup_file_path}")
        return st.session_state[cls.ANNOTATIONS_STATE_KEY]

    @classmethod
    def get_instance(cls) -> Optional["AnnotationsPerImage"]:
        return st.session_state.get(cls.ANNOTATIONS_STATE_KEY)

    @classmethod
    def create_from_yaml_file(cls, backup_file_path: str) -> "AnnotationsPerImage":
        with open(backup_file_path, "r") as f:
            dict_ = yaml.safe_load(f)
        for key in "tags", "annotations", "current_image_index":
            assert key in dict_, f"Yaml backup file is missing the key '{key}' (file {backup_file_path})"
        return cls.create_singleton_instance(
            backup_file_path,
            dict_["tags"],
            dict_["annotations"],
            dict_["current_image_index"],
        )

    def save_to_yaml_file(self, backup_file_path: str) -> None:
        data = {
            "tags": self.all_tags,
            "current_image_index": self.image_iterator.current_image_index,
            "annotations": [{"image_URL": image_URL, "tags": tags} for image_URL, tags in self.dict_img_url_to_tags.items()],
        }
        with open(backup_file_path, "w") as f:
            yaml.dump(data, f, sort_keys=False)
        logger.info(f"Saved AnnotationsPerImage object to yaml file {backup_file_path}")
        self.n_images_annotated_in_last_backup = self.get_number_of_images_annotated()

    def set_tags_for_image_url(self, img_url: str, tags: list[str]) -> None:
        assert set(tags).issubset(self.all_tags), f"some tag in {tags} is not included in allowed tags {self.all_tags}"
        self.dict_img_url_to_tags[img_url] = tags

    def get_tags_for_image_url(self, img_url: str) -> list[str]:
        return self.dict_img_url_to_tags.get(img_url, [])

    def get_number_of_images(self) -> int:
        return len(self.dict_img_url_to_tags)

    def get_number_of_images_annotated(self) -> int:
        return sum(len(tags) > 0 for tags in self.dict_img_url_to_tags.values())

    def get_number_of_tags(self) -> int:
        return len(self.all_tags)


class BackupFilesRetriever:
    def __init__(
            self,
            backup_folder: str,
            backup_name_prefix: str = "annotations_"
    ):
        self.backup_folder = Path(backup_folder)
        self.backup_name_prefix = backup_name_prefix

    def get_backup_files_from_newest_to_oldest(self) -> list[str]:
        files = glob.glob(str(self.backup_folder / "*.yml"))
        files = sorted(files, key=os.path.getctime, reverse=True)
        return files

    def create_new_backup_file_path(self, n_images_annotated: int, n_images_total: int, n_tags: int) -> str:
        now_str = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        return str(self.backup_folder / f"{self.backup_name_prefix}_{n_tags}_tags_"
                                        f"{n_images_annotated}_over_{n_images_total}_images_tagged_"
                                        f"{now_str}.yml")


def select_tags(all_tags: list[str], tags_selected_in_the_past: list[str], image_url: str) -> list[str]:
    st.write("Select tags for this image :")
    selected_tags = []
    for tag in all_tags:
        is_selected_in_the_past = (tag in tags_selected_in_the_past)
        if st.checkbox(tag, value=is_selected_in_the_past, key=f"check_box_{tag}_{image_url}"):
            selected_tags.append(tag)

    # st.write(f"{len(selected_tags)} selected tags:", selected_tags)
    return selected_tags


def do_nothing():
    pass


def main():
    st.set_page_config(layout="wide")

    with st.sidebar:
        img_width = st.number_input(
            label="Image width", min_value=300, value=DEFAULT_IMAGE_WIDTH, max_value=700, step=100
        )
        folder_backup = st.text_input("Enter folder with backup file(s) :", value=DEFAULT_BACKUP_FOLDER)
        assert os.path.isdir(folder_backup), f"Folder {os.path.abspath(folder_backup)} does not exist"
        backup_every_n_images = st.number_input(label="Backup every N images (choose N) :",
                                                min_value=1, value=DEFAULT_BACKUP_EVERY_N_IMAGES, max_value=10, step=1)

    backup_files_retriever = BackupFilesRetriever(folder_backup)
    backup_file_paths = backup_files_retriever.get_backup_files_from_newest_to_oldest()
    if not backup_file_paths:
        st.info(f"No backup file found in folder : `{os.path.abspath(folder_backup)}`")
        st.info("You need to create an initial backup file with image URLs "
                 f"using the page '`create initial backup file`' on the left side.")
        return

    if (obj := AnnotationsPerImage.get_instance()) is not None:
        current_backup_file_path_index = backup_file_paths.index(obj.backup_file_path_created_from)
    else:
        current_backup_file_path_index = 0  # no AnnotationsPerImage object created yet, we create it from latest backup
    col1, col2 = st.columns(2)
    with col1:
        backup_file_path = st.selectbox("Select backup file used to load initial state :", backup_file_paths,
                                        index=current_backup_file_path_index)
    with col2:
        add_empty_rows(2)
        st.write(f"Latest backup file in folder : `{backup_file_paths[0] if backup_file_paths else None}`")

    annotations = AnnotationsPerImage.create_from_yaml_file(backup_file_path)

    n_images = annotations.get_number_of_images()
    n_images_annotated = annotations.get_number_of_images_annotated()
    st.write(f"Image {annotations.image_iterator.current_image_index + 1}/{n_images} "
             f"({n_images_annotated} images annotated)")

    col_img, col_tags, col_prev_next = st.columns([2, 1, 1])

    with col_img:
        image_url = annotations.image_iterator.current_image_url()
        show_image(image_url, img_width)

    with col_tags:
        add_empty_rows(10)
        selected_tags = select_tags(annotations.all_tags, annotations.get_tags_for_image_url(image_url), image_url)
        if not selected_tags:
            st.warning("You must select at least one tag")

        annotations.set_tags_for_image_url(image_url, selected_tags)

    with col_prev_next:
        add_empty_rows(10)
        if button("Next image (right arrow with keyboard)", "ArrowRight", on_click=do_nothing):
            # if st.button("Next image"):
            annotations.image_iterator.next()

            # handle backup
            n_images_annotated = annotations.get_number_of_images_annotated()
            if (n_images_annotated%backup_every_n_images==0 or n_images_annotated == n_images) and (
                    n_images_annotated > annotations.n_images_annotated_in_last_backup
            ):
                backup_file_path = backup_files_retriever.create_new_backup_file_path(
                    n_images_annotated, n_images, annotations.get_number_of_tags()
                )
                annotations.save_to_yaml_file(backup_file_path)

            # refresh
            st.rerun()

        add_empty_rows(1)

        if button("Previous image (left arrow with keyboard)", "ArrowLeft", on_click=do_nothing):
            # if st.button("Previous image"):
            annotations.image_iterator.previous()
            st.rerun()

        if st.button("Save state to new backup file"):
            backup_file_path = backup_files_retriever.create_new_backup_file_path(
                n_images_annotated, n_images, annotations.get_number_of_tags()
            )
            annotations.save_to_yaml_file(backup_file_path)
            st.success(f"Saved state to new backup file `{backup_file_path}`")


if __name__ == '__main__':
    main()
