"""
견적서 PDF 만들기 (중국어 · 영어, 바이어 한 곳 = 한 장)

- 품목: 바이어별_제품관심.csv에서 그 바이어의 '관심 단계'가 '견적'인 제품 (또는 --codes로 지정)
- 단가 · 통화 · MOQ · 가격 조건 · 결제 조건 · 납기 · 견적 유효기간: 가격표.csv에 적힌 값만 쓴다.
  비어 있으면 [待确认] / [TBC]로 두고, 지어서 채우지 않는다.
- 비어 있는 칸이 하나라도 있으면 '草稿' / 'DRAFT' 표시를 붙이고 파일명 끝에 _草稿 / _DRAFT를 붙인다.
- 수량(--qty)을 주면 수량·금액 칸이 생긴다. 금액은 수량 × 단가로 계산만 한다.

쓰는 법 (이 폴더 맨 위에서):
  python3 도구/견적서_만들기.py --buyer B02 --lang 중국어 \
    --interest 결과/2027-03-20_행사명/바이어별_제품관심.csv \
    --products 내자료/제품목록.csv --prices 내자료/가격표.csv \
    --out 결과/2027-03-20_행사명/견적서 \
    --brand-zh 示例美妆 --brand-en "Example Beauty" --date 2027-03-20 \
    [--customer "바이어 회사명"] [--qty P03=3000] [--codes P03,P04]
"""
import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path

from 공통 import DESIGN, esc, font_css, lang_key, load_design, logo_html, read_csv, text_color, to_pdf
from 제품그림 import tint

L = {
 "zh": dict(doc="报价单", no="报价编号", date="报价日期", to="客户", by="报价方", tbc="[待确认]",
            cols=["序号", "产品编号", "产品名称", "规格", "单价", "币种", "最小起订量"], qty="数量", amt="金额",
            terms="交易条件", t=["价格条款", "付款方式", "交货期", "报价有效期"], draft="草稿 · 待确认",
            note="本报价以双方最终确认的订单或合同为准。", sfx="_草稿", file="报价单", dept="海外业务部"),
 "en": dict(doc="QUOTATION", no="Quotation No.", date="Date", to="To", by="From", tbc="[TBC]",
            cols=["No.", "Code", "Product", "Size", "Unit price", "Currency", "MOQ"], qty="Qty", amt="Amount",
            terms="Terms", t=["Price terms", "Payment", "Lead time", "Valid until"], draft="DRAFT · to be confirmed",
            note="Final terms are subject to the confirmed order or contract.", sfx="_DRAFT", file="Quotation",
            dept="Overseas Sales"),
}
NAME_COL = {"zh": "제품명(중)", "en": "제품명(영)"}
TERM_COL = ["가격 조건", "결제 조건", "납기", "견적 유효기간"]

CSS = """
@page { size: A4; margin: 18mm 18mm 16mm; }
body { font-family: %(font)s; color: #1f2a2e; font-size: 10.5pt; line-height: 1.6; }
.top { display: flex; justify-content: space-between; align-items: flex-end; border-bottom: 1.2pt solid #1f2a2e; padding-bottom: 3mm; }
.brand { font-size: 13pt; font-weight: 700; }
h1 { margin: 0; font-size: 20pt; letter-spacing: 2pt; }
.draft { color: #b3261e; border: .8pt solid #b3261e; padding: .5mm 2.5mm; border-radius: 2mm; font-size: 8.5pt; display: inline-block; margin-bottom: 2mm; }
.info { display: flex; gap: 10mm; margin: 8mm 0; }
.info div { flex: 1; }
.k { color: #6b7a7f; font-size: 9pt; }
table.items { width: 100%%; border-collapse: collapse; font-size: 10pt; }
table.items th { background: %(tint)s; text-align: left; padding: 2mm; font-weight: 700; font-size: 9pt; }
table.items td { padding: 2.2mm 2mm; border-bottom: .5pt solid #dfe6e4; vertical-align: top; }
.tbc { color: #b3261e; }
h2 { font-size: 9.5pt; color: %(accent)s; letter-spacing: 1pt; margin: 9mm 0 2mm; }
table.terms { border-collapse: collapse; width: 100%%; font-size: 10pt; }
table.terms th { text-align: left; color: #6b7a7f; font-weight: 400; width: 28%%; padding: 1.6mm 0; }
table.terms td { padding: 1.6mm 0; }
table.terms tr { border-bottom: .5pt solid #e3e9e7; }
.note { margin-top: 8mm; font-size: 9pt; color: #6b7a7f; }
"""


