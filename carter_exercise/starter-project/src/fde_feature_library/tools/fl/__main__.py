"""Allow the toolchain to be run as ``python3 -m fl``."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
