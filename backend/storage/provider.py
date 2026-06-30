"""Storage provider factory."""

from pathlib import Path
from storage.repository import BaseRepository


def create_storage_repository(db_path: Path) -> BaseRepository:
    """Create storage repository instance."""
    repo = BaseRepository(db_path)
    repo.connect()
    return repo
