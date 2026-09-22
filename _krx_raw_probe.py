import sys

import requests

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Referer": "http://data.krx.co.kr/contents/MDC/MDI/mdiLoader/index.cmd",
    "Origin": "http://data.krx.co.kr",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
})

payload = {
    "bld": "dbms/MDC/STAT/standard/MDCSTAT01501",
    "locale": "ko_KR",
    "tboxindIdx_finder_equidx0_0": "코스피",
    "codeNmindIdx_finder_equidx0_0": "",
    "param1indIdx_finder_equidx0_0": "",
    "indIdx": "1",
    "strtDd": "20240329",
    "endDd": "20240329",
    "share": "2",
    "money": "3",
    "csvxls_isNo": "false",
}
try:
    response = session.post(
        "http://data.krx.co.kr/comm/bldAttendant/getJsonData.cmd",
        data=payload,
        timeout=15,
    )
    sys.stdout.buffer.write(
        f"status={response.status_code} len={len(response.text)} head={response.text[:200]!r}\n".encode("utf-8")
    )
except Exception as error:
    sys.stdout.buffer.write(f"ERROR {error}\n".encode("utf-8"))