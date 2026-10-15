#!/bin/sh
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
sh scripts/wanda.sh --configure-voice
printf '\nPress Return to close this window.'
read -r answer
