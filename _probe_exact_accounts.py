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

targets = ["이자비용", "금융비용", "감가상각비", "유형자산감가상각비", "무형자산상각비",
           "법인세비용", "법인세차감전순이익"]
for account in payload.get("list", []):
    name = (account.get("account_nm") or "").strip()
    if name in targets:
        sys.stdout.buffer.write(
            f"[exact] {name} | {account.get('thstrm_amount')}\n".encode("utf-8")
        )