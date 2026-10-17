"""Check public Markdown, local links and heading anchors without network access."""
import argparse
from collections import Counter
import os
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


def prose(source):
    """Exclude fenced examples while preserving line numbers for diagnostics."""
    lines, fence = [], None
    for line in source.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if fence is None and marker:
            fence = marker[1]
            lines.append("")
        elif fence and re.fullmatch(r"\s{0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*", line):
            fence = None
            lines.append("")
        else:
            lines.append("" if fence else line)
    return "\n".join(lines), fence is not None


def heading_ids(source):
    used, anchors = Counter(), set()
    for title in re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", source, re.MULTILINE):
        slug = re.sub(r"[^\w\-\s]", "", title.lower()).replace(" ", "-")
        anchor = slug if not used[slug] else f"{slug}-{used[slug]}"
        used[slug] += 1
        anchors.add(anchor)
    return anchors


def check(root):
    root = root.resolve()
    files = sorted(set(root.glob("*.md")) | set((root / "docs").rglob("*.md"))
                   | set((root / ".github").rglob("*.md")))
    errors, sources, links = [], {}, 0
    for path in files:
        name = path.relative_to(root).as_posix()
        try:
            raw = path.read_bytes()
            source = raw.decode("utf-8")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{name}: cannot read UTF-8: {exc}")
            continue
        if "\ufffd" in source or "\x00" in source or source.startswith("\ufeff"):
            errors.append(f"{name}: invalid text or UTF-8 BOM")
        if not raw.endswith(b"\n"):
            errors.append(f"{name}: missing final newline")
        body, unclosed = prose(source)
        sources[path] = body
        if unclosed:
            errors.append(f"{name}: unclosed fenced code block")
        if ".github" not in path.relative_to(root).parts and len(re.findall(r"^# ", body, re.MULTILINE)) != 1:
            errors.append(f"{name}: expected one document title")

    inline_link = re.compile(r'!?\[[^\]\n]*\]\(\s*(<[^>]+>|[^\s)]+)(?:\s+"[^"\n]*")?\s*\)')
    reference = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]+>|\S+)", re.MULTILINE)
    for path, body in sources.items():
        name = path.relative_to(root).as_posix()
        body = re.sub(r"(`+)[^`\n]*\1", "", body)
        for match in list(inline_link.finditer(body)) + list(reference.finditer(body)):
            destination = match[1].strip("<>")
            line = body[:match.start()].count("\n") + 1
            parsed = urlsplit(destination)
            if parsed.scheme in {"https", "http", "mailto"}:
                continue
            if parsed.scheme or parsed.netloc:
                errors.append(f"{name}:{line}: unsupported link {destination}")
                continue
            links += 1
            requested = Path(os.path.abspath(path.parent / unquote(parsed.path))) if parsed.path else path
            target = requested.resolve()
            if not target.is_relative_to(root) or not target.exists():
                errors.append(f"{name}:{line}: missing or external local path {destination}")
                continue
            current = root
            for part in requested.relative_to(root).parts:
                if part not in {item.name for item in current.iterdir()}:
                    errors.append(f"{name}:{line}: path case mismatch {destination}")
                    break
                current /= part
            if parsed.fragment and target.suffix.lower() == ".md":
                target_source = sources.get(target)
                if target_source is None:
                    target_source = prose(target.read_text(encoding="utf-8"))[0]
                if unquote(parsed.fragment) not in heading_ids(target_source):
                    errors.append(f"{name}:{line}: missing heading {destination}")
    return files, links, errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    files, links, errors = check(args.root)
    if not files:
        errors.append("No public Markdown files found")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Checked {len(files)} Markdown files and {links} local links. External URLs were not fetched.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
