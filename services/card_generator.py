"""Generiert Lernkarten-Bilder pro Vokabel und Lehrer-Stil."""
from __future__ import annotations

import io
import textwrap
from pathlib import Path
from typing import Optional

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Font paths – DejaVu ist auf den meisten Linux-Systemen vorhanden
_FONT_DIRS = [
    Path("/usr/share/fonts/truetype/dejavu"),
    Path("/usr/local/lib/python3.12/site-packages/cv2/qt/fonts"),
    Path("/usr/local/lib/python3.11/site-packages/cv2/qt/fonts"),
]

def _find_font(name: str) -> Optional[Path]:
    for d in _FONT_DIRS:
        p = d / name
        if p.exists():
            return p
    return None

BOLD   = _find_font("DejaVuSans-Bold.ttf")
NORMAL = _find_font("DejaVuSans.ttf")

# Stil pro Lehrer
TEACHER_STYLE = {
    "vitali":    dict(label="[LUSTIG]",  bg="#FFF176", acc="#FF6F00", txt="#1A1A1A", sub="#5D4037", tag="HAHA"),
    "dering":    dict(label="[ERNST]",   bg="#F8F9FA", acc="#1565C0", txt="#0D0D0D", sub="#455A64", tag="EDU"),
    "imperator": dict(label="[NEON]",    bg="#050510", acc="#00E5FF", txt="#FFFFFF", sub="#B2EBF2", tag="ZAP"),
}
DEFAULT_STYLE = TEACHER_STYLE["vitali"]

W, H = 560, 370


def _hex(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def generate_card_bytes(
    word_de: str,
    word_ru: str,
    example: str,
    card_num: int = 1,
    teacher: str = "vitali",
) -> Optional[bytes]:
    """Gibt PNG-Bytes der Lernkarte zurueck, oder None wenn PIL fehlt."""
    if not PIL_AVAILABLE or BOLD is None or NORMAL is None:
        return None

    pack = TEACHER_STYLE.get(teacher, DEFAULT_STYLE)
    bg   = _hex(pack["bg"])
    acc  = _hex(pack["acc"])
    txt  = _hex(pack["txt"])
    sub  = _hex(pack["sub"])

    img  = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Bars
    draw.rectangle([0, 0, W, 12], fill=acc)
    draw.rectangle([0, H-12, W, H], fill=acc)
    draw.rectangle([5, 17, W-5, H-17], outline=acc, width=2)

    fBig   = ImageFont.truetype(str(BOLD),   58)
    fMed   = ImageFont.truetype(str(BOLD),   36)
    fSm    = ImageFont.truetype(str(NORMAL), 22)
    fLabel = ImageFont.truetype(str(BOLD),   17)

    draw.text((18, 20), pack["label"], font=fLabel, fill=acc)
    draw.text((W-62, 20), f"#{card_num:02d}", font=fLabel, fill=sub)

    bb = draw.textbbox((0, 0), word_de, font=fBig)
    draw.text(((W-(bb[2]-bb[0]))//2, 50), word_de, font=fBig, fill=txt)

    draw.rectangle([(W//2-100), 128, (W//2+100), 131], fill=acc)

    bb2 = draw.textbbox((0, 0), word_ru, font=fMed)
    draw.text(((W-(bb2[2]-bb2[0]))//2, 140), word_ru, font=fMed, fill=sub)

    wrapped = textwrap.fill(example, width=44)
    y = 208
    for line in wrapped.split("\n"):
        bb3 = draw.textbbox((0, 0), line, font=fSm)
        draw.text(((W-(bb3[2]-bb3[0]))//2, y), line, font=fSm, fill=sub)
        y += 28

    draw.rectangle([18, H-52, 82, H-22], fill=acc)
    bw = draw.textbbox((0, 0), pack["tag"], font=fLabel)
    draw.text((18+(64-(bw[2]-bw[0]))//2, H-46), pack["tag"], font=fLabel, fill=bg)
    draw.text((W-150, H-44), "natalia_bot", font=fLabel, fill=sub)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()
