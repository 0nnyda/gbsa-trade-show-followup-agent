"""
팀 공유용 엑셀 만들기

결과 폴더의 CSV(바이어관리표 · 바이어별_제품관심 · 업데이트기록)를 모아 바이어관리표.xlsx를 새로 만든다.
엑셀은 실행할 때마다 새로 만들어지므로 직접 고치지 않는다. 고칠 것은 CSV에서 고치거나 Claude에게 말한다.

쓰는 법 (이 폴더 맨 위에서):
  python3 도구/관리표_엑셀만들기.py 결과/2027-03-20_행사명 --products 내자료/제품목록.csv
"""
import argparse
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from 공통 import read_csv

FONT = "맑은 고딕"
F_BASE, F_HEAD = Font(name=FONT, size=10), Font(name=FONT, size=10, bold=True)
F_TITLE, F_NOTE = Font(name=FONT, size=13, bold=True), Font(name=FONT, size=9, color="595959")
FILL_HEAD = PatternFill("solid", fgColor="D9E1F2")
LINE = Side(style="thin", color="BFBFBF")
BOX = Border(left=LINE, right=LINE, top=LINE, bottom=LINE)
STATUS = ["할 일", "보냄", "회신 받음", "끝", "보류"]
STAGES = ["견적", "샘플", "자료", "관심"]          # 강한 순서
STAGE_FILL = {"견적": "1F6F5C", "샘플": "63A48F", "자료": "B7DCCF", "관심": "E6F2EE"}
GRADE_FILL = {"A": "E2EFDA", "B": "FFF2CC", "C": "EDEDED"}


