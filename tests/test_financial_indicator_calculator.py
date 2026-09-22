"""
투자지표 계산 엔진 단위 테스트
"""

import json
import pytest
from pathlib import Path

from src.engines.financial_indicator_calculator import (
    calculate_revenue_growth_rate,
    calculate_operating_income_growth_rate,
    calculate_eps_growth_rate,
    calculate_free_cash_flow,
    calculate_fcf_growth_rate,
    calculate_operating_profit_margin,
    calculate_return_on_equity,
    calculate_return_on_assets,
    calculate_return_on_invested_capital,
    calculate_debt_to_equity_ratio,
    calculate_current_ratio,
    calculate_interest_coverage_ratio,
    calculate_price_to_earnings_ratio,
    calculate_price_to_book_ratio,
    calculate_enterprise_value_to_ebitda_ratio,
    calculate_company_indicators_summary,
)
from src.models.financial_statement_models import (
    NormalizedFinancialStatement,
    StockPriceAndMarketCapData,
)


# ============================================================================
# 1. 성장성 지표 테스트
# ============================================================================

def test_calculate_revenue_growth_rate():
    """매출액 성장률 계산 테스트"""
    # 정상 케이스
    growth = calculate_revenue_growth_rate(110000000000, 100000000000)
    assert growth == 10.0
    
    # 마이너스 성장
    decline = calculate_revenue_growth_rate(90000000000, 100000000000)
    assert decline == -10.0
    
    # 전기 매출이 0 (None 반환)
    assert calculate_revenue_growth_rate(100000000000, 0) is None


def test_calculate_operating_income_growth_rate():
    """영업이익 성장률 및 특수 케이스 테스트"""
    # 정상 성장
    growth, note = calculate_operating_income_growth_rate(11000000000, 10000000000)
    assert growth == 10.0
    assert note is None
    
    # 흑자전환
    growth, note = calculate_operating_income_growth_rate(1000000000, -500000000)
    assert growth is None
    assert note == "흑자전환"
    
    # 적자지속
    growth, note = calculate_operating_income_growth_rate(-1000000000, -500000000)
    assert growth is None
    assert note == "적자지속"
    
    # 적자전환
    growth, note = calculate_operating_income_growth_rate(-1000000000, 500000000)
    assert growth is None
    assert note == "적자전환"


def test_calculate_free_cash_flow():
    """FCF 계산 테스트"""
    fcf = calculate_free_cash_flow(
        operating_cash_flow=50000000000,
        acquisition_of_tangible_assets=30000000000,
        acquisition_of_intangible_assets=5000000000
    )
    assert fcf == 15000000000
    
    # 마이너스 FCF
    negative_fcf = calculate_free_cash_flow(
        operating_cash_flow=10000000000,
        acquisition_of_tangible_assets=50000000000,
        acquisition_of_intangible_assets=5000000000
    )
    assert negative_fcf == -45000000000


def test_calculate_fcf_growth_rate():
    """FCF 성장률 계산 테스트"""
    growth = calculate_fcf_growth_rate(12000000000, 10000000000)
    assert growth == 20.0
    
    # 이전 FCF가 0 (None 반환)
    assert calculate_fcf_growth_rate(10000000000, 0) is None


# ============================================================================
# 2. 수익성 지표 테스트
# ============================================================================

def test_calculate_operating_profit_margin():
    """영업이익률 계산 테스트"""
    margin = calculate_operating_profit_margin(10000000000, 100000000000)
    assert margin == 10.0
    
    # 마이너스 이익률
    negative_margin = calculate_operating_profit_margin(-5000000000, 100000000000)
    assert negative_margin == -5.0
    
    # 매출이 0 (None 반환)
    assert calculate_operating_profit_margin(10000000000, 0) is None


def test_calculate_return_on_equity():
    """ROE 계산 테스트"""
    roe = calculate_return_on_equity(
        net_income=10000000000,
        beginning_equity=90000000000,
        ending_equity=110000000000
    )
    assert roe == 10.0
    
    # 평균 자기자본이 0 (None 반환)
    assert calculate_return_on_equity(10000000000, 0, 0) is None


def test_calculate_return_on_assets():
    """ROA 계산 테스트"""
    roa = calculate_return_on_assets(
        net_income=10000000000,
        beginning_assets=190000000000,
        ending_assets=210000000000
    )
    assert roa == 5.0
    
    # 평균 자산이 0 (None 반환)
    assert calculate_return_on_assets(10000000000, 0, 0) is None


