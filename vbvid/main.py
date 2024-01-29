import os
import json
import subprocess
from typing import List
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
import argparse

JOINED_FILE_NAME_ROOT='match'
GROUPED_SUBDIR='.grouped'
JOINED_SUBDIR='.joined'
RECODED_SUBDIR='.recoded'
RECODE_CRF_QUALITY=28


@dataclass
class File:
    path: Path
    timestamp: datetime


def main():
    args = parse_args()
    src_path = Path(args.path).resolve()
    grouped_path = src_path / GROUPED_SUBDIR
    joined_path = src_path / JOINED_SUBDIR
    recoded_path = src_path / RECODED_SUBDIR

    if args.recode:
        print('Recode', src_path)
        recode_files(src_path, src_path / RECODED_SUBDIR)
        return

    grouped_dirs = list_dirs(grouped_path)

    # move files into group subdirs.  Then you can double check that they are all for the same/correct
    # game before running the join operation.
    if not grouped_dirs:
        group_files(src_path, recoded_path)
        return

    for group_dir in grouped_dirs:
        joined_file = joined_path / group_dir.with_suffix('.mp4').name
        if not joined_file.exists():
            join_files(group_dir, joined_file)

    recode_files(joined_path, recoded_path)


def list_dirs(parent: Path) -> List[Path]:
    return [
        path for path in parent.iterdir()
        if path.is_dir() and not path.name.startswith('.')
    ]


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


def join_files(src_path: Path, joined_path: Path):
    files = get_sorted_files(src_path)
    groupfile_path = src_path.with_suffix('.txt')
    with open(groupfile_path, 'w') as outfile:
        for file in files:
            outfile.write(f"file '{file.path}'\n")

    joined_path.parent.mkdir(exist_ok=True)

    os.system(f'ffmpeg -f concat -safe 0 -i "{groupfile_path}" -c copy "{joined_path}"')
    groupfile_path.unlink()

def get_sorted_files(src_path: Path) -> List[File]:
    files: List[File] = []
    for file in src_path.iterdir():
        if file.is_file() and file.suffix.lower() in ('.mp4'):
            file_timestamp = datetime.fromtimestamp(file.stat().st_mtime)
            files.append(File(path=file, timestamp=file_timestamp))

    files.sort(key=lambda file: file.path.stem)

    return files


# HEVC encoder version 3.2.1+1-b5c86a64bbbe
#
# HW based scaling example:
# ffmpeg -hwaccel cuda -hwaccel_output_format cuda -i "C:\Users\brand\Videos\MyVideos\2024 AP 162\2023-12-29 Countdown City Classic\.joined\2-EP Strive 162.mp4" -vf "scale_cuda=1920:1080" -tag:v hvc1 -codec:v hevc_nvenc -preset:v p7 -rc-lookahead:v 32 -rc:v constqp -qp:v 38 -b:v 0 -movflags faststart "C:\Users\brand\Videos\MyVideos\2024 AP 162\2023-12-29 Countdown City Classic\.joined\.recoded\2-EP Strive 162.mp4"
def recode_files(src_path: Path, dest_dir: Path):
    dest_dir.mkdir(exist_ok=True)

    for file in list_files(src_path, '*.mp4'):
        output_path = dest_dir / file.name

        if not output_path.exists():
            recode_file(file, output_path)


def recode_file(file: Path, output_path: Path):
    video_info = get_video_info(file)
    # print(video_info['width'], video_info['height'])

    qp_value = 38 if video_info['width'] > 3000 else 32

    # scale_arg = '-vf scale=1920:1080'
    # scale_arg = '-vf scale=2704:1520'
    scale_arg = ''
    # os.system(f'ffmpeg -i "{file}" -codec:v libx265 -vtag hvc1 -preset veryfast {scale_arg} -crf {RECODE_CRF_QUALITY} -movflags faststart "{output_path}"')
    # filter_graph_arg = '-filter:v crop=3840:2880,eq=gamma=1.5'
    # filter_graph_arg = '-filter:v scale_npp=1920:1080'
    filter_graph_arg = ''
    # -tag:v hvc1 is necessary for MacOS and iOS playback compatibility.
    command = f'ffmpeg -hwaccel auto -i "{file}" -tag:v hvc1 {filter_graph_arg} -codec:v hevc_nvenc -preset:v p7 -rc-lookahead:v 32 -rc:v constqp -qp:v {qp_value} -b:v 0K -movflags faststart "{output_path}"'
    print(command)
    os.system(command)


def get_video_info(file: Path) -> dict:
    probe_command = f'ffprobe -v quiet -print_format json -show_format -show_streams "{file}"'
    print(probe_command)
    probe_result = subprocess.run(probe_command, capture_output=True)
    probe_info = json.loads(probe_result.stdout)
    video_streams = [stream for stream in probe_info['streams'] if stream['codec_type'] == 'video']
    return  video_streams[0]


def parse_args():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('path')
    argparser.add_argument('--recode', action='store_true', help='Just perform the recode step in a source directory.')

    return argparser.parse_args()

if __name__ == '__main__':
    main()