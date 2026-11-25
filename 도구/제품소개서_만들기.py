"""
제품 소개서 PDF 만들기 (중국어 · 영어, 제품 하나 = 한 장)

번역 검수표(코드·언어·항목·원문·번역·검수)를 읽어 제품별·언어별 PDF를 만든다.
- 내용은 검수표의 '번역' 칸만 쓴다. 칸이 비어 있으면 그 항목을 빼고, 지어서 채우지 않는다.
- 한 제품·한 언어의 줄이 모두 검수 'OK'일 때만 정식본을 만든다.
  하나라도 비어 있으면 '草稿 · 待审核' / 'DRAFT · for review' 표시를 붙이고 파일명 끝에 _草稿 / _DRAFT를 붙인다.

쓰는 법 (이 폴더 맨 위에서):
  python3 도구/제품소개서_만들기.py \
    --table 결과/2027-03-20_행사명/제품소개서/번역_검수표.csv \
    --products 내자료/제품목록.csv \
    --out 결과/2027-03-20_행사명/제품소개서 \
    --brand-zh 示例美妆 --brand-en "Example Beauty" --date 2027-03-20 \
    [--photos 내자료/사진] [--codes P01,P03] [--langs 중국어,영어]
"""
import argparse
from collections import defaultdict
from pathlib import Path

from 공통 import FONT_EN, FONT_ZH, esc, font_css, lang_key, load_design, logo_html, read_csv, safe_name, text_color, to_pdf
from 제품그림 import accent_for, ingredient_svg, product_svg, tint

