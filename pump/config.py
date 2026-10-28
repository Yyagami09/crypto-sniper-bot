import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Rules:
    min_liquidity: float = 25000
    min_market_cap: float = 100000
    max_market_cap: float = 10000000
    min_age_minutes: float = 15
    max_age_minutes: float = 10080
    min_holders: int = 150
    max_top10: float = 0.30
    max_rug: float = 0.30
    max_bundler: float = 0.20
    max_insider: float = 0.20
    min_volume_5m: float = 10000
    min_buy_sell_ratio: float = 1.20
    min_change_5m: float = 2
    max_change_5m: float = 40
    liquidity_drop: float = 0.20
    cooldown_seconds: int = 1800
    confirmation_min_seconds: int = 30
    confirmation_max_seconds: int = 600
    interval_seconds: int = 60
    batch_size: int = 12
    max_tracked: int = 60
    retention_hours: int = 24

    def __post_init__(self):
        for key, value in asdict(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"Parâmetro inválido: {key}")
        for key in ('max_top10', 'max_rug', 'max_bundler', 'max_insider', 'liquidity_drop'):
            if not 0 < getattr(self, key) <= 1:
                raise ValueError(f"{key} deve ser uma razão de 0 a 1")
        for lo, hi in [('min_market_cap', 'max_market_cap'), ('min_age_minutes', 'max_age_minutes'),
                       ('min_change_5m', 'max_change_5m'), ('confirmation_min_seconds', 'confirmation_max_seconds')]:
            if getattr(self, lo) >= getattr(self, hi):
                raise ValueError(f"{lo} precisa ser menor que {hi}")
        if not 30 <= self.interval_seconds <= 3600 or not 2 <= self.batch_size <= 30 or not self.batch_size <= self.max_tracked <= 200:
            raise ValueError("Cadência deve ser 30–3600s; lote 2–30; capacidade entre lote e 200")
        for key in ('batch_size', 'max_tracked', 'interval_seconds', 'retention_hours', 'cooldown_seconds'):
            if not isinstance(getattr(self, key), int):
                raise ValueError(f"{key} deve ser inteiro")


def load_rules(path=None):
    path = Path(path or os.getenv('PUMP_CONFIG', ROOT / 'radar.json'))
    return Rules(**json.loads(path.read_text())) if path.exists() else Rules()


def settings(extra=None):
    # Only known settings are read; secrets never enter the saved radar state.
    names = ('SUPABASE_URL', 'SUPABASE_KEY', 'PUMP_SUPABASE_KEY', 'GMGN_API_KEY', 'GMGN_CLI',
             'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID', 'PUMP_LOCAL_DB')
    return {k: os.getenv(k) or (extra or {}).get(k, '') for k in names}
