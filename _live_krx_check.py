from pathlib import Path
import sys

project_root = Path(r"C:\Users\jcy03\dev")
sys.path.insert(0, str(project_root))

from src.collectors.krx_industry_benchmark_collector import (
    fetch_industry_benchmark_from_krx,
)

result = fetch_industry_benchmark_from_krx(
    "264", "반도체와반도체장비", "20240329"
)
if result is None:
    print("RESULT=None (fixture fallback 대상)")
else:
    sys.stdout.buffer.write(
        ("RESULT ok: "
         f"PER={result.average_price_to_earnings_ratio} "
         f"PBR={result.average_price_to_book_ratio} "
         f"source={result.data_source_name}\n").encode("utf-8")
    )