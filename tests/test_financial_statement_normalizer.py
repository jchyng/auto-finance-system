"""
재무제표 정제기 단위 테스트
"""

import json
import pytest
from pathlib import Path

from src.normalizers.financial_statement_normalizer import (
    normalize_dart_financial_statement,
    normalize_multiple_years_from_dart_response,
    find_account_value_by_name,
    find_basic_eps_value,
    ACCOUNT_NAME_MAPPING,
)
from src.models.financial_statement_models import NormalizedFinancialStatement


def test_find_basic_eps_value():
    accounts = [{
        "sj_div": "CIS",
        "account_nm": "기본주당이익",
        "thstrm_amount": "1,250",
        "fiscal_year": 2023,
    }]
    assert find_basic_eps_value(accounts, 2023) == 1250.0


def test_account_name_mapping_coverage():
    """계정과목 매핑 테이블이 주요 항목을 포함하는지 검증"""
    required_accounts = [
        "매출액", "영업이익", "당기순이익", "지배기업소유주지분순이익",
        "자산총계", "부채총계", "지배기업소유주지분",
        "유동자산", "유동부채", "단기차입금", "장기차입금",
        "현금및현금성자산", "영업활동현금흐름"
    ]
    
    for account in required_accounts:
        assert account in ACCOUNT_NAME_MAPPING, f"{account}이 매핑 테이블에 없습니다"
        assert len(ACCOUNT_NAME_MAPPING[account]) > 0, f"{account}의 매핑 목록이 비어있습니다"


def test_find_account_value_by_name():
    """계정과목명 검색 함수 테스트"""
    mock_accounts = [
        {"account_nm": "매출액", "thstrm_amount": "100,000,000,000"},
        {"account_nm": "영업이익", "thstrm_amount": "10,000,000,000"},
        {"account_nm": "자산총계", "thstrm_amount": "500,000,000,000"}
    ]
    
    revenue = find_account_value_by_name(mock_accounts, "매출액", 2023)
    assert revenue == 100000000000
    
    operating_income = find_account_value_by_name(mock_accounts, "영업이익", 2023)
    assert operating_income == 10000000000
    
    # 존재하지 않는 계정과목
    not_found = find_account_value_by_name(mock_accounts, "존재하지않는계정", 2023)
    assert not_found is None


def test_normalize_dart_financial_statement_basic():
    """기본 정제 로직 테스트 (제조업)"""
    mock_accounts = [
        {"account_nm": "매출액", "thstrm_amount": "258935494000000"},
        {"account_nm": "영업이익", "thstrm_amount": "6566976000000"},
        {"account_nm": "지배기업의 소유주에게 귀속되는 당기순이익", "thstrm_amount": "14472674000000"},
        {"sj_div": "CIS", "account_nm": "기본주당이익", "thstrm_amount": "10000"},
        {"account_nm": "법인세비용", "thstrm_amount": "4504859000000"},
        {"account_nm": "자산총계", "thstrm_amount": "455905984000000"},
        {"account_nm": "부채총계", "thstrm_amount": "92228145000000"},
        {"account_nm": "지배기업의 소유주에게 귀속되는 자본", "thstrm_amount": "354709566000000"},
        {"account_nm": "유동자산", "thstrm_amount": "218846052000000"},
        {"account_nm": "유동부채", "thstrm_amount": "83858829000000"},
        {"account_nm": "단기차입금", "thstrm_amount": "15200000000000"},
        {"account_nm": "장기차입금", "thstrm_amount": "3500000000000"},
        {"account_nm": "현금및현금성자산", "thstrm_amount": "69081200000000"},
    ]
    
    result = normalize_dart_financial_statement(
        stock_code="005930",
        company_name="삼성전자",
        fiscal_year=2023,
        dart_raw_accounts=mock_accounts,
        is_financial_industry=False
    )
    
    assert isinstance(result, NormalizedFinancialStatement)
    assert result.stock_code == "005930"
    assert result.company_name == "삼성전자"
    assert result.fiscal_year == 2023
    assert result.revenue_krw == 258935494000000
    assert result.operating_income_krw == 6566976000000
    assert result.controlling_interest_net_income_krw == 14472674000000
    assert result.adjusted_basic_shares_outstanding == 1447267400
    assert result.total_assets_krw == 455905984000000
    assert result.total_liabilities_krw == 92228145000000
    assert result.controlling_interest_equity_krw == 354709566000000
    assert result.current_assets_krw == 218846052000000
    assert result.current_liabilities_krw == 83858829000000
    assert result.is_financial_industry is False


