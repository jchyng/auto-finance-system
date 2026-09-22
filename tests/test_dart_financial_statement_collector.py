"""
DART 재무제표 수집기 단위 테스트
"""

import pytest
from pathlib import Path

from src.collectors.dart_financial_statement_collector import (
    collect_normalized_financial_statements,
    load_financial_statements_from_fixture,
    get_dart_api_key_from_environment,
    get_fixture_sample_data_description,
    parse_corporation_code_mapping_from_corp_code_xml,
    fetch_corporation_code_from_dart,
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

def test_fixture_sample_data_description_declares_approximation():
    """G2(b): fixture가 공시 기반 샘플/근사 데이터임을 명시하는지 검증"""
    description = get_fixture_sample_data_description()

    assert "샘플/근사" in description
    assert "실측" in description


def test_parse_corporation_code_mapping_from_corp_code_xml():
    """G4: corpCode.xml 파싱으로 종목코드→기업코드 매핑이 복원되는지 검증"""
    sample_xml_bytes = (
        b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        b"<result><list>"
        b"<corp_code>00126380</corp_code><stock_code>005930</stock_code>"
        b"</list><list>"
        b"<corp_code>00164779</corp_code><stock_code>005380</stock_code>"
        b"</list><list>"
        b"<corp_code>00115912</corp_code><stock_code></stock_code>"
        b"</list></result>"
    )

    mapping = parse_corporation_code_mapping_from_corp_code_xml(sample_xml_bytes)

    assert mapping == {"005930": "00126380", "005380": "00164779"}


def test_fetch_corporation_code_falls_back_to_hardcoded_mapping_without_network(
    monkeypatch,
):
    """G4: corpCode.xml 다운로드 실패 시 검증된 하드코딩 매핑으로 폴백"""
    import src.collectors.dart_financial_statement_collector as dart_collector_module

    def raise_network_error(api_key: str) -> bytes:
        raise RuntimeError("network unavailable in test")

    monkeypatch.setattr(
        dart_collector_module,
        "download_corp_code_xml_bytes_from_dart",
        raise_network_error,
    )

    assert (
        fetch_corporation_code_from_dart("005930", "TEST_KEY") == "00126380"
    )
    assert fetch_corporation_code_from_dart("999999", "TEST_KEY") is None


    api_key = get_dart_api_key_from_environment()
    # API Key가 설정되어 있지 않아도 테스트는 통과해야 함
    assert api_key is None or isinstance(api_key, str)
