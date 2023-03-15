import os
from typing import List
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

@dataclass
class File:
    path: Path
    timestamp: datetime


def main():
    _src_path = '/mnt/c/Users/brand/Videos/2023-02-25 AP 111'
    src_path = Path(_src_path)

    # group_files(src_path)
    join_files(src_path)


def group_files(src_path: Path):
    file_groups: List[List[File]] = []

    def new_group():
        new_group = []
        file_groups.append(new_group)
        return new_group

    prev_file_timestamp = None
    group = None

    for file in get_sorted_files():
        timestamp_delta = file.timestamp - prev_file_timestamp if prev_file_timestamp else timedelta(minutes=999)
        annotation = ''
        if timestamp_delta > timedelta(minutes=10):
            annotation = '*'
            group = new_group()
        elif timestamp_delta > timedelta(minutes=1):
            annotation = 'TO'
        print(str(file.path.name), file.timestamp, timestamp_delta, annotation)
        prev_file_timestamp = file.timestamp
        group.append(file)

    for idx, group in enumerate(file_groups):
        group_path = src_path / f'group{idx}'
        print(str(group_path))
        group_path.mkdir(exist_ok=True)
        for file in group:
            file.path.rename(group_path / file.path.name)


def join_files(src_path: Path):
    for subdir in src_path.iterdir():
        if not subdir.is_dir(): continue
        files = get_sorted_files(subdir)
        groupfile_path = subdir.with_suffix('.txt')
        with open(groupfile_path, 'w') as outfile:
            for file in files:
                outfile.write(f"file '{file.path}'\n")

        joinedfile_path = subdir.with_suffix('.mp4')
        os.system(f'ffmpeg -f concat -safe 0 -i "{groupfile_path}" -c copy "{joinedfile_path}"')
        groupfile_path.unlink()

def get_sorted_files(src_path: Path) -> List[File]:
    files: List[File] = []
    for file in src_path.iterdir():
        if file.is_file() and file.suffix.lower() in ('.mp4'):
            file_timestamp = datetime.fromtimestamp(file.stat().st_mtime)
            files.append(File(path=file, timestamp=file_timestamp))

    files.sort(key=lambda file: file.timestamp)

    return files


if __name__ == '__main__':
    main()