def test_normalize_dart_financial_statement_financial_industry():
    """금융업 정제 로직 테스트 (유동자산/부채 None)"""
    mock_accounts = [
        {"account_nm": "영업수익", "thstrm_amount": "10000000000000"},
        {"account_nm": "영업이익", "thstrm_amount": "2000000000000"},
        {"account_nm": "당기순이익", "thstrm_amount": "1500000000000"},
        {"account_nm": "자산총계", "thstrm_amount": "500000000000000"},
        {"account_nm": "부채총계", "thstrm_amount": "450000000000000"},
        {"account_nm": "자본총계", "thstrm_amount": "50000000000000"},
    ]
    
    result = normalize_dart_financial_statement(
        stock_code="055550",
        company_name="신한지주",
        fiscal_year=2023,
        dart_raw_accounts=mock_accounts,
        is_financial_industry=True
    )
    
    assert result.is_financial_industry is True
    assert result.current_assets_krw is None, "금융업은 유동자산이 None이어야 함"
    assert result.current_liabilities_krw is None, "금융업은 유동부채가 None이어야 함"
    assert result.revenue_krw == 10000000000000
    assert result.total_assets_krw == 500000000000000


def test_normalize_dart_financial_statement_missing_required_account():
    """필수 계정과목 누락 시 에러 발생 검증"""
    incomplete_accounts = [
        {"account_nm": "매출액", "thstrm_amount": "100000000000"},
        # 영업이익 누락
    ]
    
    with pytest.raises(ValueError, match="필수 계정과목 누락"):
        normalize_dart_financial_statement(
            stock_code="999999",
            company_name="테스트",
            fiscal_year=2023,
            dart_raw_accounts=incomplete_accounts,
            is_financial_industry=False
        )


def test_normalize_multiple_years_from_fixture_samsung():
    """삼성전자 fixture 전체 연도 정제 테스트"""
    fixture_path = Path(__file__).parent.parent / "data" / "fixtures" / "005930_samsung_electronics_dart_financials.json"
    
    with open(fixture_path, "r", encoding="utf-8") as file:
        fixture_data = json.load(file)
    
    normalized_statements = normalize_multiple_years_from_dart_response(fixture_data)
    
    assert len(normalized_statements) == 5, "5개년 재무제표가 정제되어야 함"
    assert all(isinstance(stmt, NormalizedFinancialStatement) for stmt in normalized_statements)
    
    # 연도 검증
    years = [stmt.fiscal_year for stmt in normalized_statements]
    assert years == [2023, 2022, 2021, 2020, 2019]
    
    # 2023년 데이터 상세 검증
    stmt_2023 = normalized_statements[0]
    assert stmt_2023.stock_code == "005930"
    assert stmt_2023.company_name == "삼성전자"
    assert stmt_2023.revenue_krw == 258935494000000
    assert stmt_2023.operating_income_krw == 6566976000000
    assert stmt_2023.is_financial_industry is False


def test_normalize_multiple_years_from_fixture_hyundai():
    """현대자동차 fixture 정제 테스트"""
    fixture_path = Path(__file__).parent.parent / "data" / "fixtures" / "005380_hyundai_motor_dart_financials.json"
    
    with open(fixture_path, "r", encoding="utf-8") as file:
        fixture_data = json.load(file)
    
    normalized_statements = normalize_multiple_years_from_dart_response(fixture_data)
    
    assert len(normalized_statements) == 5
    assert normalized_statements[0].stock_code == "005380"
    assert normalized_statements[0].company_name == "현대자동차"
    assert normalized_statements[0].is_financial_industry is False


def test_normalize_multiple_years_from_fixture_shinhan():
    """신한지주(금융업) fixture 정제 테스트"""
    fixture_path = Path(__file__).parent.parent / "data" / "fixtures" / "055550_shinhan_financial_dart_financials.json"
    
    with open(fixture_path, "r", encoding="utf-8") as file:
        fixture_data = json.load(file)
    
    normalized_statements = normalize_multiple_years_from_dart_response(fixture_data)
    
    assert len(normalized_statements) == 5
    assert normalized_statements[0].stock_code == "055550"
    assert normalized_statements[0].company_name == "신한지주"
    assert normalized_statements[0].is_financial_industry is True
    
    # 금융업 특성 검증
    assert normalized_statements[0].current_assets_krw is None
    assert normalized_statements[0].current_liabilities_krw is None
