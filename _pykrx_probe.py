from pathlib import Path
import sys

sys.path.insert(0, str(Path(r"C:\Users\jcy03\dev")))

from pykrx import stock as pykrx_stock

for date_string in ["20240329", "20260911", "20260923"]:
    try:
        df = pykrx_stock.get_market_cap_by_date(
            fromdate=date_string, todate=date_string, ticker="005930"
        )
        sys.stdout.buffer.write(
            f"{date_string}: empty={df.empty} rows={len(df)}\n".encode("utf-8")
        )
    except Exception as error:
        sys.stdout.buffer.write(
            f"{date_string}: ERROR {error}\n".encode("utf-8")
        )