def table(ws, top, header, rows, widths, wrap=True):
    for j, h in enumerate(header, 1):
        c = ws.cell(top, j, h)
        c.font, c.fill, c.border = F_HEAD, FILL_HEAD, BOX
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, r in enumerate(rows, top + 1):
        for j, v in enumerate(r, 1):
            c = ws.cell(i, j, v)
            c.font, c.border = F_BASE, BOX
            c.alignment = Alignment(wrap_text=wrap, vertical="top")
    for j, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(j)].width = w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", help="결과 폴더 (바이어관리표.csv가 있는 곳)")
    ap.add_argument("--products", required=True)
    ap.add_argument("--columns", default=str(Path(__file__).resolve().parent.parent / "양식" / "바이어관리표_칸설명.csv"))
    a = ap.parse_args()
    folder = Path(a.folder)
    buyers = read_csv(folder / "바이어관리표.csv")
    interest = read_csv(folder / "바이어별_제품관심.csv") if (folder / "바이어별_제품관심.csv").exists() else []
    updates = read_csv(folder / "업데이트기록.csv") if (folder / "업데이트기록.csv").exists() else []
    products = read_csv(a.products)
    cols = list(buyers[0].keys())
    n = len(buyers)

    wb = Workbook()
    # ---- 0. 읽는 법
    ws = wb.active; ws.title = "읽는 법"
    ws["A1"] = "상담 후속 관리표"; ws["A1"].font = F_TITLE
    ws["A2"] = f"바이어 {n}곳 · 제품 {len(products)}개 · 이 파일은 도구/관리표_엑셀만들기.py가 CSV로 새로 만든다. 직접 고치지 말고 CSV를 고치거나 Claude에게 말한다."
    ws["A2"].font = F_NOTE
    guide = [["바이어 관리표", "바이어 한 곳 = 한 줄. 진행 상태 칸으로 팀이 어디까지 했는지 본다"],
             ["관심도 표", "바이어 × 제품. 칸에는 그 제품에 대한 관심 단계 (견적 > 샘플 > 자료 > 관심)"],
             ["제품별 관심", "제품마다 관심 바이어 수, 단계별 수, A등급 바이어 수 (관심도 표에서 수식으로 셈)"],
             ["후속 일정", "마감이 빠른 순서"],
             ["확인 필요", "사람이 확인해야 할 것만 모음"],
             ["업데이트 기록", "팀원이 말한 진행 변화가 쌓이는 곳 (최신이 위)"],
             ["칸 설명", "관리표 칸의 뜻과 쓰는 값"]]
    table(ws, 4, ["시트", "보는 것"], guide, [16, 90])

    # ---- 1. 바이어 관리표
    ws = wb.create_sheet("바이어 관리표")
    width = {"번호": 7, "상담일": 11, "바이어 유형": 20, "지역": 12, "언어": 8, "연락 경로": 10, "관심 제품": 22,
             "요청 사항": 36, "우리가 약속한 것": 22, "등급": 6, "등급 근거": 22, "다음 할 일": 36, "마감": 11,
             "확인 필요": 34, "진행 상태": 10, "최근 업데이트": 12}
    table(ws, 1, cols, [[b[c] for c in cols] for b in buyers], [width.get(c, 14) for c in cols])
    ws.freeze_panes = "B2"; ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{n + 1}"
    gcol = get_column_letter(cols.index("등급") + 1)
    for g, color in GRADE_FILL.items():
        ws.conditional_formatting.add(f"{gcol}2:{gcol}{n + 1}", CellIsRule(operator="equal", formula=[f'"{g}"'], fill=PatternFill("solid", fgColor=color)))
    if "진행 상태" in cols:
        scol = get_column_letter(cols.index("진행 상태") + 1)
        dv = DataValidation(type="list", formula1='"' + ",".join(STATUS) + '"', allow_blank=True)
        ws.add_data_validation(dv); dv.add(f"{scol}2:{scol}{n + 1}")
        ws.conditional_formatting.add(f"A2:{get_column_letter(len(cols))}{n + 1}",
            FormulaRule(formula=[f'${scol}2="끝"'], font=Font(name=FONT, size=10, color="A6A6A6")))

    # ---- 2. 관심도 표 (바이어 × 제품)
    ws = wb.create_sheet("관심도 표")
    pcodes = [p["코드"] for p in products]
    extra = ["목록 외"] if any(r["코드"] not in pcodes for r in interest) else []
    heads = ["번호", "바이어 유형", "등급"] + [f'{p["코드"]} {p["제품명(한)"]}' for p in products] + extra
    stage_of = {}
    for r in interest:
        k = (r["번호"], r["코드"] if r["코드"] in pcodes else "목록 외")
        old = stage_of.get(k)
        if old is None or STAGES.index(r["관심 단계"]) < STAGES.index(old):
            stage_of[k] = r["관심 단계"]
    rows = [[b["번호"], b["바이어 유형"], b["등급"]] + [stage_of.get((b["번호"], c)) for c in pcodes + extra] for b in buyers]
    table(ws, 1, heads, rows, [7, 24, 6] + [13] * (len(pcodes) + len(extra)), wrap=True)
    for j in range(4, len(heads) + 1):
        for i in range(2, n + 2):
            ws.cell(i, j).alignment = Alignment(horizontal="center", vertical="center")
    last = get_column_letter(len(heads))
    rng = f"D2:{last}{n + 1}"
    for s, color in STAGE_FILL.items():
        ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=[f'"{s}"'], fill=PatternFill("solid", fgColor=color),
                                      font=Font(name=FONT, size=10, color="FFFFFF" if s in ("견적", "샘플") else "1F2A2E")))
    dv = DataValidation(type="list", formula1='"' + ",".join(STAGES) + '"', allow_blank=True)
    ws.add_data_validation(dv); dv.add(rng)
    ws.freeze_panes = "D2"
    ws.cell(n + 3, 1, "칸 = 그 제품에 대해 메모에 적힌 가장 강한 요청: 견적(가격·MOQ 문의) > 샘플 > 자료(카탈로그·소개서·성분표) > 관심(말로만)").font = F_NOTE

    # ---- 3. 제품별 관심 (수식)
    ws = wb.create_sheet("제품별 관심")
    head = ["코드", "제품", "관심 바이어 수", "견적", "샘플", "자료", "관심", "A등급 바이어 수"]
    plist = [(p["코드"], p["제품명(한)"]) for p in products] + ([("목록 외", "제품목록에 없는 제품")] if extra else [])
    table(ws, 1, head, [[c, nm] for c, nm in plist], [9, 22, 14, 8, 8, 8, 8, 15])
    src = "'관심도 표'"
    grade = f"{src}!$C$2:$C${n + 1}"
    for i, _ in enumerate(plist, 2):
        col = get_column_letter(4 + i - 2)
        r = f"{src}!${col}$2:${col}${n + 1}"
        ws.cell(i, 3, f"=COUNTA({r})")
        for j, s in enumerate(STAGES, 4):
            ws.cell(i, j, f'=COUNTIF({r},"{s}")')
        ws.cell(i, 8, f'=COUNTIFS({grade},"A",{r},"<>")')
        for j in range(3, 9):
            c = ws.cell(i, j); c.font, c.border, c.alignment = F_BASE, BOX, Alignment(horizontal="center")
    tot = len(plist) + 2
    ws.cell(tot, 2, "바이어 수 (관심도 표)").font = F_HEAD
    ws.cell(tot, 3, f"=COUNTA({src}!$A$2:$A${n + 1})").font = F_HEAD
    ws.cell(tot + 1, 1, "한 바이어가 여러 제품에 관심이 있으면 제품마다 센다. 관심 단계는 '관심도 표'를 바꾸면 다시 계산된다.").font = F_NOTE
    ws.freeze_panes = "C2"

    # ---- 4. 후속 일정
    ws = wb.create_sheet("후속 일정")
    order = sorted(buyers, key=lambda b: (b["마감"], b["등급"], b["번호"]))
    table(ws, 1, ["마감", "번호", "등급", "다음 할 일", "진행 상태"],
          [[b["마감"], b["번호"], b["등급"], b["다음 할 일"], b.get("진행 상태", "")] for b in order], [11, 7, 6, 60, 10])
    ws.freeze_panes = "A2"

    # ---- 5. 확인 필요
    ws = wb.create_sheet("확인 필요")
    need = [b for b in buyers if b["확인 필요"] not in ("", "-")]
    table(ws, 1, ["번호", "등급", "확인 필요", "진행 상태"],
          [[b["번호"], b["등급"], b["확인 필요"], b.get("진행 상태", "")] for b in need], [7, 6, 70, 10])
    ws.freeze_panes = "A2"

    # ---- 6. 업데이트 기록
    ws = wb.create_sheet("업데이트 기록")
    table(ws, 1, ["일시", "번호", "바뀐 것", "메모"],
          [[u["일시"], u["번호"], u["바뀐 것"], u["메모"]] for u in updates], [17, 7, 34, 60])
    if not updates:
        ws.cell(3, 1, "아직 없음. 예: \"B02 중문 소개서 보냈어\"라고 말하면 여기와 관리표의 진행 상태가 바뀐다.").font = F_NOTE
    ws.freeze_panes = "A2"

    # ---- 7. 칸 설명
    ws = wb.create_sheet("칸 설명")
    spec = read_csv(a.columns)
    table(ws, 1, ["칸", "뜻", "쓰는 값"], [[s["칸"], s["뜻"], s["쓰는 값"]] for s in spec], [14, 40, 50])

    out = folder / "바이어관리표.xlsx"
    wb.save(out)
    print(f"완료: {out} (바이어 {n} · 관심 {len(interest)}줄 · 업데이트 {len(updates)}줄)")


if __name__ == "__main__":
    main()
