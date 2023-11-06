import os

from src.config import settings


# TODO Delete this
# https://hypothesis-vstorm.atlassian.net/jira/software/projects/PA/boards/2?selectedIssue=PA-84
def delete_files_from_media():
    for dirname in os.listdir(settings.MEDIA_DIR):
        dir_path = os.path.join(settings.MEDIA_DIR, dirname)
        if dirname != ".gitkeep" and os.path.isdir(dir_path):
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(dir_path)
