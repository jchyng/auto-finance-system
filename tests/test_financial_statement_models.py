"""
재무제표 및 투자 지표 데이터 모델 단위 테스트
(Unit Tests for Financial Statement and Indicator Models)
"""

import json
import os
from pathlib import Path
import pytest

from src.models.financial_statement_models import (
    NormalizedFinancialStatement,
    StockPriceAndMarketCapData,
    IndustryBenchmarkData,
)
from src.models.investment_indicator_models import (
    AnnualCalculatedIndicators,
    HistoricalFiveYearAverageIndicators,
    CompanyInvestmentIndicatorsSummary,
)
from src.models.indicator_evaluation_models import (
    IndicatorEvaluationStatus,
    IndicatorCategory,
    SingleIndicatorEvaluation,
    CompleteCompanyEvaluationReport,
)


def test_load_and_parse_samsung_electronics_dart_fixture():
    """삼성전자 실제 DART 공시 원본 샘플 JSON 로드 및 모델 변환 검증"""
    fixture_path = Path(__file__).parent.parent / "data" / "fixtures" / "005930_samsung_electronics_dart_financials.json"
    assert fixture_path.exists(), f"Fixture 파일이 존재하지 않습니다: {fixture_path}"

    with open(fixture_path, "r", encoding="utf-8") as file:
        raw_data = json.load(file)

    # 1. 주가 및 시가총액 모델 검증
    price_data = StockPriceAndMarketCapData.from_dictionary(raw_data["stock_price_and_market_cap"])
    assert price_data.stock_code == "005930"
    assert price_data.company_name == "삼성전자"
    assert price_data.closing_price_krw == 72000
    assert price_data.market_capitalization_krw == 429824400000000

    # 2. 업종 벤치마크 모델 검증
    industry_benchmark = IndustryBenchmarkData.from_dictionary(raw_data["industry_benchmark"])
    assert industry_benchmark.industry_classification_name == "반도체와반도체장비"
    assert industry_benchmark.average_price_to_earnings_ratio == 24.1

    # 3. 5개년 재무제표 연속성 및 직렬화/역직렬화 검증
    annual_statements = [
        NormalizedFinancialStatement.from_dictionary(item)
        for item in raw_data["annual_financial_statements"]
    ]
    assert len(annual_statements) == 5
    years = [stmt.fiscal_year for stmt in annual_statements]
    assert years == [2019, 2020, 2021, 2022, 2023]

    # 2023년 데이터 상세 검증
    stmt_2023 = annual_statements[-1]
    assert stmt_2023.revenue_krw == 258935494000000
    assert stmt_2023.operating_income_krw == 6566976000000
    assert stmt_2023.controlling_interest_equity_krw == 354709566000000

    # 직렬화 후 복원 무결성 확인
    serialized = stmt_2023.to_dictionary()
    deserialized = NormalizedFinancialStatement.from_dictionary(serialized)
    assert stmt_2023 == deserialized


def test_load_and_parse_hyundai_motor_and_shinhan_financial_fixtures():
    """현대자동차(제조) 및 신한지주(금융업) 샘플 데이터 무결성 검증"""
    fixtures_directory = Path(__file__).parent.parent / "data" / "fixtures"

    # 현대자동차 검증
    hyundai_file = fixtures_directory / "005380_hyundai_motor_dart_financials.json"
    with open(hyundai_file, "r", encoding="utf-8") as file:
        hyundai_data = json.load(file)
    assert hyundai_data["company_name"] == "현대자동차"
    assert hyundai_data["is_financial_industry"] is False

    # 신한지주 검증 (금융업 특성: 유동자산/유동부채 None, 부채비율 1000% 이상)
    shinhan_file = fixtures_directory / "055550_shinhan_financial_dart_financials.json"
    with open(shinhan_file, "r", encoding="utf-8") as file:
        shinhan_data = json.load(file)
    assert shinhan_data["company_name"] == "신한지주"
    assert shinhan_data["is_financial_industry"] is True

    shinhan_stmt_2023 = NormalizedFinancialStatement.from_dictionary(
        shinhan_data["annual_financial_statements"][-1]
    )
    assert shinhan_stmt_2023.current_assets_krw is None
    assert shinhan_stmt_2023.current_liabilities_krw is None
    assert shinhan_stmt_2023.is_financial_industry is True


