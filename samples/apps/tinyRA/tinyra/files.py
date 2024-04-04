import os
from typing import Protocol, List, AsyncGenerator, runtime_checkable
from pathlib import Path

from .exceptions import FileManagerError


@runtime_checkable
class FileManager(Protocol):

    async def get_root_path(self) -> Path:
        pass

    async def list_files(self) -> List[Path]:
        pass

    async def open_file(self, path: Path) -> bool:
        pass

    async def delete_files(self, path_list: List[Path]) -> AsyncGenerator[Path, None]:
        pass


class BaseFileManager:

    def __init__(self, root_path: Path):
        self._root_path = root_path

    def get_root_path(self) -> Path:
        return self._root_path

    async def list_files(self) -> List[Path]:
        return [f for f in self._root_path.iterdir() if f.is_file()]

    async def open_file(self, path: Path) -> bool:
        try:
            await self._open_file(path)
            return True
        except Exception as e:
            raise FileManagerError(f"Error opening file {path}", e)

    async def delete_files(self, path_list: List[Path]) -> AsyncGenerator[Path, None]:
        """Delete the files."""
        for path in path_list:

            # check if root path is a parent of path
            if not path.is_relative_to(self._root_path):
                raise FileManagerError(f"Invalid path {path}")

            try:
                os.remove(path)
                yield path
            except Exception as e:
                raise FileManagerError(f"Error deleting file {path}", e)


class CodespacesFileManager(BaseFileManager):

    async def _open_file(self, path: Path) -> bool:
        os.system(f"code '{path}'")


class MacOSFileManager(BaseFileManager):

    async def _open_file(self, path: Path) -> bool:
        os.system(f"open '{path}'")


class WindowsFileManager(BaseFileManager):

    async def _open_file(self, path: Path) -> bool:
        os.system(f"start '{path}'")
