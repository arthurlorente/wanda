#!/bin/sh
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
sh scripts/wanda.sh
result=$?
if [ "$result" -ne 0 ]; then
  printf '\nPress Return to close this window.'
  read -r answer
fi
exit "$result"
