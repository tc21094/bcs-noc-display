#!/usr/bin/env bash
# Rebuild theme/ from the sources
set -e
cd "$(dirname "$0")"
rm -rf theme
python3 build_theme.py "$1" "$2" theme
cat trace_data.script logic.script > theme/bcs-noc.script
cat > theme/bcs-noc.plymouth <<'P'
[Plymouth Theme]
Name=BCS NOC
Description=BCS NOC boot splash - logo with animated circuit traces
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/bcs-noc
ScriptFile=/usr/share/plymouth/themes/bcs-noc/bcs-noc.script
P
