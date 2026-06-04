# visiontrader-python

Official Python client for the [VisionTrader](https://github.com/visiontrader) market data API (options boards, Deribit-first).

## Install

```bash
pip install visiontrader
```

With pandas helpers:

```bash
pip install visiontrader[pandas]
```

Development:

```bash
git clone https://github.com/visiontrader/visiontrader-python.git
cd visiontrader-python
pip install -e ".[dev]"
pytest
```

## Quickstart

Point at your API (default: `http://localhost:5259`, or set `VT_API_BASE_URL`):

```python
import pandas as pd
from visiontrader import OptionsClient

client = OptionsClient()  # or OptionsClient(base_url="https://api.example.com")

print(client.list_exchanges(type="options"))
print(client.list_instruments("deribit"))
print(client.list_expiries("deribit", "BTC_USDC"))

snap = client.get_snapshot(
    "deribit",
    "BTC",
    expiry=pd.Timestamp("2026-05-01").date(),
    ts=pd.Timestamp("2026-04-25T12:00:00Z").to_pydatetime(),
)
print(snap.underlying_price, len(snap.options))
```

Or with the short alias:

```python
import visiontrader as vt

client = vt.options_client()
```

Load a full day into a DataFrame:

```python
df = client.snapshots_to_dataframe(
    "deribit",
    "BTC",
    expiry=date(2026, 5, 1),
    on_date=date(2026, 4, 25),
)
```

## API coverage (v0.1)

| Method | HTTP |
|--------|------|
| `list_exchanges(type=...)` | `GET /exchanges` |
| `list_instruments(exchange)` | `GET options/instruments` |
| `list_expiries(exchange, symbol)` | `GET options/expiries` |
| `list_dates(exchange, symbol, expiry)` | `GET options/dates` |
| `get_snapshot(...)` | `GET /options/snapshot` |
| `get_snapshots(..., on_date=...)` | `GET /options/snapshots` |
| `snapshots_to_dataframe(...)` | same + pandas |

Query parameter for the board symbol is **`symbol`** (not `instrument`).

## Backend

Requires a running [VT.AspNetApp](https://github.com/visiontrader) REST API and its gRPC data layer.

## License

MIT — see [LICENSE](LICENSE).
