"""Example: explore options catalog (requires VT.AspNetApp running)."""

from datetime import date

from visiontrader import VisionOptionsClient


def main() -> None:
    with VisionOptionsClient() as vision_options:
        print('exchanges:', vision_options.list_exchanges())
        print('instruments:', vision_options.list_instruments('deribit'))
        expiries = vision_options.list_expiries('deribit', 'BTC')
        if not expiries:
            return
        expiry = expiries[0].expiry
        print('dates:', vision_options.list_dates('deribit', 'BTC', expiry))
        dates = vision_options.list_dates('deribit', 'BTC', expiry)
        if dates:
            snaps = vision_options.get_snapshots(
                'deribit',
                'BTC',
                expiry=expiry,
                on_date=dates[-1],
            )
            print(f'snapshots on {dates[-1]}:', len(snaps))


if __name__ == '__main__':
    main()
