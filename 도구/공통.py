"""도구 스크립트들이 같이 쓰는 함수 (CSV 읽기, PDF 만들기, 글꼴)."""
import csv, html, re, sys
from pathlib import Path

FONT_ZH = '"Noto Sans CJK SC", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", "PingFang SC", sans-serif'
FONT_EN = '"Noto Sans", "Helvetica Neue", Arial, "Noto Sans CJK SC", "Microsoft YaHei", sans-serif'


def read_csv(path):
    """UTF-8(BOM 있어도 됨) CSV를 dict 목록으로 읽는다. 칸 이름 앞뒤 공백은 지운다."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    return [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in rows]


def esc(s):
    return html.escape(s or "")


def safe_name(s):
    s = re.sub(r"[\\/:*?\"<>|]", "", s or "").strip()
    return re.sub(r"\s+", "-", s)


def to_pdf(html_text, out_path):
    """HTML을 PDF로 저장한다. WeasyPrint가 없으면 설치 방법을 알려 주고 멈춘다."""
    try:
        from weasyprint import HTML
    except ImportError:
        sys.exit("WeasyPrint가 없습니다. 먼저 실행하세요: pip install weasyprint")
    HTML(string=html_text).write_pdf(str(out_path))


def lang_key(s):
    """'중국어'/'zh' → 'zh', '영어'/'en' → 'en'"""
    s = (s or "").strip().lower()
    if s in ("중국어", "zh", "cn", "中文", "chinese"):
        return "zh"
    if s in ("영어", "en", "english"):
        return "en"
    sys.exit(f"언어는 중국어 또는 영어만 됩니다: {s}")


# ---------------------------------------------------------------- 디자인 설정 (브랜드 색 · 글꼴 · 로고)
import json

ROOT = Path(__file__).resolve().parent.parent
DESIGN = {}


def load_design(path=None):
    """내자료/디자인설정.json → 없으면 양식/디자인설정_기본.json. --design으로 다른 파일을 줄 수 있다."""
    cands = [Path(path)] if path else [ROOT / "내자료" / "디자인설정.json", ROOT / "양식" / "디자인설정_기본.json"]
    for p in cands:
        if p.exists():
            DESIGN.clear()
            DESIGN.update(json.loads(p.read_text(encoding="utf-8")))
            DESIGN["_파일"] = p.name
            return DESIGN
    sys.exit("디자인 설정 파일이 없습니다: 양식/디자인설정_기본.json")


def _file(rel):
    if not rel:
        return None
    p = Path(rel)
    p = p if p.is_absolute() else ROOT / p
    if not p.exists():
        print(f"!! 디자인 설정의 파일을 찾지 못함: {rel} — 기본값으로 만든다")
        return None
    return p


def font_css(lang):
    """(@font-face CSS, font-family 목록). 설정에 글꼴 파일이 있으면 그 글꼴을 맨 앞에 둔다."""
    key = {"zh": "중국어", "en": "영어"}[lang]
    base = FONT_ZH if lang == "zh" else FONT_EN
    f = _file(DESIGN.get("글꼴", {}).get(key, ""))
    if not f:
        return "", base
    return f'@font-face {{ font-family: "Brand{lang}"; src: url("{f.resolve().as_uri()}"); }}\n', f'"Brand{lang}", ' + base


def logo_html(height="9mm"):
    f = _file(DESIGN.get("로고", ""))
    return f'<img src="{f.resolve().as_uri()}" style="height:{height}; vertical-align: middle;">' if f else ""


def _lum(h):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(c1, c2="#FFFFFF"):
    a, b = sorted((_lum(c1), _lum(c2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def text_color(color, bg="#FFFFFF", need=4.5):
    """글자로 쓸 때 배경과 대비가 need 이상이 될 때까지 색을 진하게 한다 (밝은 브랜드 색 대비 보정)"""
    r, g, b = (int(color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    c = color
    for k in range(20):
        if contrast(c, bg) >= need:
            return c
        t = (k + 1) * 0.05
        c = "#%02X%02X%02X" % (int(r * (1 - t)), int(g * (1 - t)), int(b * (1 - t)))
    return c
