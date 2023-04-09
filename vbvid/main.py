import os
from typing import List
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import argparse

JOINED_FILE_NAME_ROOT='match'
RECODED_SUBDIR='recoded'
RECODE_CRF_QUALITY=28


@dataclass
class File:
    path: Path
    timestamp: datetime


def main():
    args = parse_args()
    src_path = Path(args.path)

    joined_dirs = list_dirs(src_path, f'{JOINED_FILE_NAME_ROOT}*')

    if joined_files:=list_files(src_path, f'{JOINED_FILE_NAME_ROOT}*.*'):
        recode_files(joined_files)
    elif joined_dirs:
        # If there are no group* dirs, then perform grouping operation
        join_files(src_path)
    else:
        # Otherwise move files into group subdirs.  Then you can double check that they are all for the same/correct
        # game before running the join operation.
        group_files(src_path)


def list_dirs(parent: Path, glob: str) -> List[Path]:
    return [path for path in parent.glob(glob) if path.is_dir()]


def list_files(parent: Path, glob: str) -> List[Path]:
    return [path for path in parent.glob(glob) if path.is_file()]


def group_files(src_path: Path):
    file_groups: List[List[File]] = []

    def new_group():
        new_group = []
        file_groups.append(new_group)
        return new_group

    prev_file_timestamp = None
    group = None

    for file in get_sorted_files(src_path):
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
        group_path = src_path / f'match{idx+1}'
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

# HEVC encoder version 3.2.1+1-b5c86a64bbbe
def recode_files(file_paths: List[Path]):
    for file in file_paths:
        output_path = file.parent / RECODED_SUBDIR / file.name
        output_path.parent.mkdir(exist_ok=True)

        # scale_arg = '-vf scale=1920:1080'
        # scale_arg = '-vf scale=2704:1520'
        scale_arg = ''
        os.system(f'ffmpeg -i "{file}" -codec:v libx265 -vtag hvc1 -preset veryfast {scale_arg} -crf {RECODE_CRF_QUALITY} -movflags faststart "{output_path}"')
        # return # TEMP TEST


def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("path")

    return argparser.parse_args()

if __name__ == '__main__':
    main()