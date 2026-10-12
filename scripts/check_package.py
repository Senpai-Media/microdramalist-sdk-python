"""The PyPI distributions' contents, checked before every publish (task
package:check): exactly the SDK, its docs, README, CHANGELOG, LICENSE and
packaging metadata -- nothing else -- and no file in them carrying a
credential-shaped string or an encrypted-secrets marker. Exit 1 lists what
is wrong.

    uv build --out-dir dist && python scripts/check_package.py dist
"""

import re
import sys
import tarfile
import zipfile
from pathlib import Path

MODULES = r"(__init__|_client|_errors|_version|types)\.py|py\.typed"
SDIST_ALLOWED = [
    re.compile(rf"^microdramalist-[^/]+/{p}$")
    for p in [
        rf"src/microdramalist/({MODULES})",
        r"docs/[a-z0-9-]+\.md",
        r"README\.md",
        r"CHANGELOG\.md",
        r"LICENSE",
        r"pyproject\.toml",
        r"PKG-INFO",
    ]
]
WHEEL_ALLOWED = [
    re.compile(rf"^microdramalist/({MODULES})$"),
    re.compile(r"^microdramalist-[^/]+\.dist-info/(METADATA|WHEEL|RECORD|licenses/LICENSE)$"),
]
# Never ship: tokens (ours mdl_, GitHub ghp_/github_pat_, npm npm_, PyPI
# pypi-), private keys, sops/age encrypted files.
FORBIDDEN = [
    re.compile(p)
    for p in [
        r"mdl_[A-Za-z0-9_-]{20,}",
        r"gh[pousr]_[A-Za-z0-9]{30,}",
        r"github_pat_[A-Za-z0-9_]{30,}",
        r"npm_[A-Za-z0-9]{30,}",
        r"pypi-[A-Za-z0-9_-]{30,}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
        r"ENC\[AES256_GCM",
        r"age1[a-z0-9]{50,}",
        r"\bsops:",
    ]
]


def check(name: str, data: bytes, allowed: list, problems: list) -> None:
    if not any(a.match(name) for a in allowed):
        problems.append(f"not allowed: {name}")
    text = data.decode("utf-8", "replace")
    problems.extend(f"{name} matches {f.pattern}" for f in FORBIDDEN if f.search(text))


def main(dist: Path) -> int:
    problems: list = []
    sdists, wheels = sorted(dist.glob("*.tar.gz")), sorted(dist.glob("*.whl"))
    if len(sdists) != 1 or len(wheels) != 1:
        print(f"want one sdist and one wheel in {dist}, have {len(sdists)} and {len(wheels)}")
        return 1
    with tarfile.open(sdists[0]) as tar:
        for m in tar.getmembers():
            if m.isfile():
                check(m.name, tar.extractfile(m).read(), SDIST_ALLOWED, problems)  # type: ignore[union-attr]
    with zipfile.ZipFile(wheels[0]) as whl:
        for n in whl.namelist():
            check(n, whl.read(n), WHEEL_ALLOWED, problems)
    if problems:
        print("\n".join(problems))
        return 1
    print(f"packages ok: {sdists[0].name}, {wheels[0].name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1] if len(sys.argv) > 1 else "dist")))
