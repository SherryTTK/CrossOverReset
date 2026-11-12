#!/usr/bin/env python3
"""CrossOver 26 trial reset. Preview by default; --apply writes with backups.

Reference: https://www.cnblogs.com/msbfb/p/20047167
This automates the article's steps; it does not establish vendor permission.
"""

import argparse
import datetime as dt
import os
from pathlib import Path
import plistlib
import re
import subprocess
import sys
import tempfile

DOMAIN = "com.codeweavers.CrossOver"
HOME = Path.home()
BOTTLES = HOME / "Library/Application Support/CrossOver/Bottles"
BACKUPS = HOME / "Library/Application Support/CrossOver Trial Backups"
SECTION = re.compile(rb"^\[([^\r\n]*)\][^\r\n]*(?:\r?\n|$)", re.MULTILINE)
TARGET = rb"software\codeweavers\crossover\cxoffice"


def reset_registry(data):
    """Remove only the exact cxoffice section, preserving every other byte."""
    headers = list(SECTION.finditer(data))
    spans = []
    for i, match in enumerate(headers):
        name = match.group(1).replace(b"\\\\", b"\\").lower()
        if name == TARGET:
            end = headers[i + 1].start() if i + 1 < len(headers) else len(data)
            spans.append((match.start(), end))
    for start, end in reversed(spans):
        data = data[:start] + data[end:]
    return data, len(spans)


def export_preferences():
    result = subprocess.run(
        ["/usr/bin/defaults", "export", DOMAIN, "-"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return result.stdout


def import_preferences(path):
    subprocess.run(["/usr/bin/defaults", "import", DOMAIN, str(path)],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def ensure_closed():
    result = subprocess.run(
        ["/bin/ps", "-U", str(os.getuid()), "-o", "pid=,comm="],
        check=True, stdout=subprocess.PIPE, text=True,
    )
    running = [line.strip() for line in result.stdout.splitlines()
               if "/crossover.app/contents/" in line.lower()]
    if running:
        raise RuntimeError("请先退出 CrossOver 和所有 Bottle 内程序，再重试：\n"
                           + "\n".join(running))


def atomic_write(path, data):
    mode = path.stat().st_mode & 0o777
    fd, temp = tempfile.mkstemp(prefix=".cx-reset-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def restore(backup):
    backup = backup.expanduser().resolve()
    prefs = backup / "preferences.plist"
    plistlib.loads(prefs.read_bytes())
    records = []
    for source in sorted((backup / "Bottles").glob("*/system.reg")):
        target = BOTTLES / source.parent.name / "system.reg"
        if not target.is_file() or target.is_symlink():
            raise RuntimeError(f"无法恢复：{target}")
        records.append((source, target))
    ensure_closed()
    for source, target in records:
        atomic_write(target, source.read_bytes())
    import_preferences(prefs)
    print(f"已恢复备份：{backup}")


def main():
    parser = argparse.ArgumentParser(description="CrossOver 试用记录重置；默认仅预览")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--apply", action="store_true", help="备份后执行修改")
    group.add_argument("--restore", type=Path, metavar="备份目录", help="恢复指定备份")
    args = parser.parse_args()
    if args.restore:
        restore(args.restore)
        return

    raw_preferences = export_preferences()
    preferences = plistlib.loads(raw_preferences)
    previous = preferences.get("FirstRunDate")
    if not isinstance(previous, dt.datetime):
        raise RuntimeError("未找到日期类型的 FirstRunDate；停止修改。")
    yesterday = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1))
    yesterday = yesterday.replace(tzinfo=None, microsecond=0)
    print(f"FirstRunDate（UTC）：{previous} → {yesterday}")
    changes = []
    if not BOTTLES.is_dir():
        raise RuntimeError(f"未找到 Bottle 目录：{BOTTLES}")
    for bottle in sorted(BOTTLES.iterdir()):
        registry = bottle / "system.reg"
        if not registry.is_file():
            continue
        if bottle.is_symlink() or registry.is_symlink():
            raise RuntimeError(f"检测到符号链接，请手动检查：{registry}")
        original = registry.read_bytes()
        updated, count = reset_registry(original)
        print(f"Bottle {bottle.name}：匹配到 {count} 个 cxoffice 段落")
        if count:
            changes.append((registry, original, updated))
    if not args.apply:
        print("仅预览，未修改数据。执行修改：")
        print(f'python3 "{Path(__file__).resolve()}" --apply')
        return

    ensure_closed()
    backup = BACKUPS / dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup.mkdir(parents=True, mode=0o700)
    prefs_backup = backup / "preferences.plist"
    prefs_backup.write_bytes(raw_preferences)
    for path, original, _ in changes:
        saved = backup / "Bottles" / path.parent.name / "system.reg"
        saved.parent.mkdir(parents=True)
        saved.write_bytes(original)
    preferences["FirstRunDate"] = yesterday
    updated_prefs = backup / "preferences-updated.plist"
    updated_prefs.write_bytes(plistlib.dumps(preferences))
    print(f"备份：{backup}")
    written = []
    preferences_attempted = False
    try:
        for path, original, updated in changes:
            if path.read_bytes() != original:
                raise RuntimeError(f"文件在预览后被其他程序修改：{path}")
            atomic_write(path, updated)
            written.append((path, original))
        preferences_attempted = True
        import_preferences(updated_prefs)
        actual = plistlib.loads(export_preferences()).get("FirstRunDate")
        if actual != yesterday:
            raise RuntimeError("FirstRunDate 写入验证失败")
    except BaseException:
        for path, original in reversed(written):
            atomic_write(path, original)
        if preferences_attempted:
            import_preferences(prefs_backup)
        raise
    print("已完成重置步骤。请启动 CrossOver 检查实际试用状态。")
    print("此方法不是永久授权；若再次到期，需要重新运行。")
    print(f'恢复命令：python3 "{Path(__file__).resolve()}" --restore "{backup}"')


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"失败：{exc}", file=sys.stderr)
        if isinstance(exc, subprocess.CalledProcessError) and exc.stderr:
            message = exc.stderr
            print(message.decode(errors="replace") if isinstance(message, bytes) else message,
                  file=sys.stderr)
        sys.exit(1)