def test_investment_indicator_models_serialization():
    """15개 투자 지표 모델 직렬화 및 5년 평균 모델 무결성 검증"""
    latest_indicators = AnnualCalculatedIndicators(
        fiscal_year=2023,
        revenue_growth_rate_percentage=-14.3,
        operating_income_growth_rate_percentage=-84.9,
        operating_income_turnaround_status_note=None,
        earnings_per_share_growth_rate_percentage=-72.2,
        free_cash_flow_growth_rate_percentage=-92.1,
        operating_profit_margin_percentage=2.5,
        return_on_equity_percentage=4.1,
        return_on_assets_percentage=3.2,
        return_on_invested_capital_percentage=2.8,
        debt_to_equity_ratio_percentage=26.4,
        current_ratio_percentage=261.2,
        interest_coverage_ratio=18.2,
        is_debt_free_company=False,
        free_cash_flow_amount_krw=4200000000000,
        price_to_earnings_ratio=32.4,
        price_to_book_ratio=1.4,
        enterprise_value_to_ebitda_ratio=8.2,
    )

    five_year_averages = HistoricalFiveYearAverageIndicators(
        start_fiscal_year=2019,
        end_fiscal_year=2023,
        average_revenue_growth_rate_percentage=5.2,
        average_operating_income_growth_rate_percentage=-2.1,
        average_earnings_per_share_growth_rate_percentage=1.8,
        average_free_cash_flow_growth_rate_percentage=-5.4,
        average_operating_profit_margin_percentage=15.2,
        average_return_on_equity_percentage=11.4,
        average_return_on_assets_percentage=8.5,
        average_return_on_invested_capital_percentage=13.1,
        average_debt_to_equity_ratio_percentage=35.2,
        average_current_ratio_percentage=240.1,
        average_interest_coverage_ratio=32.5,
        average_free_cash_flow_amount_krw=15000000000000,
        average_price_to_earnings_ratio=15.8,
        average_price_to_book_ratio=1.5,
        average_enterprise_value_to_ebitda_ratio=6.5,
    )

    summary = CompanyInvestmentIndicatorsSummary(
        stock_code="005930",
        company_name="삼성전자",
        latest_fiscal_year=2023,
        latest_indicators=latest_indicators,
        historical_five_year_averages=five_year_averages,
    )

    serialized = summary.to_dictionary()
    deserialized = CompanyInvestmentIndicatorsSummary.from_dictionary(serialized)
    assert summary == deserialized
    assert deserialized.latest_indicators.revenue_growth_rate_percentage == -14.3


def test_indicator_evaluation_models_serialization():
    """지표 상태 판정 모델 및 최종 리포트 모델 직렬화 검증"""
    single_evaluation = SingleIndicatorEvaluation(
        indicator_category=IndicatorCategory.FINANCIAL_HEALTH,
        indicator_name_korean="부채비율",
        indicator_name_english="Debt to Equity Ratio",
        current_value_formatted="26.4%",
        historical_five_year_average_formatted="35.2%",
        industry_benchmark_average_formatted="100.0% 이하 권고선",
        evaluation_status=IndicatorEvaluationStatus.GOOD,
        evaluation_reason_description="부채비율(26.4%)이 법정 건전성 권고선(100% 이하)을 크게 밑돌아 매우 안정적입니다.",
        calculation_formula_description="총부채 / 총자본 * 100",
        data_source_and_base_date_description="DART 전자공시 (2023 사업연도 결산)",
    )

    full_report = CompleteCompanyEvaluationReport(
        stock_code="005930",
        company_name="삼성전자",
        industry_classification_name="반도체와반도체장비",
        fiscal_year=2023,
        closing_price_krw=72000,
        market_capitalization_krw=429824400000000,
        evaluations=[single_evaluation],
        plain_korean_summary_text="부채비율 26.4%로 재무건전성이 양호합니다.",
        financial_term_glossary_dictionary={"부채비율": "기업이 가진 자본 대비 빚의 비율입니다."},
        disclaimer_text="본 자료는 투자 참고용 객관적 자료이며 매수/매도를 추천하지 않습니다.",
    )

    serialized = full_report.to_dictionary()
    deserialized = CompleteCompanyEvaluationReport.from_dictionary(serialized)
    assert full_report == deserialized
    assert deserialized.evaluations[0].evaluation_status == IndicatorEvaluationStatus.GOOD
