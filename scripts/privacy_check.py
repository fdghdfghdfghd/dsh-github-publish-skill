"""Scan a folder for personal data and secrets before publishing it.

Usage:
    python privacy_check.py <folder> [--json] [--max-mb 5]

Exit code 1 when any HIGH finding exists.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TEXT_EXT = {
    ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".js", ".ts", ".tsx", ".jsx", ".c", ".h", ".cpp", ".java", ".sh", ".ps1",
    ".bat", ".cmd", ".html", ".css", ".csv", ".ipynb", ".gitignore", ".env",
}
MEDIA_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".mp4", ".mov"}
DOC_EXT = {".docx", ".doc", ".pdf", ".xlsx", ".xls", ".pptx", ".key", ".pem", ".p12"}

PATTERNS = [
    ("HIGH", "private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("HIGH", "github token", re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}")),
    ("HIGH", "cloud/api key", re.compile(r"\bsk-[A-Za-z0-9]{20,}|\bAKIA[0-9A-Z]{16}\b")),
    ("HIGH", "absolute user path", re.compile(r"[A-Za-z]:\\\\?Users\\\\?[^\\/\s\"']+|/root/|/home/[a-z0-9_-]+/")),
    ("HIGH", "cn id number", re.compile(r"(?<!\d)[1-9]\d{5}(19|20)\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{3}[\dXx](?!\d)")),
    ("MED", "email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("MED", "cn mobile", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("MED", "ip address", re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")),
    ("MED", "container/host id", re.compile(r"autodl[-_a-z0-9]*|container-[a-z0-9]{6,}", re.I)),
    ("LOW", "student-id-like number", re.compile(r"(?<!\d)\d{10}(?!\d)")),
]

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"}


# Benign addresses that show up in nearly every project's docs and scripts.
IGNORE_EMAILS = {"git@github.com", "noreply@github.com", "you@example.com"}


def scan_text(text):
    hits = []
    for level, label, pat in PATTERNS:
        found = pat.findall(text)
        if label == "email":
            found = [
                m for m in found
                if str(m).lower() not in IGNORE_EMAILS
                and not str(m).lower().endswith(("@users.noreply.github.com", "@example.com"))
            ]
        if found:
            sample = sorted({m if isinstance(m, str) else str(m) for m in found})[:3]
            hits.append((level, label, len(found), sample))
    return hits


def git_author(root):
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "log", "-1", "--format=%an <%ae>"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-mb", type=float, default=5.0)
    args = ap.parse_args()

    root = Path(args.folder).resolve()
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    limit = int(args.max_mb * 1024 * 1024)
    findings = []
    media, docs, secrets = [], [], []

    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        # don't flag the scanner's own pattern list
        if path.resolve() == Path(__file__).resolve():
            continue

        name = path.name.lower()
        if name.startswith(".env") or name in {"id_rsa", "id_ed25519", "credentials", ".npmrc"}:
            secrets.append(str(rel))

        if path.suffix.lower() in MEDIA_EXT:
            media.append(str(rel))
        if path.suffix.lower() in DOC_EXT:
            docs.append(str(rel))

        if path.suffix.lower() not in TEXT_EXT:
            continue
        if path.stat().st_size > limit:
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for level, label, count, sample in scan_text(text):
            findings.append({
                "file": str(rel), "level": level, "kind": label,
                "count": count, "sample": sample,
            })

    author = git_author(root) if (root / ".git").exists() else None

    if args.json:
        print(json.dumps({
            "root": str(root),
            "findings": findings,
            "media": media,
            "documents": docs,
            "secret_files": secrets,
            "git_author": author,
        }, ensure_ascii=False, indent=2))
    else:
        print(f"root: {root}")
        print(f"files scanned: {sum(1 for p in root.rglob('*') if p.is_file() and not any(x in SKIP_DIRS for x in p.relative_to(root).parts))}")
        print()

        if findings:
            print("== text findings ==")
            for f in findings:
                print(f"  [{f['level']}] {f['file']}")
                print(f"         {f['kind']} x{f['count']}  e.g. {f['sample']}")
        else:
            print("== text findings ==\n  clean")

        if secrets:
            print("\n== secret-looking files ==")
            for s in secrets:
                print(f"  [HIGH] {s}")

        if media:
            print("\n== images/videos (inspect by eye, they may contain screenshots) ==")
            for m in media:
                print(f"  [CHECK] {m}")

        if docs:
            print("\n== office/pdf files (metadata often carries author names) ==")
            for d in docs:
                print(f"  [CHECK] {d}")

        if author:
            print("\n== git commit author ==")
            print(f"  {author}")
            print("  (public on GitHub; use a noreply address)")

        high = [f for f in findings if f["level"] == "HIGH"] or secrets
        print()
        print("RESULT:", "BLOCK — fix HIGH items first" if high else "OK (review MED/CHECK items)")

    high = any(f["level"] == "HIGH" for f in findings) or bool(secrets)
    return 1 if high else 0


if __name__ == "__main__":
    sys.exit(main())
