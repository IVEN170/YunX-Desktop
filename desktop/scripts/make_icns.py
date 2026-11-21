"""由仓库根目录的 YunX-Desktop.ico 生成 macOS 用的 YunX-Desktop.icns。

jpackage 打 DMG 时只认 .icns（Windows 用 .ico）。ICNS 的 PNG 段格式很简单：
    'icns' + 总长度(大端 u32) + 若干段 [4 字节类型][长度(含 8 字节头)][PNG 数据]
所以不需要 macOS 的 iconutil，任何平台有 Pillow 都能生成。

用法（仓库根目录）：
    python desktop/scripts/make_icns.py
依赖：pillow
"""

from __future__ import annotations

import io
import struct
import sys
from pathlib import Path

from PIL import Image

# Windows 控制台默认 cp950/cp936，中文日志会抛 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover - 老 Python / 被重定向到不支持的对象
    pass

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "YunX-Desktop.ico"
OUT = ROOT / "YunX-Desktop.icns"

# (ICNS 类型, 像素边长)；同时给 1x/2x，避免 Retina 上取到缩放的模糊图
WANT = [
    ("icp4", 16), ("icp5", 32), ("icp6", 64),
    ("ic07", 128), ("ic08", 256), ("ic09", 512), ("ic10", 1024),
    ("ic11", 32), ("ic12", 64), ("ic13", 256), ("ic14", 512),
]


def main() -> int:
    if not SRC.is_file():
        raise SystemExit(f"找不到 {SRC}")
    ico = Image.open(SRC)
    sizes = sorted(ico.info.get("sizes", [(256, 256)]))
    biggest = sizes[-1][0]
    ico.size = (biggest, biggest)
    ico.load()
    base = ico.convert("RGBA")
    print(f"ico 帧：{sizes}，取 {biggest}x{biggest} 作基准")

    def png(size: int) -> bytes:
        buf = io.BytesIO()
        base.resize((size, size), Image.LANCZOS).save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    body = b""
    for typ, size in WANT:
        data = png(size)
        body += typ.encode("ascii") + struct.pack(">I", len(data) + 8) + data

    OUT.write_bytes(b"icns" + struct.pack(">I", len(body) + 8) + body)

    # 自检：头正确、每段都是 PNG、总长自洽
    raw = OUT.read_bytes()
    assert raw[:4] == b"icns", "icns 头错误"
    assert struct.unpack(">I", raw[4:8])[0] == len(raw), "总长度字段不对"
    off = 8
    while off < len(raw):
        typ = raw[off:off + 4].decode("ascii")
        length = struct.unpack(">I", raw[off + 4:off + 8])[0]
        assert raw[off + 8:off + 11] == b"\x89PN", f"{typ} 不是 PNG 数据"
        off += length
    assert off == len(raw), "分段长度与文件总长不符"

    print(f"已写 {OUT}（{OUT.stat().st_size} 字节，{len(WANT)} 段）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
