# visiontrader-python

VisionTrader — Your navigator in the world of options and high-frequency data. Analyze historical Deribit options in near real-time. View historical IV, mark prices, and open interest—bridging the gap between the past and the present moment.

## Install

```bash
pip install visiontrader
```

Requires **pandas** (installed automatically):

```python
import pandas as pd
```

Development:

```bash
git clone https://github.com/visiontrader/visiontrader-python.git
cd visiontrader-python
pip install -e ".[dev]"
pytest
```

## Quickstart

Connect to your API (default: `http://localhost:5259`, or set `VT_API_BASE_URL`).

Example session (as in a Jupyter notebook; sample output from a live API):

In [1]:

Import dependencies and create the options client (`VisionOptionsClient` connects to the API; default is local, or pass `base_url` / set `VT_API_BASE_URL`).

```python
from datetime import date, datetime, timezone
import pandas as pd
from visiontrader import VisionOptionsClient
vision_options = VisionOptionsClient()  # VisionOptionsClient(base_url='https://api.example.com')
```

In [2]:

List exchanges that provide options data (the client requests only the options-capable subset).

```python
vision_options.list_exchanges()
```

Out[2]:

```python
['deribit']
```

In [3]:

List symbols with option boards on Deribit—not the exchange’s full instrument list, only names where historical options data is available.

```python
vision_options.list_instruments('deribit')
```

Out[3]:

```python
[
    'AVAX_USDC',
    'BTC',
    'BTC_USDC',
    'ETH',
    'ETH_USDC',
    'SOL',
    'SOL_USDC',
    'TRX_USDC',
    'XRP_USDC',
]
```

In [4]:

Fetch expiry dates and settlement period types for BTC, then display them as a table (`tail` shows the last rows when the list is long).

```python
expiries = vision_options.list_expiries('deribit', 'BTC')
df = pd.DataFrame([{'expiry': e.expiry, 'settlement_period': e.settlement_period} for e in expiries])
df.tail(22).reset_index(drop=True)
```

Out[4]:

```
       expiry settlement_period
0  2026-05-29             month
1  2026-05-30               day
2  2026-05-31               day
3  2026-06-01               day
4  2026-06-02               day
5  2026-06-03               day
6  2026-06-04               day
7  2026-06-05              week
8  2026-06-06               day
9  2026-06-07               day
10 2026-06-08               day
11 2026-06-09               day
12 2026-06-10               day
13 2026-06-11               day
14 2026-06-12              week
15 2026-06-19              week
16 2026-06-26             month
17 2026-07-31             month
18 2026-08-28             month
19 2026-09-25             month
20 2026-12-25             month
21 2027-03-26             month
```

In [5]:

Show calendar dates on which snapshot data exists for the selected expiry.

```python
dates = vision_options.list_dates('deribit', 'BTC', '2026-06-04')
pd.DataFrame({'available dates': dates})
```

Out[5]:

```
   available dates
0    2026-05-31
1    2026-06-01
2    2026-06-02
3    2026-06-03
4    2026-06-04
```

In [6]:

Load a single options board at a given timestamp. Returns a DataFrame with strikes, bid/ask, mark price, implied volatility, and open interest.

```python
snap = vision_options.get_snapshot('deribit', 'BTC', '2026-06-04', '2026-06-03T12:00')
snap.head(6)
```

Out[6]:

```
              symbol  strike  type     bid     ask  markPrice  markIv    oi
0  BTC-4JUN26-61000-C   61000  call  0.0845  0.0940     0.0889   87.81   NaN
1  BTC-4JUN26-61000-P   61000   put  0.0001  0.0003     0.0002   87.80  79.1
2  BTC-4JUN26-62000-C   62000  call  0.0700  0.0790     0.0741   83.35   0.2
3  BTC-4JUN26-62000-P   62000   put  0.0003  0.0005     0.0004   83.35  38.2
4  BTC-4JUN26-63000-C   63000  call  0.0555  0.0640     0.0595   76.52   NaN
5  BTC-4JUN26-63000-P   63000   put  0.0006  0.0008     0.0007   76.52  92.3
```

## API coverage (v0.1)

| Method | HTTP |
|--------|------|
| `list_exchanges()` | `GET /exchanges?type=options` |
| `list_instruments(exchange)` | `GET options/instruments` |
| `list_expiries(exchange, symbol)` | `GET options/expiries` |
| `list_dates(exchange, symbol, expiry)` | `GET options/dates` |
| `get_snapshot(...)` | `GET /options/snapshot` → DataFrame |
| `get_snapshots(..., on_date=...)` | `GET /options/snapshots` |
| `snapshots_to_dataframe(...)` | `GET /options/snapshots` → DataFrame |

Query parameter for the board symbol is **`symbol`** (not `instrument`).

## Backend

Requires a running [VT.AspNetApp](https://github.com/visiontrader) REST API and its gRPC data layer.

## License

MIT — see [LICENSE](LICENSE).
