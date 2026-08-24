from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    raw_dir: Path = Path("data/raw")
    processed_dir: Path = Path("data/processed")
    cache_dir: Path = Path("data/cache")
    horizons: tuple[int, ...] = (5, 10, 20, 60)
    min_history: int = 252
    default_symbols: tuple[str, ...] = ("MSR",)
    risk_free_rate: float = 0.0


SETTINGS = Settings()

for directory in (SETTINGS.raw_dir, SETTINGS.processed_dir, SETTINGS.cache_dir):
    directory.mkdir(parents=True, exist_ok=True)
