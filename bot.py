#!/usr/bin/env python3
"""
Start the notifier. The real code lives in the notifier package.
"""

import sys

from notifier.run import main

if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
