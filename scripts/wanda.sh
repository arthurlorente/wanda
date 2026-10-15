#!/bin/sh
# No downloads, dependencies, shell evaluation of configuration, or elevated rights.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if command -v python3 >/dev/null 2>&1; then
  exec python3 -m wanda "$@"
fi
if command -v python >/dev/null 2>&1; then
  exec python -m wanda "$@"
fi
echo "Python 3.11 or newer is needed. Install Python from python.org, then open Start Wanda again."
exit 1
