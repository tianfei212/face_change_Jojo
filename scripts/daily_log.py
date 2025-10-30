#!/usr/bin/env python3
import argparse
import datetime as dt
import os
import subprocess
import sys


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, capture_output=False)


def file_read(path: str) -> str:
    if not os.path.exists(path):
        return "# 操作记录（Operations Log）\n\n"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def file_write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def ensure_section(content: str, date_str: str) -> str:
    header = f"## {date_str}"
    if header not in content:
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"\n{header}\n"
    return content


def main():
    parser = argparse.ArgumentParser(description="Append daily operation log and create daily git tag.")
    parser.add_argument("--message", required=True, help="Operation message to append")
    parser.add_argument("--date", help="Date in YYYY-MM-DD, default: today")
    parser.add_argument("--no-commit", action="store_true", help="Do not create a git commit")
    parser.add_argument("--no-tag", action="store_true", help="Do not create a git tag")
    parser.add_argument("--no-push", action="store_true", help="Do not push commit/tag to remote")
    args = parser.parse_args()

    date_str = args.date or dt.date.today().isoformat()
    time_str = dt.datetime.now().strftime("%H:%M:%S")
    tag_name = f"daily-{date_str}"

    # Update OPERATIONS_LOG.md
    path = os.path.join(os.getcwd(), "OPERATIONS_LOG.md")
    content = file_read(path)
    content = ensure_section(content, date_str)
    content += f"- [{time_str}] {args.message}\n"
    file_write(path, content)

    # Git add and commit
    run(["git", "add", "OPERATIONS_LOG.md"])
    if not args.no_commit:
        run(["git", "commit", "-m", f"chore(log): {date_str} {args.message}"])

    # Tag operations
    if not args.no_tag:
        # Create tag if not exists
        res = subprocess.run(["git", "tag", "-l", tag_name], text=True, capture_output=True)
        if not res.stdout.strip():
            run(["git", "tag", "-a", tag_name, "-m", f"Daily tag {date_str}"])
        if not args.no_push:
            run(["git", "push", "origin", tag_name])

    # Push commit
    if not args.no_push and not args.no_commit:
        run(["git", "push"]) 


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e}", file=sys.stderr)
        sys.exit(e.returncode)