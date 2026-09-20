"""
DART 재무제표 수집기 단위 테스트
"""

import pytest
from pathlib import Path

from src.collectors.dart_financial_statement_collector import (
    collect_normalized_financial_statements,
    load_financial_statements_from_fixture,
    get_dart_api_key_from_environment,
)
from src.models.financial_statement_models import NormalizedFinancialStatement


def test_fixture_fallback_samsung_electronics():
    """삼성전자 fixture JSON 로드 및 NormalizedFinancialStatement 변환 검증"""
    statements = collect_normalized_financial_statements(
        stock_code="005930",
        use_fixture_fallback=True
    )
    
    assert len(statements) == 5, "5개년 재무제표가 수집되어야 함"
    assert all(isinstance(stmt, NormalizedFinancialStatement) for stmt in statements)
    
    # 연도 정렬 검증 (내림차순: 최신년도가 첫 번째)
    years = [stmt.fiscal_year for stmt in statements]
    assert years == [2023, 2022, 2021, 2020, 2019], f"연도 순서가 올바르지 않음: {years}"
    
    # 2023년 데이터 상세 검증
    stmt_2023 = statements[0]
    assert stmt_2023.stock_code == "005930"
    assert stmt_2023.company_name == "삼성전자"
    assert stmt_2023.revenue_krw == 258935494000000
    assert stmt_2023.operating_income_krw == 6566976000000
    assert stmt_2023.is_financial_industry is False


def test_fixture_fallback_hyundai_motor():
    """현대자동차 fixture JSON 로드 검증"""
    statements = collect_normalized_financial_statements(
        stock_code="005380",
        use_fixture_fallback=True
    )
    
    assert len(statements) == 5
    assert statements[0].stock_code == "005380"
    assert statements[0].company_name == "현대자동차"
    assert statements[0].is_financial_industry is False


def test_fixture_fallback_shinhan_financial():
    """신한지주(금융업) fixture JSON 로드 및 금융업 특성 검증"""
    statements = collect_normalized_financial_statements(
        stock_code="055550",
        use_fixture_fallback=True
    )
    
    assert len(statements) == 5
    assert statements[0].stock_code == "055550"
    assert statements[0].company_name == "신한지주"
    assert statements[0].is_financial_industry is True
    
    # 금융업 특성: 유동자산/유동부채 None
    assert statements[0].current_assets_krw is None
    assert statements[0].current_liabilities_krw is None


def test_invalid_stock_code_without_fixture_raises_error():
    """존재하지 않는 종목코드는 fixture도 없고 API Key도 없으면 에러 발생"""
    with pytest.raises(ValueError, match="재무제표 수집 실패"):
        collect_normalized_financial_statements(
            stock_code="999999",  # 존재하지 않는 종목코드
            use_fixture_fallback=True
        )


def test_load_financial_statements_from_fixture_returns_none_for_unknown_ticker():
    """알 수 없는 종목코드는 fixture 로드 시 None 반환"""
    result = load_financial_statements_from_fixture("999999")
    assert result is None


def test_api_key_detection():
    """환경변수에서 DART API Key 감지 테스트 (키 없어도 정상 동작)"""
    api_key = get_dart_api_key_from_environment()
    # API Key가 설정되어 있지 않아도 테스트는 통과해야 함
    assert api_key is None or isinstance(api_key, str)
