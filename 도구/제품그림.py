"""제품 소개서에 넣는 그림 (SVG). 사진이 없을 때 쓰는 단순한 용기 그림과 성분 층 그림.

- 용기 모양은 제품 이름·종류로 고른다: 앰플→스포이트 병, 크림→단지, 선크림·클렌징→튜브, 마스크→파우치, 그 밖→병
- 실제 제품 사진이 아니라는 것이 한눈에 보이도록 평면 그림으로만 그린다.
"""
from 공통 import DESIGN, esc

PALETTE = ["#2F8F83", "#3D7DD8", "#D99A1E", "#3FA37F", "#8C6BC8", "#D2604F"]


def accent_for(code):
    """제품 색: 디자인 설정의 '제품 색'에 코드가 있으면 그 색, 없으면 '색 목록'에서 차례로"""
    fixed = DESIGN.get("제품 색", {}).get(code)
    if fixed:
        return fixed
    pal = DESIGN.get("색 목록") or PALETTE
    digits = "".join(ch for ch in code if ch.isdigit()) or "0"
    return pal[(int(digits) - 1) % len(pal)]


def tint(hex_color, t):
    """흰색 쪽으로 t만큼 섞는다 (t=1이면 흰색)"""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    mix = lambda c: int(c + (255 - c) * t)
    return f"#{mix(r):02X}{mix(g):02X}{mix(b):02X}"


def shade(hex_color, t):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"#{int(r * (1 - t)):02X}{int(g * (1 - t)):02X}{int(b * (1 - t)):02X}"


def shape_for(name_ko, kind):
    s = f"{name_ko} {kind}"
    if "앰플" in s or "세럼" in s or "에센스" in s:
        return "dropper"
    if "크림" in s and "선" not in s:
        return "jar"
    if "선" in s or "클렌징" in s or "폼" in s:
        return "tube"
    if "마스크" in s or "팩" in s:
        return "pouch"
    return "bottle"


def _label(x, y, w, brand, name, accent, font):
    words, lines, cur = name.split(), [], ""
    for wd in words:
        if len(cur) + len(wd) + 1 > 12 and cur:
            lines.append(cur); cur = wd
        else:
            cur = f"{cur} {wd}".strip()
    lines.append(cur)
    out = f'<text x="{x + w / 2}" y="{y}" text-anchor="middle" font-size="7" letter-spacing="1" fill="{accent}" font-family=\'{font}\'>{esc(brand.upper())}</text>'
    for i, ln in enumerate(lines[:3]):
        out += f'<text x="{x + w / 2}" y="{y + 18 + i * 14}" text-anchor="middle" font-size="12" font-weight="700" fill="#1f2a2e" font-family=\'{font}\'>{esc(ln)}</text>'
    return out


