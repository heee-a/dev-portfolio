"""SHA 级对齐：用本地提交的精确字节经 API 重建远端提交对象。

原理：git 的 blob/tree/commit SHA 全部由内容决定。用 `git cat-file` 取出
本地提交的真实字节（LF、真实模式、真实作者时间戳），经 API 创建相同的
blob/tree/commit，得到的远端 SHA 与本地完全一致——无 github.com 也能对齐。

用法: TOKEN=xxx python sha_align.py <owner/name>
"""

import base64
import http.client
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

REPO = sys.argv[1]
TOKEN = os.environ["TOKEN"]
API = f"https://api.github.com/repos/{REPO}"


def api(method: str, path: str, payload: dict | None = None,
        retries: int = 4) -> dict:
    """带网络重试的 API 调用；GitHub 错误码包装在 __http_error__ 里返回。"""
    err: Exception | None = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(
            f"{API}{path}",
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={"Authorization": f"token {TOKEN}",
                     "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json; charset=utf-8",
                     "User-Agent": "sha-align"},
            method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            return {"__http_error__": e.code, "body": body}
        except (urllib.error.URLError, ConnectionError, OSError,
                http.client.IncompleteRead) as e:
            err = e
            print(f"    网络错误（第 {attempt} 次），退避 {2 ** attempt}s: {e}")
            time.sleep(2 ** attempt)
    raise RuntimeError(f"网络重试 {retries} 次后仍失败: {path}") from err


def git(*args) -> str:
    return subprocess.check_output(
        ["git", "-c", "core.quotepath=false", *args], text=True, encoding="utf-8")


def parse_date(raw: str) -> str:
    """git 时间戳 '1789272767 +0800' -> 保留原始时区的 ISO8601。"""
    ts, tz = raw.split()
    hours, minutes = int(tz[1:3]), int(tz[3:5])
    tzobj = timezone(timedelta(hours=hours, minutes=minutes) *
                     (1 if tz[0] == "+" else -1))
    dt = datetime.fromtimestamp(int(ts), tz=tzobj)
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + tz[0] + f"{hours:02d}:{minutes:02d}"


def parse_person(line: str) -> dict:
    rest = line.split(" ", 1)[1]              # 'heee-a <email> 1789272767 +0800'
    name_email, ts, tz = rest.rsplit(" ", 2)
    name, email = name_email.rsplit(" <", 1)
    return {"name": name, "email": email.removesuffix(">"),
            "date": parse_date(f"{ts} {tz}")}


def main() -> None:
    commits = git("rev-list", "--reverse", "HEAD").splitlines()
    print(f"本地提交链 {len(commits)} 个: {' -> '.join(c[:7] for c in commits)}")

    uploaded: set[str] = set()
    parent: str | None = None
    for cid in commits:
        obj = git("cat-file", "commit", cid)
        lines = obj.split("\n")
        tree_sha = lines[0].split()[1]
        author_line = next(l for l in lines if l.startswith("author "))
        committer_line = next(l for l in lines if l.startswith("committer "))
        message = obj.split("\n\n", 1)[1]

        entries = []
        for line in git("ls-tree", "-r", cid).splitlines():
            meta, path = line.split("\t")
            mode, _otype, sha = meta.split()
            if sha not in uploaded:
                created = api("POST", "/git/blobs",
                              {"content": base64.b64encode(
                                  subprocess.check_output(
                                      ["git", "cat-file", "blob", sha])).decode(),
                               "encoding": "base64"})
                if "__http_error__" in created:
                    print(f"    blob {path} 上传失败: {created}")
                    sys.exit(1)
                assert created["sha"] == sha, f"blob SHA 不一致: {path}"
                uploaded.add(sha)
            entries.append({"path": path, "mode": mode, "type": "blob", "sha": sha})

        tree = api("POST", "/git/trees", {"tree": entries})
        assert tree["sha"] == tree_sha, f"tree SHA 不一致 @ {cid[:7]}"

        new_commit = api("POST", "/git/commits", {
            "message": message, "tree": tree["sha"],
            "parents": [parent] if parent else [],
            "author": parse_person(author_line),
            "committer": parse_person(committer_line)})
        assert new_commit["sha"] == cid, (
            f"commit SHA 不一致 @ {cid[:7]}: 得到 {new_commit['sha'][:7]}")
        print(f"  重建 {cid[:7]} ✓")
        parent = cid

    api("PATCH", "/git/refs/heads/main",
        {"sha": parent, "force": True})
    print(f"远端 main 已指向 {parent[:7]}，SHA 级对齐完成")


if __name__ == "__main__":
    main()
