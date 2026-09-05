#!/bin/sh
# All seven verification passes. Non-zero exit if any of them finds anything.
set -e
cd "$(dirname "$0")"
for c in check1_topology.py check2_fit.py check3_print.py check4_v3.py check5_stand.py check6_standbox.py; do
    printf '%-22s ' "$c"
    if python3 "$c" > /tmp/wc-check.txt 2>&1; then
        tail -1 /tmp/wc-check.txt
    else
        echo '*** FAILED ***'; cat /tmp/wc-check.txt; exit 1
    fi
done
# check 7 runs once per body: the back-stand's footprint scales with the clock
# and the 60 is a different part in every dimension that matters.
for t in '' -32 -60; do
    printf '%-22s ' "check7_backstand.py ${t:-24}"
    if python3 check7_backstand.py "$t" > /tmp/wc-check.txt 2>&1; then
        tail -1 /tmp/wc-check.txt
    else
        echo '*** FAILED ***'; cat /tmp/wc-check.txt; exit 1
    fi
done
