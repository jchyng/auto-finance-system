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


def fetch_accounts(corp_code: str, year: str, fs_div: str = "CFS"):
    params = {
        "crtfc_key": api_key,
        "corp_code": corp_code,
        "bsns_year": year,
        "reprt_code": "11011",
        "fs_div": fs_div,
    }
    url = (
        "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json?"
        + urllib.parse.urlencode(params)
    )
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


# 1) 삼성전자: CF 섹션 전체 행
payload = fetch_accounts("00126380", "2023")
sys.stdout.buffer.write("== SAMSUNG CF ROWS ==\n".encode("utf-8"))
for account in payload.get("list") or []:
    if account.get("sj_div") == "CF":
        sys.stdout.buffer.write(
            f"{account.get('account_nm')} | {account.get('thstrm_amount')}\n".encode("utf-8")
        )

# 2) 현대차: 순이익/세금 관련 행
payload = fetch_accounts("00164742", "2023")
sys.stdout.buffer.write("\n== HYUNDAI INCOME ROWS ==\n".encode("utf-8"))
for account in payload.get("list") or []:
    name = account.get("account_nm") or ""
    if any(k in name for k in ["순이익", "법인세", "당기이익"]):
        sys.stdout.buffer.write(
            f"{name} | {account.get('thstrm_amount')}\n".encode("utf-8")
        )