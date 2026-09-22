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

# 삼성전자 OFS(별도)에서 감가상각 계정 존재 여부 확인
for fs_div in ["CFS", "OFS"]:
    params = {
        "crtfc_key": api_key,
        "corp_code": "00126380",
        "bsns_year": "2023",
        "reprt_code": "11011",
        "fs_div": fs_div,
    }
    url = (
        "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json?"
        + urllib.parse.urlencode(params)
    )
    with urllib.request.urlopen(url, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    accounts = payload.get("list") or []
    sys.stdout.buffer.write(f"== fs_div={fs_div} total={len(accounts)}\n".encode("utf-8"))
    for account in accounts:
        name = (account.get("account_nm") or "").strip()
        if "상각" in name or "감가" in name:
            sys.stdout.buffer.write(
                f"  [{account.get('sj_div')}] {name} | {account.get('thstrm_amount')}\n".encode("utf-8")
            )