import mypycheck as _chk; _chk.check(__file__)

import buildfile as _bf

from pathlib import Path as _Path

env = _bf.BuildEnv()
root = _Path('lua-safe/src/lua')
print(env.deps(root).value())
print(root)
for d in env.files[root].deps.value():
    print(f"\t{d}")
    for dd in env.deps(d).value():
        print(f"\t\t{dd}")
