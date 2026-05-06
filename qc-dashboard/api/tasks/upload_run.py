from __future__ import annotations

import os
from pathlib import Path, PurePosixPath
from shutil import copyfileobj, rmtree
import stat
import zipfile

from api.app import settings
from api.tasks.utils import split_run_name


PROJECT_ROOT = settings.PROJECT_ROOT
TEMP_RUN_DIR = settings.UPLOAD_DIR
LAB_RUN_DIR = settings.LAB_RUNS_DIR


class UnsafeArchiveError(ValueError):
    pass


def upload_run(zip_path: Path | None = None) -> tuple[str, str]:
    """
    Extract a sequencing run archive and move the validated run files into
    data/lab_runs/{sample}_{run}.
    """
    TEMP_RUN_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = zip_path or next(TEMP_RUN_DIR.glob("*.zip"), None)
    if zip_path is None:
        raise FileNotFoundError("No ZIP archive found for upload.")

    staging_dir = TEMP_RUN_DIR / f"{zip_path.stem}.extract"
    if staging_dir.exists():
        rmtree(staging_dir)
    staging_dir.mkdir(parents=True)

    try:
        safe_extract_zip(zip_path, staging_dir)
        run_dirs = [item for item in staging_dir.iterdir() if item.is_dir()]
        if len(run_dirs) != 1:
            raise ValueError("Archive must contain exactly one top-level run directory.")

        sample, run = get_run_info(run_dirs[0])
        move_lab_runs(sample, run, run_dirs[0])
        return sample, run
    finally:
        delete_temp_dir(staging_dir)
        if zip_path.exists():
            zip_path.unlink()


def safe_extract_zip(zip_path: Path, dest_dir: Path) -> None:
    extracted_bytes = 0
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        members = zip_ref.infolist()
        if len(members) > settings.MAX_ZIP_MEMBERS:
            raise UnsafeArchiveError("Archive contains too many files.")

        for member in members:
            member_path = PurePosixPath(member.filename)
            if not member.filename or "\\" in member.filename:
                raise UnsafeArchiveError(f"Unsafe archive path: {member.filename}")
            if member_path.is_absolute() or ".." in member_path.parts:
                raise UnsafeArchiveError(f"Unsafe archive path: {member.filename}")

            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise UnsafeArchiveError(f"Symlinks are not allowed in uploads: {member.filename}")

            extracted_bytes += member.file_size
            if extracted_bytes > settings.MAX_EXTRACTED_BYTES:
                raise UnsafeArchiveError("Archive extracted size exceeds configured limit.")

        dest_root = dest_dir.resolve()
        for member in members:
            target_path = (dest_dir / member.filename).resolve()
            if target_path != dest_root and not str(target_path).startswith(f"{dest_root}{os.sep}"):
                raise UnsafeArchiveError(f"Unsafe archive path: {member.filename}")

            if member.is_dir():
                target_path.mkdir(parents=True, exist_ok=True)
                continue

            target_path.parent.mkdir(parents=True, exist_ok=True)
            with zip_ref.open(member) as source, open(target_path, "wb") as target:
                copyfileobj(source, target, length=1024 * 1024)


def get_run_info(item: Path) -> tuple[str, str]:
    """
    Extract sample and run information from a top-level directory.
    Expected format: sample_run_part1_part2, with sample in the first segment.
    """
    return split_run_name(item.name)


def move_lab_runs(sample: str, run: str, src_dir: Path) -> None:
    dest_dir = LAB_RUN_DIR / f"{sample}_{run}"
    dest_dir.mkdir(parents=True, exist_ok=True)
    for item in src_dir.iterdir():
        if item.is_dir():
            continue
        target_path = dest_dir / item.name
        if target_path.exists():
            continue
        item.rename(target_path)


def delete_temp_dir(temp_dir: Path) -> None:
    if temp_dir.exists():
        rmtree(temp_dir)


def sanitize_upload_filename(filename: str) -> str:
    name = Path(filename or "").name
    if not name or name != filename or not name.lower().endswith(".zip"):
        raise ValueError("Expected a local .zip filename without path components.")
    return name


def unique_upload_path(filename: str) -> Path:
    TEMP_RUN_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = sanitize_upload_filename(filename)
    candidate = TEMP_RUN_DIR / safe_name
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    for index in range(1, 10_000):
        candidate = TEMP_RUN_DIR / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
    raise FileExistsError("Could not allocate a unique upload filename.")
