from pathlib import Path
import json
import sys
import urllib.parse
import urllib.request

project_root = Path(r"C:\Users\jcy03\dev")

api_key = None
for line in (project_root / ".env").read_text(encoding="utf-8").splitlines():
    if line.strip().startswith("DART_API_KEY"):
        api_key = line.split("=", 1)[1].strip()
        break

params = {
    "crtfc_key": api_key,
    "corp_code": "00126380",
    "bsns_year": "2023",
    "reprt_code": "11011",
    "fs_div": "CFS",
}
url = (
    "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json?"
    + urllib.parse.urlencode(params)
)
with urllib.request.urlopen(url, timeout=15) as response:
    payload = json.loads(response.read().decode("utf-8"))

accounts = payload.get("list") or []
sys.stdout.buffer.write(f"total={len(accounts)} status={payload.get('status')}\n".encode("utf-8"))

# 현금흐름/상각 관련 행 전체 출력
for account in accounts:
    name = (account.get("account_nm") or "").strip()
    sid = account.get("sj_div", "")
    if any(keyword in name for keyword in ["상각", "감가", "현금흐름", "영업활동"]):
        sys.stdout.buffer.write(
            f"[{sid}] {name} | {account.get('thstrm_amount')}\n".encode("utf-8")
        )