#!/bin/bash
#
# Install development prerequisites for source distributions of Drake on macOS.
#
# The development and runtime prerequisites for binary distributions should be
# installed before running this script.

set -euxo pipefail

if [[ "${EUID}" -eq 0 ]]; then
  echo 'This script must NOT be run as root' >&2
  exit 1
fi

brew update
brew bundle --file="${BASH_SOURCE%/*}/Brewfile"

/usr/local/opt/python@2/bin/pip2 install --upgrade --requirement "${BASH_SOURCE%/*}/requirements.txt"
