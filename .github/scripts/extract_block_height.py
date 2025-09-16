#!/usr/bin/env python3
"""Extract the highest Bitcoin block height from an OpenTimestamps proof."""
from __future__ import annotations

import sys
from pathlib import Path

try:
    from opentimestamps.core.serialize import StreamDeserializationContext
    from opentimestamps.core.timestamp import DetachedTimestampFile
    from opentimestamps.core.notary import BitcoinBlockHeaderAttestation
except Exception:
    sys.exit(0)


def main(path_arg: str) -> None:
    path = Path(path_arg)
    if not path.is_file():
        return

    try:
        with path.open('rb') as fh:
            ctx = StreamDeserializationContext(fh)
            timestamp = DetachedTimestampFile.deserialize(ctx).timestamp
    except Exception:
        return

    heights = sorted(
        {
            att.height
            for _, att in timestamp.all_attestations()
            if isinstance(att, BitcoinBlockHeaderAttestation)
        }
    )
    if heights:
        print(heights[-1])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(0)
    main(sys.argv[1])
