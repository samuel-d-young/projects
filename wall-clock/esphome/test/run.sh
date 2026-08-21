#!/usr/bin/env bash
# Compile-check and smoke-test the render lambda WITHOUT the ESPHome toolchain.
#
# Why this exists: `esphome config` validates YAML but never compiles the
# lambda, and a full `esphome compile` needs the whole toolchain. This extracts
# the lambda, stubs the ESPHome types it touches (copied from
# esphome/core/color.h and components/light/esp_color_view.h @ 2026.8.0) and
# builds it with g++ -Wall -Wextra. It catches type errors, and asserts the
# hand positions land on the right pixel at 12/24/60 LEDs.
#
# It does NOT verify the YAML schema — run `esphome config wall-clock.yaml`
# for that. The two checks are complementary; run both.
set -euo pipefail
cd "$(dirname "$0")"
python3 - <<'PY'
import yaml
class L(yaml.SafeLoader): pass
L.add_constructor('!secret', lambda l, n: 'redacted')
d = yaml.load(open('../wall-clock.yaml'), Loader=L)
lam = d['light'][0]['effects'][0]['addressable_lambda']['lambda']
for k, v in d['substitutions'].items():
    lam = lam.replace('${%s}' % k, str(v))
open('lambda_body.cpp', 'w').write(lam)
print('extracted lambda: %d lines' % len(lam.splitlines()))
PY
g++ -std=c++17 -Wall -Wextra -Wno-unused-parameter -O1 -o harness harness.cpp
./harness
