import os
from pathlib import Path
from typing import Protocol


class DocumentStorage(Protocol):
    def put(self, key: str, data: bytes) -> None:
        ...

    def get(self, key: str) -> bytes:
        ...

    def delete(self, key: str) -> None:
        ...


class LocalDocumentStorage:
    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _path(self, key: str) -> Path:
        if not key or "/" in key or "\\" in key or key in {".", ".."}:
            raise ValueError("invalid internal storage key")
        path = (self._root / key[:2] / key).resolve()
        if self._root not in path.parents:
            raise ValueError("storage key escapes storage root")
        return path

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(data)
        os.chmod(path, 0o600)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        try:
            path.unlink()
        except FileNotFoundError:
            return