def product_svg(code, name_ko, kind, brand_en, name_en, font):
    a = accent_for(code)
    shape = shape_for(name_ko, kind)
    bg = f"""<defs><linearGradient id="g{code}" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{tint(a, .78)}"/><stop offset="1" stop-color="{tint(a, .95)}"/></linearGradient></defs>
<rect width="300" height="340" rx="18" fill="url(#g{code})"/>
<path d="M30 292 C 70 250, 150 270, 200 256 S 285 262, 272 300 C 260 322, 60 330, 30 292 Z" fill="{tint(a, .62)}" opacity=".7"/>
<ellipse cx="150" cy="304" rx="78" ry="9" fill="{shade(a, .35)}" opacity=".18"/>"""
    dark, body = shade(a, .25), "#FFFFFF"
    if shape == "dropper":
        g = f"""<rect x="140" y="58" width="20" height="46" rx="10" fill="{dark}"/>
<rect x="132" y="100" width="36" height="30" rx="4" fill="{dark}"/>
<rect x="104" y="128" width="92" height="174" rx="20" fill="{body}" stroke="{tint(a, .55)}" stroke-width="1.5"/>
<rect x="104" y="232" width="92" height="70" rx="20" fill="{tint(a, .7)}" opacity=".55"/>
<rect x="114" y="160" width="72" height="62" rx="6" fill="#FBFAF7"/>""" + _label(114, 178, 72, brand_en, name_en, a, font)
    elif shape == "jar":
        g = f"""<rect x="78" y="168" width="144" height="40" rx="10" fill="{dark}"/>
<rect x="72" y="204" width="156" height="98" rx="16" fill="{body}" stroke="{tint(a, .55)}" stroke-width="1.5"/>
<rect x="72" y="204" width="156" height="10" fill="{tint(a, .6)}"/>
<rect x="96" y="226" width="108" height="60" rx="6" fill="#FBFAF7"/>""" + _label(96, 244, 108, brand_en, name_en, a, font)
    elif shape == "tube":
        g = f"""<rect x="96" y="92" width="108" height="16" rx="3" fill="{tint(a, .45)}"/>
<path d="M98 108 L202 108 L184 266 L116 266 Z" fill="{body}" stroke="{tint(a, .55)}" stroke-width="1.5"/>
<rect x="118" y="264" width="64" height="40" rx="7" fill="{dark}"/>
<rect x="112" y="140" width="76" height="70" rx="6" fill="#FBFAF7"/>""" + _label(112, 160, 76, brand_en, name_en, a, font)
    elif shape == "pouch":
        g = f"""<rect x="82" y="70" width="136" height="232" rx="10" fill="{body}" stroke="{tint(a, .55)}" stroke-width="1.5"/>
<rect x="82" y="70" width="136" height="22" rx="10" fill="{tint(a, .5)}"/>
<path d="M82 98 l8 -5 l-8 -5 Z" fill="{tint(a, .95)}"/>
<rect x="100" y="210" width="100" height="70" rx="50" fill="{tint(a, .78)}"/>
<rect x="98" y="122" width="104" height="66" rx="6" fill="#FBFAF7"/>""" + _label(98, 142, 104, brand_en, name_en, a, font)
    else:
        g = f"""<rect x="128" y="76" width="44" height="40" rx="6" fill="{dark}"/>
<rect x="100" y="114" width="100" height="188" rx="18" fill="{body}" stroke="{tint(a, .55)}" stroke-width="1.5"/>
<rect x="112" y="160" width="76" height="66" rx="6" fill="#FBFAF7"/>""" + _label(112, 178, 76, brand_en, name_en, a, font)
    return f'<svg viewBox="0 0 300 340" xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">{bg}{g}</svg>'


def _wrap(name, limit):
    if len(name) <= limit:
        return [name]
    if " " in name:
        out, cur = [], ""
        for w in name.split():
            if cur and len(cur) + len(w) + 1 > limit:
                out.append(cur); cur = w
            else:
                cur = f"{cur} {w}".strip()
        return out + [cur]
    return [name[i:i + limit] for i in range(0, len(name), limit)]


def ingredient_svg(code, items, font):
    """성분을 층처럼 쌓은 그림 + 이름 (성분은 최대 4개, 긴 이름은 두 줄)"""
    a = accent_for(code)
    items = items[:4]
    cjk = any("\u4e00" <= ch <= "\u9fff" for ch in "".join(items))
    limit = 9 if cjk else 20
    step = 64
    h = 40 + len(items) * step
    out = ""
    for k, name in enumerate(items):
        cy = 30 + k * step
        col = tint(a, .15 + k * .2)
        side = shade(col, .12)
        lines = _wrap(name, limit)[:2]
        ty = cy + 16 - (len(lines) - 1) * 12
        out += f"""<path d="M14 {cy} a48 13 0 0 0 96 0 v18 a48 13 0 0 1 -96 0 Z" fill="{side}"/>
<ellipse cx="62" cy="{cy}" rx="48" ry="13" fill="{col}"/>
<line x1="114" y1="{cy + 9}" x2="150" y2="{cy + 9}" stroke="#9aa6aa" stroke-width="1.2"/>
<circle cx="114" cy="{cy + 9}" r="2.6" fill="#9aa6aa"/>"""
        for i, ln in enumerate(lines):
            out += f'<text x="160" y="{ty + i * 25}" font-size="21" font-weight="700" fill="#1f2a2e" font-family=\'{font}\'>{esc(ln)}</text>'
    return f'<svg viewBox="0 0 400 {h}" xmlns="http://www.w3.org/2000/svg" width="100%">{out}</svg>'