def test_calculate_return_on_invested_capital():
    """ROIC 계산 테스트"""
    roic = calculate_return_on_invested_capital(
        operating_income=20000000000,
        income_tax_expense=4000000000,
        profit_before_tax=20000000000,
        total_borrowings=30000000000,
        equity=100000000000,
        cash=10000000000,
        is_financial_industry=False
    )
    # NOPAT = 20B * (1 - 0.2) = 16B
    # IC = (30B - 10B) + 100B = 120B
    # ROIC = 16B / 120B * 100 = 13.3%
    assert roic == 13.3
    
    # 비정상 실효세율 (20% 사용)
    roic_abnormal = calculate_return_on_invested_capital(
        operating_income=20000000000,
        income_tax_expense=-5000000000,  # 비정상
        profit_before_tax=20000000000,
        total_borrowings=30000000000,
        equity=100000000000,
        cash=10000000000,
        is_financial_industry=False
    )
    assert roic_abnormal == 13.3

    # 금융업 (업종 특성상 None 반환)
    roic_financial = calculate_return_on_invested_capital(
        operating_income=20000000000,
        income_tax_expense=4000000000,
        profit_before_tax=20000000000,
        total_borrowings=30000000000,
        equity=100000000000,
        cash=10000000000,
        is_financial_industry=True
    )
    assert roic_financial is None


# ============================================================================
# 3. 재무건전성 지표 테스트
# ============================================================================

def test_calculate_debt_to_equity_ratio():
    """부채비율 계산 테스트"""
    # 일반 제조업
    debt_ratio = calculate_debt_to_equity_ratio(
        total_liabilities=50000000000,
        equity=100000000000,
        is_financial_industry=False
    )
    assert debt_ratio == 50.0
    
    # 금융업 (None 반환)
    assert calculate_debt_to_equity_ratio(50000000000, 100000000000, True) is None
    
    # 자본이 0 (None 반환)
    assert calculate_debt_to_equity_ratio(50000000000, 0, False) is None


def test_calculate_current_ratio():
    """유동비율 계산 테스트"""
    # 일반 제조업
    current_ratio = calculate_current_ratio(
        current_assets=150000000000,
        current_liabilities=100000000000,
        is_financial_industry=False
    )
    assert current_ratio == 150.0
    
    # 금융업 (None 반환)
    assert calculate_current_ratio(150000000000, 100000000000, True) is None
    
    # 유동자산/부채가 None (None 반환)
    assert calculate_current_ratio(None, 100000000000, False) is None
    assert calculate_current_ratio(150000000000, None, False) is None


def test_calculate_interest_coverage_ratio():
    """이자보상배율 계산 테스트"""
    # 정상 케이스
    coverage, is_debt_free = calculate_interest_coverage_ratio(
        operating_income=10000000000,
        interest_expense=1000000000,
        is_financial_industry=False
    )
    assert coverage == 10.0
    assert is_debt_free is False
    
    # 무차입 기업
    coverage, is_debt_free = calculate_interest_coverage_ratio(
        operating_income=10000000000,
        interest_expense=0,
        is_financial_industry=False
    )
    assert coverage is None
    assert is_debt_free is True

    # 금융업 (이자비용이 본업의 원가이므로 배율/무차입 판정 불가)
    coverage, is_debt_free = calculate_interest_coverage_ratio(
        operating_income=10000000000,
        interest_expense=1000000000,
        is_financial_industry=True
    )
    assert coverage is None
    assert is_debt_free is False


# ============================================================================
# 4. 밸류에이션 지표 테스트
# ============================================================================

def test_calculate_price_to_earnings_ratio():
    """PER 계산 테스트"""
    per = calculate_price_to_earnings_ratio(
        market_capitalization=100000000000000,
        net_income=10000000000000
    )
    assert per == 10.0
    
    # 적자 (None 반환)
    assert calculate_price_to_earnings_ratio(100000000000000, -1000000000000) is None
    assert calculate_price_to_earnings_ratio(100000000000000, 0) is None


def test_calculate_price_to_book_ratio():
    """PBR 계산 테스트"""
    pbr = calculate_price_to_book_ratio(
        market_capitalization=100000000000000,
        equity=50000000000000
    )
    assert pbr == 2.0
    
    # 자본잠식 (None 반환)
    assert calculate_price_to_book_ratio(100000000000000, -1000000000000) is None
    assert calculate_price_to_book_ratio(100000000000000, 0) is None


