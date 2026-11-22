#!/usr/bin/env python3
"""Historical synthetic corpus generation is disabled.

The existing 600-ad corpus is demo data, not verified merchant inventory.
It must not be regenerated with extrapolated condition prices or treated as
real listings. The prior generator remains available in repository history.
"""


def main(n=600):
    raise RuntimeError(
        'Synthetic inventory generation is disabled. Preserve the historical demo corpus. '
        'Production inventory needs real authorized listings, per-ad provenance, explicit '
        'units and conditions, and reviewed ingestion. No new ads or prices were written.'
    )


if __name__ == '__main__':
    main()