LABEL = {
    "zh": {"doc": "产品介绍", "size": "规格", "ing": "主要成分", "feat": "产品特点", "use": "使用方法",
           "skin": "适用肤质", "store": "储存方法", "life": "保质期", "spec": "产品信息", "date": "资料日期",
           "draft": "草稿 · 待审核", "suffix": "_草稿", "file": "产品介绍", "sep": "、"},
    "en": {"doc": "Product Sheet", "size": "Size", "ing": "Key ingredients", "feat": "Highlights", "use": "How to use",
           "skin": "Skin type", "store": "Storage", "life": "Shelf life", "spec": "Product details", "date": "Issued",
           "draft": "DRAFT · for review", "suffix": "_DRAFT", "file": "ProductSheet", "sep": ","},
}
NAME_COL = {"zh": "제품명(중)", "en": "제품명(영)"}

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
body { margin: 0; font-family: %(font)s; color: #1f2a2e; font-size: 11pt; line-height: 1.65; }
.page { width: 210mm; height: 297mm; padding: 15mm 16mm 14mm; position: relative; }
.top { display: flex; justify-content: space-between; align-items: baseline;
       border-bottom: 1.2pt solid #1f2a2e; padding-bottom: 2.5mm; }
.brand { font-size: 13pt; font-weight: 700; letter-spacing: .5pt; }
.brand small { font-weight: 400; color: #6b7a7f; margin-left: 2mm; font-size: 9pt; }
.doc { font-size: 9pt; color: #6b7a7f; letter-spacing: 1.5pt; }
.draft { position: absolute; top: 7mm; right: 16mm; font-size: 8.5pt; color: #b3261e;
         border: .8pt solid #b3261e; padding: .5mm 2.5mm; border-radius: 2mm; }
.hero { display: flex; gap: 8mm; margin-top: 8mm; align-items: center; }
.hero .txt { flex: 1; }
.visual { width: 80mm; height: 98mm; border-radius: 4mm; overflow: hidden; }
.visual img { width: 100%%; height: 100%%; object-fit: cover; }
.meta span { font-size: 8.5pt; letter-spacing: 1pt; padding: .6mm 2.5mm; border-radius: 1.5mm; margin-right: 2mm;
             background: %(tint)s; color: %(accent_text)s; }
h1 { font-size: %(h1)s; line-height: 1.25; margin: 4mm 0 1mm; font-weight: 700; }
.sub { color: #6b7a7f; font-size: 10pt; }
.lead { font-size: 13pt; margin-top: 7mm; padding-left: 4mm; border-left: 2.4pt solid %(accent)s; }
h2 { font-size: 9.5pt; color: %(accent_text)s; letter-spacing: 1.2pt; margin: 0 0 2.5mm; font-weight: 700;
     border-bottom: .5pt solid #d5dddb; padding-bottom: 1.5mm; }
.ing { background: #f7f8f6; border-radius: 3mm; padding: 5mm 6mm 4mm; }
.grid { display: flex; gap: 9mm; margin-top: 11mm; }
.col { flex: 1; }
ol { margin: 0; padding: 0; list-style: none; counter-reset: f; }
ol li { counter-increment: f; margin-bottom: 2mm; padding-left: 9mm; position: relative; }
ol li:before { content: counter(f, decimal-leading-zero); position: absolute; left: 0; top: .2mm;
               font-size: 9pt; font-weight: 700; color: %(accent_text)s; }
table { width: 100%%; border-collapse: collapse; font-size: 10pt; }
th { text-align: left; color: #6b7a7f; font-weight: 400; width: 30%%; vertical-align: top; padding: 1.6mm 0; }
td { padding: 1.6mm 0; vertical-align: top; }
tr { border-bottom: .5pt solid #e3e9e7; }
.use div { background: %(tint)s; padding: 4mm 5mm; border-radius: 2mm; }
.foot { position: absolute; left: 16mm; right: 16mm; bottom: 10mm; display: flex; justify-content: space-between;
        font-size: 8pt; color: #8a979b; border-top: .5pt solid #d5dddb; padding-top: 2.5mm; }
"""


def build_html(lang, code, product, f, brand_zh, brand_en, date, photo, draft):
    L = LABEL[lang]
    name = product.get(NAME_COL[lang]) or product.get("제품명(한)", code)
    sub = product.get("제품명(영)", "") if lang == "zh" else ""
    brand_main, brand_sub = (brand_zh, brand_en) if lang == "zh" else (brand_en, "")
    face, font = font_css(lang)
    accent = accent_for(code)
    ing = [x.strip() for x in f.get("주요 성분", "").replace("、", ",").split(",") if x.strip()]
    feats = [f[k] for k in ("특징1", "특징2", "특징3") if f.get(k)]
    spec = [(L["size"], f.get("용량")), (L["skin"], f.get("피부 타입")),
            (L["life"], f.get("사용기한")), (L["store"], f.get("보관 방법"))]
    spec = [(a, b) for a, b in spec if b]

    if photo:
        visual = f'<img src="{Path(photo).resolve().as_uri()}">'
    else:
        visual = product_svg(code, product.get("제품명(한)", ""), product.get("종류", ""), brand_en,
                             product.get("제품명(영)", "") or name, font)
    ing_html = f'<div class="ing"><h2>{L["ing"]}</h2>{ingredient_svg(code, ing, font)}</div>' if ing else ""
    long_name = len(name) > (14 if lang == "en" else 8)
    left = f'<h2>{L["feat"]}</h2><ol>' + "".join(f"<li>{esc(x)}</li>" for x in feats) + "</ol>" if feats else ""
    right = f'<h2>{L["spec"]}</h2><table>' + "".join(
        f"<tr><th>{esc(a)}</th><td>{esc(b)}</td></tr>" for a, b in spec) + "</table>" if spec else ""
    use = f'<div class="use"><h2>{L["use"]}</h2><div>{esc(f["사용법"])}</div></div>' if f.get("사용법") else ""
    lead = f'<div class="lead">{esc(f["한 줄 소개"])}</div>' if f.get("한 줄 소개") else ""
    cat = f'<span>{esc(f["종류"])}</span>' if f.get("종류") else ""
    css = face + CSS % {"font": font, "accent": accent, "accent_text": text_color(accent), "tint": tint(accent, .88),
                        "h1": "23pt" if long_name else "28pt"}
    logo = logo_html()
    return f"""<!DOCTYPE html><html lang="{'zh-CN' if lang == 'zh' else 'en'}"><head><meta charset="utf-8">
<style>{css}</style></head><body><div class="page">
{'<div class="draft">' + L['draft'] + '</div>' if draft else ''}
<div class="top"><div class="brand">{logo or esc(brand_main)}<small>{'' if logo else esc(brand_sub)}</small></div><div class="doc">{L['doc'].upper() if lang == 'en' else L['doc']}</div></div>
<div class="hero"><div class="txt"><div class="meta"><span>{esc(code)}</span>{cat}</div>
<h1>{esc(name)}</h1>{f'<div class="sub">{esc(sub)}</div>' if sub else ''}{lead}</div>
<div class="visual">{visual}</div></div>
<div class="grid"><div class="col" style="flex:1.15">{ing_html}</div><div class="col">{left}</div></div>
<div class="grid"><div class="col" style="flex:1.15">{right}</div><div class="col">{use}</div></div>
<div class="foot"><span>{esc(brand_main)}{' · ' + esc(brand_en) if lang == 'zh' else ''}</span><span>{L['date']} {esc(date)} · {esc(code)}</span></div>
</div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True, help="번역 검수표 CSV")
    ap.add_argument("--products", required=True, help="제품목록 CSV")
    ap.add_argument("--out", required=True)
    ap.add_argument("--brand-zh", required=True)
    ap.add_argument("--brand-en", required=True)
    ap.add_argument("--date", required=True, help="자료 날짜 YYYY-MM-DD")
    ap.add_argument("--photos", help="제품 사진 폴더 (P01.jpg / P01.png). 없으면 사진 없이 만든다")
    ap.add_argument("--codes", help="만들 제품 코드, 쉼표로 구분 (없으면 전부)")
    ap.add_argument("--langs", default="중국어,영어")
    ap.add_argument("--design", help="디자인 설정 JSON (없으면 내자료/디자인설정.json → 양식/디자인설정_기본.json)")
    a = ap.parse_args()
    d = load_design(a.design)
    print(f"디자인 설정: {d['_파일']} ({d.get('설정 상태', '')})")

    products = {p["코드"]: p for p in read_csv(a.products)}
    data, review = defaultdict(dict), defaultdict(list)
    for r in read_csv(a.table):
        key = (r["코드"], lang_key(r["언어"]))
        data[key][r["항목"]] = r["번역"]
        review[key].append(r.get("검수", "").upper() == "OK")
    codes = [c.strip() for c in a.codes.split(",")] if a.codes else sorted({k[0] for k in data})
    langs = [lang_key(x) for x in a.langs.split(",")]
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)

    made = []
    for code in codes:
        if code not in products:
            print(f"!! {code}: 제품목록에 없음 — 건너뜀"); continue
        for lang in langs:
            key = (code, lang)
            if key not in data:
                print(f"!! {code} {lang}: 검수표에 번역이 없음 — 건너뜀"); continue
            draft = not all(review[key])
            photo = None
            if a.photos:
                for ext in (".png", ".jpg", ".jpeg"):
                    p = Path(a.photos) / f"{code}{ext}"
                    if p.exists():
                        photo = p; break
            L = LABEL[lang]
            pname = products[code].get(NAME_COL[lang]) or code
            fn = f"{code}_{L['file']}_{safe_name(pname)}{L['suffix'] if draft else ''}.pdf"
            to_pdf(build_html(lang, code, products[code], data[key], a.brand_zh, a.brand_en, a.date, photo, draft), out / fn)
            made.append((fn, draft))
            print(("초안 " if draft else "정식 ") + fn)
    n_draft = sum(d for _, d in made)
    print(f"완료: {len(made)}개 (정식 {len(made) - n_draft} · 검수 전 초안 {n_draft})")


if __name__ == "__main__":
    main()
