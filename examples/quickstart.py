"""Example: explore options catalog (requires VT.AspNetApp running)."""

from datetime import date

from visiontrader import VisionOptionsClient


def main() -> None:
    with VisionOptionsClient() as vision_options:
        print('exchanges:', vision_options.list_exchanges())
        print('instruments:', vision_options.list_instruments('deribit'))
        expiries = vision_options.list_expiries('deribit', 'BTC')
        if expiries.empty:
            return
        expiry = expiries.iloc[0]['expiry']
        print('dates:', vision_options.list_dates('deribit', 'BTC', expiry))
        dates = vision_options.list_dates('deribit', 'BTC', expiry)
        if not dates.empty:
            on_date = dates['available dates'].iloc[-1]
            snaps = vision_options.get_snapshots(
                'deribit',
                'BTC',
                expiry=expiry,
                on_date=on_date,
            )
            print(f'snapshots on {on_date}:', len(snaps))


if __name__ == '__main__':
    main()
