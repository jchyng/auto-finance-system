"""
데이터 수집기 패키지 (Data Collectors Package)

독립적으로 실행 가능한 데이터 수집 모듈을 제공합니다.
"""

from src.collectors.dart_financial_statement_collector import (
    collect_normalized_financial_statements,
    save_financial_statements_to_json_file,
)
from src.collectors.krx_stock_price_collector import (
    collect_stock_price_and_market_cap,
    save_stock_price_to_json_file,
)
from src.collectors.krx_industry_benchmark_collector import (
    collect_industry_benchmark_data,
    save_industry_benchmark_to_json_file,
)

__all__ = [
    "collect_normalized_financial_statements",
    "save_financial_statements_to_json_file",
    "collect_stock_price_and_market_cap",
    "save_stock_price_to_json_file",
    "collect_industry_benchmark_data",
    "save_industry_benchmark_to_json_file",
]
