"""Example: explore options catalog (requires VT.AspNetApp running)."""

from datetime import date

from visiontrader import OptionsClient


def main() -> None:
    with OptionsClient() as client:
        print("exchanges:", client.list_exchanges(type="options"))
        print("instruments:", client.list_instruments("deribit"))
        expiries = client.list_expiries("deribit", "BTC")
        if not expiries:
            return
        expiry = expiries[0].expiry
        print("dates:", client.list_dates("deribit", "BTC", expiry))
        dates = client.list_dates("deribit", "BTC", expiry)
        if dates:
            snaps = client.get_snapshots(
                "deribit",
                "BTC",
                expiry=expiry,
                on_date=dates[-1],
            )
            print(f"snapshots on {dates[-1]}:", len(snaps))


if __name__ == "__main__":
    main()
