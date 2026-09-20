"""
KRX 데이터 수집기 단위 테스트
"""

import pytest
from pathlib import Path

from src.collectors.krx_stock_price_collector import (
    collect_stock_price_and_market_cap,
    load_stock_price_from_fixture,
)
from src.collectors.krx_industry_benchmark_collector import (
    collect_industry_benchmark_data,
    load_industry_benchmark_from_fixture,
)
from src.models.financial_statement_models import (
    StockPriceAndMarketCapData,
    IndustryBenchmarkData,
)


def test_stock_price_fixture_samsung_electronics():
    """삼성전자 주가 데이터 fixture 로드 검증"""
    price_data = collect_stock_price_and_market_cap(
        stock_code="005930",
        use_fixture_fallback=True
    )
    
    assert isinstance(price_data, StockPriceAndMarketCapData)
    assert price_data.stock_code == "005930"
    assert price_data.company_name == "삼성전자"
    assert price_data.closing_price_krw == 72000
    assert price_data.market_capitalization_krw == 429824400000000
    assert price_data.total_shares_outstanding == 5969782550
    assert price_data.base_trading_date == "2024-03-29"
    assert price_data.data_source_name == "KRX 정보데이터시스템"


def test_stock_price_fixture_hyundai_motor():
    """현대자동차 주가 데이터 fixture 로드 검증"""
    price_data = collect_stock_price_and_market_cap(
        stock_code="005380",
        use_fixture_fallback=True
    )
    
    assert isinstance(price_data, StockPriceAndMarketCapData)
    assert price_data.stock_code == "005380"
    assert price_data.company_name == "현대자동차"


def test_stock_price_fixture_shinhan_financial():
    """신한지주 주가 데이터 fixture 로드 검증"""
    price_data = collect_stock_price_and_market_cap(
        stock_code="055550",
        use_fixture_fallback=True
    )
    
    assert isinstance(price_data, StockPriceAndMarketCapData)
    assert price_data.stock_code == "055550"
    assert price_data.company_name == "신한지주"


def test_stock_price_invalid_ticker_raises_error():
    """존재하지 않는 종목코드는 에러 발생"""
    with pytest.raises(ValueError, match="주가 데이터 수집 실패"):
        collect_stock_price_and_market_cap(
            stock_code="999999",
            use_fixture_fallback=True
        )


def test_industry_benchmark_fixture_samsung_electronics():
    """삼성전자 업종 벤치마크 fixture 로드 검증"""
    benchmark = collect_industry_benchmark_data(
        stock_code="005930",
        use_fixture_fallback=True
    )
    
    assert isinstance(benchmark, IndustryBenchmarkData)
    assert benchmark.industry_classification_code == "264"
    assert benchmark.industry_classification_name == "반도체와반도체장비"
    assert benchmark.average_operating_profit_margin_percentage == 6.8
    assert benchmark.average_return_on_equity_percentage == 5.2
    assert benchmark.average_debt_to_equity_ratio_percentage == 45.0
    assert benchmark.average_price_to_earnings_ratio == 24.1
    assert benchmark.average_price_to_book_ratio == 1.6
    assert benchmark.base_date == "2024-03-29"
    assert benchmark.data_source_name == "KRX 업종 지수"


def test_industry_benchmark_fixture_hyundai_motor():
    """현대자동차 업종 벤치마크 fixture 로드 검증"""
    benchmark = collect_industry_benchmark_data(
        stock_code="005380",
        use_fixture_fallback=True
    )
    
    assert isinstance(benchmark, IndustryBenchmarkData)
    assert benchmark.industry_classification_name == "자동차"


def test_industry_benchmark_fixture_shinhan_financial():
    """신한지주(금융업) 업종 벤치마크 fixture 로드 검증"""
    benchmark = collect_industry_benchmark_data(
        stock_code="055550",
        use_fixture_fallback=True
    )
    
    assert isinstance(benchmark, IndustryBenchmarkData)
    assert benchmark.industry_classification_name == "은행/금융지주"


def test_industry_benchmark_invalid_ticker_raises_error():
    """존재하지 않는 종목코드는 에러 발생"""
    with pytest.raises(ValueError, match="업종 벤치마크 데이터 수집 실패"):
        collect_industry_benchmark_data(
            stock_code="999999",
            use_fixture_fallback=True
        )


def test_load_stock_price_from_fixture_returns_none_for_unknown():
    """알 수 없는 종목코드는 None 반환"""
    result = load_stock_price_from_fixture("999999")
    assert result is None


def test_load_industry_benchmark_from_fixture_returns_none_for_unknown():
    """알 수 없는 종목코드는 None 반환"""
    result = load_industry_benchmark_from_fixture("999999")
    assert result is None
