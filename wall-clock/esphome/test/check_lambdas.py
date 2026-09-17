#!/usr/bin/env python3
"""Static check over every lambda in the mini clock's firmware.

WHY THIS EXISTS. The clocks run ESPHome 2026.8.1 and the newest release
installable in this sandbox is 2026.6.5, in which `online_image` was still a
top-level component rather than an `image:` platform. So `esphome config` on
this file fails here on a syntax that is correct on the bench, and `esphome
compile` is further out of reach still. That leaves roughly a hundred lines of
hand-written C++ that nobody can build until Sam flashes it.

This will not type-check anything. It catches the two mistakes that actually
happen when you edit a lambda you cannot compile:

  1. an `id(...)` naming something that is not declared anywhere in the file --
     a typo, or a rename that missed a use;
  2. braces, parens or brackets that do not balance.

Run it before pushing firmware. It is not a substitute for the bench; it is
the difference between finding a typo here and finding it in a flash.
"""
import os, re, sys, yaml

# Resolve from this file, not the shell's cwd -- the point of this checker is
# that it still runs in a month, from wherever it is invoked.
FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    os.pardir, 'mini-round-clock-with-display.yaml')


class L(yaml.SafeLoader):
    pass


for tag in ('!secret', '!lambda', '!include', '!extend', '!remove'):
    L.add_constructor(tag, lambda ldr, node, t=tag:
                      ldr.construct_scalar(node) if isinstance(node, yaml.ScalarNode) else None)

doc = yaml.load(open(FILE), Loader=L)

ids, lambdas = set(), []


def walk(node, path='', in_lambda_key=False):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'id' and isinstance(v, str):
                ids.add(v)
            if k in ('lambda', 'value') and isinstance(v, str) and 'id(' in v:
                lambdas.append((path + '/' + str(k), v))
            walk(v, path + '/' + str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f'{path}[{i}]')
    elif isinstance(node, str) and 'id(' in node and '\n' in node:
        lambdas.append((path, node))


walk(doc)
# ESPHome makes an id for every named entity too, but `id(...)` can only reach
# ones that were declared with `id:` -- which is exactly the set above.
subs = doc.get('substitutions', {}) or {}

strip_line = re.compile(r'//.*')
strip_blk = re.compile(r'/\*.*?\*/', re.S)
id_use = re.compile(r'\bid\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)')

bad_ids, bad_bal = [], []
for path, body in lambdas:
    for k, v in subs.items():
        body = body.replace('${%s}' % k, str(v))
    code = strip_line.sub('', strip_blk.sub('', body))
    for name in set(id_use.findall(code)):
        if name not in ids:
            bad_ids.append((path, name))
    for open_c, close_c in (('{', '}'), ('(', ')'), ('[', ']')):
        d = code.count(open_c) - code.count(close_c)
        if d:
            bad_bal.append((path, open_c, d))

# ---- globals: every one needs a type -------------------------------------
# NOT about lambdas, but it belongs to the same job: things `esphome config`
# would catch in a second and nothing here can. Added because I inserted a new
# global directly after `- id: grow_daytime` and above its `type:`, which
# silently handed grow_daytime's type to the new entry and left the old one
# with none. Every lambda still balanced and every id still resolved, so this
# file said the firmware was fine. A checker only sees what it looks at.
REQUIRED = ('type', 'restore_value')
bad_glob = []
for g in (doc.get('globals') or []):
    if not isinstance(g, dict):
        bad_glob.append((str(g), 'not a mapping'))
        continue
    gid = g.get('id', '<no id>')
    for key in REQUIRED:
        if key not in g:
            bad_glob.append((gid, f'no {key}:'))

print(f'{len(lambdas)} lambdas, {len(ids)} declared ids, '
      f'{len(doc.get("globals") or [])} globals')
ok = True
if bad_glob:
    ok = False
    print(f'\n{len(bad_glob)} MALFORMED globals:')
    for gid, why in bad_glob:
        print(f'   {gid}   {why}')
else:
    print('  [ok  ] every global declares a type and a restore_value')
if bad_ids:
    ok = False
    print(f'\n{len(bad_ids)} UNDECLARED id() references:')
    for path, name in sorted(set(bad_ids)):
        print(f'   id({name})   in {path}')
else:
    print('  [ok  ] every id(...) names something the file declares')
if bad_bal:
    ok = False
    print(f'\n{len(bad_bal)} UNBALANCED lambdas:')
    for path, c, d in bad_bal:
        print(f'   {c} off by {d:+d}   in {path}')
else:
    print('  [ok  ] braces, parens and brackets balance in every lambda')
sys.exit(0 if ok else 1)
