# visiontrader-python

Official Python client for the [VisionTrader](https://github.com/visiontrader) market data API (options boards, Deribit-first).

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

```python
# We export the components required for the operation of the options module:
from datetime import date, datetime, timezone
import pandas as pd
# We are exporting the VisionTrader options module:
from visiontrader import VisionOptionsClient
vision_options = VisionOptionsClient()  # VisionOptionsClient(base_url="https://api.example.com")
```
In [2]:

```python
# Get a list of exchanges trading options
vision_options.list_exchanges()
```

Out[2]:

```python
['deribit']
```

In [3]:

```python
# Retrieve the list of instruments with tradable options for the selected exchange.
vision_options.list_instruments("deribit")
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

```python
# Get a list of expiration dates and option types for the selected instrument and exchange.
# Display the list as a pandas DataFrame.
expiries = vision_options.list_expiries("deribit", "BTC")
df = pd.DataFrame([{"expiry": e.expiry, "settlement_period": e.settlement_period} for e in expiries])
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

Use `df` for the full table; `tail(22)` shows the last rows when the list is long.

In [5]:

```python
# Display the dates on which data was recorded for the selected option.
vision_options.list_dates("deribit", "BTC_USDC", date(2026, 5, 1))
```

Out[5]:

```python
[
    datetime.date(2026, 4, 20),
    datetime.date(2026, 4, 21),
    datetime.date(2026, 4, 22),
]
```

In [6]:

```python
snap = vision_options.get_snapshot(
    "deribit",
    "BTC_USDC",
    expiry=date(2026, 5, 1),
    ts=datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc),
)
snap
```

Out[6]:

```python
OptionsSnapshot(
    exchange='deribit',
    underlying='BTC_USDC',
    expiry=datetime.date(2026, 5, 1),
    ts=datetime.datetime(2026, 4, 25, 12, 0, tzinfo=datetime.timezone.utc),
    underlying_price=77704.28,
    options=(
        OptionLeg(
            symbol='BTC-1MAY26-70000-C',
            strike=70000.0,
            type='call',
            bid=0.072,
            ask=0.1245,
            mark_price=0.0997,
            mark_iv=0.4816,
            oi=1561.2,
        ),
        # ... more strikes ...
    ),
    error=None,
)
```

In [7]:

```python
snap.options[0].mark_iv
```

Out[7]:

```python
0.4816
```

Implied volatility is in decimal form (0.48 = 48%), not percent.

In [8]:

```python
vision_options.get_snapshots(
    "deribit",
    "BTC_USDC",
    expiry=date(2026, 5, 1),
    on_date=date(2026, 4, 25),
)
```

Out[8]:

```python
[
    OptionsSnapshot(..., ts=datetime.datetime(2026, 4, 25, 0, 0, tzinfo=...), options=(...)),
    OptionsSnapshot(..., ts=datetime.datetime(2026, 4, 25, 0, 1, tzinfo=...), options=(...)),
    # one snapshot per timestamp in the day (resolution default: 1m)
]
```

In [9]:

```python
df = vision_options.snapshots_to_dataframe(
    "deribit",
    "BTC_USDC",
    expiry=date(2026, 5, 1),
    on_date=date(2026, 4, 25),
)
df.head(3)
```

Out[9]:

```
   exchange  underlying      expiry                        ts  underlying_price  \
0   deribit    BTC_USDC  2026-05-01 2026-04-25 12:00:00+00:00          77704.28
1   deribit    BTC_USDC  2026-05-01 2026-04-25 12:00:00+00:00          77704.28
2   deribit    BTC_USDC  2026-05-01 2026-04-25 12:00:00+00:00          77704.28

              symbol    strike  type     bid     ask  mark_price  mark_iv      oi
0  BTC-1MAY26-70000-C   70000.0  call  0.0720  0.1245      0.0997   0.4816  1561.2
1  BTC-1MAY26-72000-C   72000.0  call  0.0580  0.1100      0.0850   0.4720  1420.0
2  BTC-1MAY26-74000-C   74000.0  call  0.0450  0.0980      0.0720   0.4650  1388.5
```

Long format: one row per option leg per snapshot timestamp.

In [10]:

```python
import visiontrader as vt

vt.vision_options_client()
```

Out[10]:

```python
<visiontrader.options.VisionOptionsClient at 0x...>
```

## API coverage (v0.1)

| Method | HTTP |
|--------|------|
| `list_exchanges()` | `GET /exchanges?type=options` |
| `list_instruments(exchange)` | `GET options/instruments` |
| `list_expiries(exchange, symbol)` | `GET options/expiries` |
| `list_dates(exchange, symbol, expiry)` | `GET options/dates` |
| `get_snapshot(...)` | `GET /options/snapshot` |
| `get_snapshots(..., on_date=...)` | `GET /options/snapshots` |
| `snapshots_to_dataframe(...)` | `GET /options/snapshots` → DataFrame |

Query parameter for the board symbol is **`symbol`** (not `instrument`).

## Backend

Requires a running [VT.AspNetApp](https://github.com/visiontrader) REST API and its gRPC data layer.

## License

MIT — see [LICENSE](LICENSE).