def num(s):
    try:
        return Decimal((s or "").replace(",", ""))
    except InvalidOperation:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--buyer", required=True)
    ap.add_argument("--lang", required=True, help="중국어 또는 영어")
    ap.add_argument("--interest", required=True)
    ap.add_argument("--products", required=True)
    ap.add_argument("--prices", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--brand-zh", required=True)
    ap.add_argument("--brand-en", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--customer", default="")
    ap.add_argument("--qty", default="", help="P03=3000,P04=1000")
    ap.add_argument("--codes", default="")
    ap.add_argument("--design", help="디자인 설정 JSON (없으면 내자료/디자인설정.json → 양식/디자인설정_기본.json)")
    a = ap.parse_args()
    load_design(a.design)
    lang = lang_key(a.lang); T = L[lang]; tbc = T["tbc"]

    products = {p["코드"]: p for p in read_csv(a.products)}
    prices = {p["코드"]: p for p in read_csv(a.prices)}
    if a.codes:
        codes = [c.strip() for c in a.codes.split(",") if c.strip()]
    else:
        codes = [r["코드"] for r in read_csv(a.interest) if r["번호"] == a.buyer and r["관심 단계"] == "견적"]
    codes = [c for c in codes if c in products]
    if not codes:
        raise SystemExit(f"{a.buyer}: 견적 단계인 제품목록 제품이 없습니다. --codes로 지정하세요.")
    qty = dict(x.split("=") for x in a.qty.split(",") if "=" in x)

    missing = []
    def val(v, what):
        if v:
            return esc(v)
        missing.append(what)
        return f'<span class="tbc">{tbc}</span>'

    cols = T["cols"][:4] + ([T["qty"]] if qty else []) + T["cols"][4:6] + ([T["amt"]] if qty else []) + T["cols"][6:]
    rows = ""
    for i, c in enumerate(codes, 1):
        p, pr = products[c], prices.get(c, {})
        name = p.get(NAME_COL[lang]) or p.get("제품명(한)", c)
        cells = [str(i), esc(c), esc(name), val(pr.get("규격"), f"{c} 규격")]
        if qty:
            cells.append(val(qty.get(c), f"{c} 수량"))
        cells += [val(pr.get("단가"), f"{c} 단가"), val(pr.get("통화"), f"{c} 통화")]
        if qty:
            q, u = num(qty.get(c)), num(pr.get("단가"))
            cells.append(f"{q * u:,}" if q is not None and u is not None else f'<span class="tbc">{tbc}</span>')
        cells.append(val(pr.get("MOQ"), f"{c} MOQ"))
        rows += "<tr>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>"

    terms = ""
    for label, col in zip(T["t"], TERM_COL):
        vals = {c: prices.get(c, {}).get(col, "") for c in codes}
        uniq = set(vals.values())
        if len(uniq) == 1:
            v = val(uniq.pop(), col)
        else:
            v = " / ".join(f"{esc(c)}: {val(x, f'{c} {col}')}" for c, x in vals.items())
        terms += f"<tr><th>{label}</th><td>{v}</td></tr>"

    customer = val(a.customer, "고객명")
    draft = bool(missing)
    brand = a.brand_zh if lang == "zh" else a.brand_en
    face, font = font_css(lang)
    main = DESIGN.get("견적서 색") or "#2F6F62"
    logo = logo_html()
    qno = f"Q-{a.date.replace('-', '')}-{a.buyer}"
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>{face}{CSS % {'font': font, 'accent': text_color(main), 'tint': tint(main, .88)}}</style></head><body>
<div class="top"><div class="brand">{logo or esc(brand)}</div><div style="text-align:right">{'<div class="draft">' + T['draft'] + '</div><br>' if draft else ''}<h1>{T['doc']}</h1></div></div>
<div class="info"><div><div class="k">{T['to']}</div>{customer}</div>
<div><div class="k">{T['by']}</div>{esc(brand)} {T['dept']}</div>
<div><div class="k">{T['no']}</div>{qno}<div class="k" style="margin-top:2mm">{T['date']}</div>{esc(a.date)}</div></div>
<table class="items"><tr>{''.join(f'<th>{x}</th>' for x in cols)}</tr>{rows}</table>
<h2>{T['terms']}</h2><table class="terms">{terms}</table>
<div class="note">{T['note']}</div>
</body></html>"""
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    fn = f"{a.buyer}_{T['file']}{T['sfx'] if draft else ''}.pdf"
    to_pdf(html, out / fn)
    print(("초안 " if draft else "정식 ") + fn)
    if missing:
        print("채워야 할 칸: " + ", ".join(dict.fromkeys(missing)))


if __name__ == "__main__":
    main()