def test_calculate_enterprise_value_to_ebitda_ratio():
    """EV/EBITDA 계산 테스트"""
    # 일반 제조업
    ev_ebitda = calculate_enterprise_value_to_ebitda_ratio(
        market_capitalization=100000000000000,
        total_borrowings=20000000000000,
        cash=10000000000000,
        operating_income=15000000000000,
        depreciation=3000000000000,
        amortization=1000000000000,
        is_financial_industry=False
    )
    # EV = 100T + 20T - 10T = 110T
    # EBITDA = 15T + 3T + 1T = 19T
    # EV/EBITDA = 110T / 19T = 5.8
    assert ev_ebitda == 5.8
    
    # 금융업 (None 반환)
    assert calculate_enterprise_value_to_ebitda_ratio(
        100000000000000, 20000000000000, 10000000000000,
        15000000000000, 3000000000000, 1000000000000,
        True
    ) is None
    
    # EBITDA가 0 이하 (None 반환)
    assert calculate_enterprise_value_to_ebitda_ratio(
        100000000000000, 20000000000000, 10000000000000,
        -15000000000000, 3000000000000, 1000000000000,
        False
    ) is None


# ============================================================================
# 통합 테스트
# ============================================================================

def test_calculate_company_indicators_summary_samsung():
    """삼성전자 fixture 기반 통합 계산 테스트"""
    # Fixture 로드
    fixture_path = Path(__file__).parent.parent / "data" / "fixtures" / "005930_samsung_electronics_dart_financials.json"
    
    with open(fixture_path, "r", encoding="utf-8") as file:
        fixture_data = json.load(file)
    
    # 재무제표 변환
    statements_list = fixture_data.get("annual_financial_statements", [])
    financial_statements = [
        NormalizedFinancialStatement.from_dictionary(stmt)
        for stmt in statements_list
    ]
    
    # 주가 데이터 변환
    price_data = StockPriceAndMarketCapData.from_dictionary(
        fixture_data.get("stock_price_and_market_cap")
    )
    
    # 통합 계산
    summary = calculate_company_indicators_summary(financial_statements, price_data)
    
    assert summary.stock_code == "005930"
    assert summary.company_name == "삼성전자"
    assert summary.latest_fiscal_year == 2023
    
    # 최신 지표 검증
    latest = summary.latest_indicators
    assert latest.fiscal_year == 2023
    assert latest.revenue_growth_rate_percentage is not None
    assert latest.operating_profit_margin_percentage is not None
    assert latest.return_on_equity_percentage is not None
    assert latest.debt_to_equity_ratio_percentage is not None
    assert latest.price_to_earnings_ratio is not None
    assert latest.is_debt_free_company is False
    
    # 5개년 평균 검증
    averages = summary.historical_five_year_averages
    assert averages.start_fiscal_year == 2019
    assert averages.end_fiscal_year == 2023
    assert averages.average_revenue_growth_rate_percentage is not None
    assert averages.average_operating_profit_margin_percentage is not None


def test_calculate_company_indicators_summary_shinhan():
    """신한지주(금융업) fixture 기반 통합 계산 테스트"""
    fixture_path = Path(__file__).parent.parent / "data" / "fixtures" / "055550_shinhan_financial_dart_financials.json"
    
    with open(fixture_path, "r", encoding="utf-8") as file:
        fixture_data = json.load(file)
    
    financial_statements = [
        NormalizedFinancialStatement.from_dictionary(stmt)
        for stmt in fixture_data.get("annual_financial_statements", [])
    ]
    
    price_data = StockPriceAndMarketCapData.from_dictionary(
        fixture_data.get("stock_price_and_market_cap")
    )
    
    summary = calculate_company_indicators_summary(financial_statements, price_data)
    
    assert summary.stock_code == "055550"
    assert summary.company_name == "신한지주"
    
    # 금융업 특성 검증
    latest = summary.latest_indicators
    assert latest.debt_to_equity_ratio_percentage is None, "금융업은 부채비율이 None이어야 함"
    assert latest.current_ratio_percentage is None, "금융업은 유동비율이 None이어야 함"
    assert latest.enterprise_value_to_ebitda_ratio is None, "금융업은 EV/EBITDA가 None이어야 함"
    assert latest.return_on_invested_capital_percentage is None, "금융업은 ROIC가 None이어야 함"
    assert latest.interest_coverage_ratio is None, "금융업은 이자보상배율이 None이어야 함"
    assert summary.is_financial_industry is True
