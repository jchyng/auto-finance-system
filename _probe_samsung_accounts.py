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

keywords = ["감가", "상각", "법인세", "이자", "당기순이익", "지배", "매출"]
seen = set()
for account in payload.get("list", []):
    name = account.get("account_nm", "")
    if any(keyword in name for keyword in keywords) and name not in seen:
        seen.add(name)
        sys.stdout.buffer.write(
            f"{name} | {account.get('thstrm_amount')}\n".encode("utf-8")
        )