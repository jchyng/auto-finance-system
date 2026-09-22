"""
Step 8. 실제 기업 3종 종합 검증 테스트 (Real Company Cross-Verification)

삼성전자(005930)·현대자동차(005380)·신한지주(055550) 3개 기업에 대해
파이프라인이 산출한 투자지표를 "원본 공시 fixture 값"으로부터 순수 사칙연산으로
독립 재계산하여 100% 일치하는지 교차 검증하고, 시스템 원칙 준수 여부를 검증합니다.

[검증 항목]
1. 지표 재현성: 원본 fixture 값 -> 독립 재계산값 == 파이프라인 산출값 (15개 지표 + 5개년 평균)
2. 기준값 고정: 3개 기업 15개 지표의 확정 기준값(회귀 방지 baseline) 일치
3. 금융업 예외: 신한지주는 부채비율/유동비율/이자보상배율/ROIC/EV-EBITDA가 `판단불가`,
   일반 제조업(삼성전자/현대자동차)은 동일 지표가 정상 산출
4. 규칙 1 (투자 권유 금지): 리포트 본문에 금지 표현 0건
5. 리포트 무결성: 15개 지표 명칭·계산공식·데이터 출처 표기

[준수 규칙]
- 규칙 3 (모듈 독립성): 파이프라인 공개 인터페이스만 사용하여 검증
- 규칙 6 (명확한 명명): 축약어 없는 완전한 함수명 및 변수명 사용
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from src.investment_analysis_pipeline import run_investment_analysis_pipeline
from src.explainers.financial_report_explainer import check_prohibited_expressions
from src.models.indicator_evaluation_models import IndicatorEvaluationStatus


PROJECT_ROOT_DIRECTORY = Path(__file__).parent.parent
FIXTURE_DIRECTORY = PROJECT_ROOT_DIRECTORY / "data" / "fixtures"

# 파이프라인/엔진과 동일하게 소수점 1자리로 반올림하므로,
# 반올림 경계 오차만 허용하기 위한 아주 작은 허용 오차
INDICATOR_COMPARISON_TOLERANCE = 0.05

# 15개 지표의 한국어 명칭 (리포트 표기와 동일)
ALL_FIFTEEN_INDICATOR_KOREAN_NAMES = [
    "매출액 성장률",
    "영업이익 성장률",
    "EPS 성장률",
    "FCF 성장률",
    "영업이익률",
    "ROE",
    "ROA",
    "ROIC",
    "부채비율",
    "유동비율",
    "이자보상배율",
    "잉여현금흐름(FCF)",
    "PER",
    "PBR",
    "EV/EBITDA",
]

# 금융업(은행/금융지주)에 적용이 부적합하여 `판단불가(업종 특성)` 처리되는 5개 지표
FINANCIAL_INDUSTRY_EXCEPTION_INDICATOR_KOREAN_NAMES = [
    "부채비율",
    "유동비율",
    "이자보상배율",
    "ROIC",
    "EV/EBITDA",
]

# Step 8 검증 대상 3개 기업 정의
# (기준값은 원본 fixture로부터 독립 재계산하여 수동 검증을 완료한 값)
REAL_COMPANY_VERIFICATION_TARGETS = [
    {
        "stock_code": "005930",
        "company_name": "삼성전자",
        "industry_profile": "일반 제조/다운사이클",
        "fixture_filename": "005930_samsung_electronics_dart_financials.json",
        "is_financial_industry": False,
        "expected_latest_indicators": {
            "revenue_growth_rate_percentage": -14.3,
            "operating_income_growth_rate_percentage": -84.9,
            "earnings_per_share_growth_rate_percentage": -73.6,
            "free_cash_flow_growth_rate_percentage": -230.4,
            "operating_profit_margin_percentage": 2.5,
            "return_on_equity_percentage": 4.1,
            "return_on_assets_percentage": 3.2,
            "return_on_invested_capital_percentage": 1.3,
            "debt_to_equity_ratio_percentage": 26.0,
            "current_ratio_percentage": 261.0,
            "interest_coverage_ratio": 6.9,
            "free_cash_flow_amount_krw": -12184384000000,
            "price_to_earnings_ratio": 29.7,
            "price_to_book_ratio": 1.2,
            "enterprise_value_to_ebitda_ratio": 8.4,
        },
        "expected_five_year_averages": {
            "average_revenue_growth_rate_percentage": 3.7,
            "average_operating_profit_margin_percentage": 12.5,
            "average_return_on_equity_percentage": 11.3,
            "average_debt_to_equity_ratio_percentage": 33.5,
            "average_free_cash_flow_amount_krw": 10164055000000,
            "average_price_to_earnings_ratio": 17.0,
        },
    },
    {
        "stock_code": "005380",
        "company_name": "현대자동차",
        "industry_profile": "안정적 수익 제조",
        "fixture_filename": "005380_hyundai_motor_dart_financials.json",
        "is_financial_industry": False,
        "expected_latest_indicators": {
            "revenue_growth_rate_percentage": 14.1,
            "operating_income_growth_rate_percentage": 54.0,
            "earnings_per_share_growth_rate_percentage": 53.7,
            "free_cash_flow_growth_rate_percentage": 18.6,
            "operating_profit_margin_percentage": 9.3,
            "return_on_equity_percentage": 12.2,
            "return_on_assets_percentage": 4.6,
            "return_on_invested_capital_percentage": 5.7,
            "debt_to_equity_ratio_percentage": 159.7,
            "current_ratio_percentage": 145.6,
            "interest_coverage_ratio": 6.3,
            "free_cash_flow_amount_krw": 10200000000000,
            "price_to_earnings_ratio": 4.1,
            "price_to_book_ratio": 0.5,
            "enterprise_value_to_ebitda_ratio": 6.5,
        },
        "expected_five_year_averages": {
            "average_revenue_growth_rate_percentage": 11.7,
            "average_operating_profit_margin_percentage": 5.5,
            "average_return_on_equity_percentage": 7.7,
            "average_debt_to_equity_ratio_percentage": 168.9,
            "average_free_cash_flow_amount_krw": 5920000000000,
            "average_price_to_earnings_ratio": 12.5,
        },
    },
    {
        "stock_code": "055550",
        "company_name": "신한지주",
        "industry_profile": "금융업 예외 처리",
        "fixture_filename": "055550_shinhan_financial_dart_financials.json",
        "is_financial_industry": True,
        "expected_latest_indicators": {
            "revenue_growth_rate_percentage": 13.7,
            "operating_income_growth_rate_percentage": -2.4,
            "earnings_per_share_growth_rate_percentage": -5.9,
            "free_cash_flow_growth_rate_percentage": 7.1,
            "operating_profit_margin_percentage": 10.8,
            "return_on_equity_percentage": 8.4,
            "return_on_assets_percentage": 0.6,
            "return_on_invested_capital_percentage": None,
            "debt_to_equity_ratio_percentage": None,
            "current_ratio_percentage": None,
            "interest_coverage_ratio": None,
            "free_cash_flow_amount_krw": 18500000000000,
            "price_to_earnings_ratio": 5.6,
            "price_to_book_ratio": 0.5,
            "enterprise_value_to_ebitda_ratio": None,
        },
        "expected_five_year_averages": {
            "average_revenue_growth_rate_percentage": 9.3,
            "average_operating_profit_margin_percentage": 13.3,
            "average_return_on_equity_percentage": 8.6,
            "average_debt_to_equity_ratio_percentage": None,
            "average_free_cash_flow_amount_krw": 15362000000000,
            "average_price_to_earnings_ratio": 6.3,
        },
    },
]


# ============================================================================
# 1. 원본 fixture 기반 독립 재계산 (Independent Recomputation)
# ============================================================================

def load_fixture_data_for_target(target: Dict[str, Any]) -> Dict[str, Any]:
    """검증 대상 기업의 원본 공시 fixture JSON을 로드합니다."""
    fixture_path = FIXTURE_DIRECTORY / target["fixture_filename"]
    with open(fixture_path, "r", encoding="utf-8") as file:
        return json.load(file)


def calculate_effective_tax_rate_from_fixture(statement: Dict[str, Any]) -> float:
    """원본 재무제표 값으로 실효세율을 계산합니다 (비정상 시 법정세율 20%)."""
    income_tax_expense = statement["income_tax_expense_krw"]
    profit_before_tax = statement["profit_before_tax_krw"]

    if profit_before_tax != 0 and income_tax_expense >= 0:
        candidate_tax_rate = income_tax_expense / profit_before_tax
        if 0 <= candidate_tax_rate <= 1:
            return candidate_tax_rate

    return 0.2


def calculate_free_cash_flow_amount_from_fixture(statement: Dict[str, Any]) -> int:
    """원본 재무제표 값으로 FCF 절대액을 계산합니다."""
    return (
        statement["operating_cash_flow_krw"]
        - statement["acquisition_of_tangible_assets_krw"]
        - statement["acquisition_of_intangible_assets_krw"]
    )


def round_to_one_decimal(value: float) -> float:
    """엔진과 동일한 반올림 규칙(소수점 1자리)을 적용합니다."""
    return round(value, 1)


def recompute_annual_indicators_from_fixture(
    current_statement: Dict[str, Any],
    previous_statement: Optional[Dict[str, Any]],
    stock_price_and_market_cap: Dict[str, Any],
    is_financial_industry: bool,
) -> Dict[str, Any]:
    """
    원본 공시 값만으로 한 사업연도의 15개 지표를 순수 사칙연산으로 재계산합니다.
    (계산 엔진의 공식과 동일한 정의를 독립적으로 구현)
    """
    market_capitalization_krw = stock_price_and_market_cap["market_capitalization_krw"]
    total_borrowings_krw = (
        current_statement["short_term_borrowings_krw"]
        + current_statement["long_term_borrowings_krw"]
    )
    current_free_cash_flow_krw = calculate_free_cash_flow_amount_from_fixture(current_statement)

    effective_tax_rate = calculate_effective_tax_rate_from_fixture(current_statement)
    net_operating_profit_after_tax_krw = (
        current_statement["operating_income_krw"] * (1 - effective_tax_rate)
    )
    invested_capital_krw = (
        total_borrowings_krw
        - current_statement["cash_and_cash_equivalents_krw"]
        + current_statement["controlling_interest_equity_krw"]
    )

    recomputed_indicators: Dict[str, Any] = {}

    # 성장성 (전기 데이터가 있어야 계산 가능)
    recomputed_indicators["revenue_growth_rate_percentage"] = None
    recomputed_indicators["operating_income_growth_rate_percentage"] = None
    recomputed_indicators["earnings_per_share_growth_rate_percentage"] = None
    recomputed_indicators["free_cash_flow_growth_rate_percentage"] = None

    # 수익성
    recomputed_indicators["operating_profit_margin_percentage"] = round_to_one_decimal(
        current_statement["operating_income_krw"] / current_statement["revenue_krw"] * 100
    )
    recomputed_indicators["return_on_equity_percentage"] = None
    recomputed_indicators["return_on_assets_percentage"] = None
    recomputed_indicators["return_on_invested_capital_percentage"] = (
        None
        if is_financial_industry
        else round_to_one_decimal(net_operating_profit_after_tax_krw / invested_capital_krw * 100)
    )

    # 재무건전성 (금융업 예외 처리 포함)
    recomputed_indicators["debt_to_equity_ratio_percentage"] = (
        None
        if is_financial_industry
        else round_to_one_decimal(
            current_statement["total_liabilities_krw"]
            / current_statement["controlling_interest_equity_krw"]
            * 100
        )
    )
    is_current_ratio_applicable = (
        not is_financial_industry
        and current_statement["current_assets_krw"] is not None
        and current_statement["current_liabilities_krw"] is not None
    )
    recomputed_indicators["current_ratio_percentage"] = (
        round_to_one_decimal(
            current_statement["current_assets_krw"]
            / current_statement["current_liabilities_krw"] * 100
        )
        if is_current_ratio_applicable
        else None
    )
    recomputed_indicators["interest_coverage_ratio"] = (
        None
        if is_financial_industry or current_statement["interest_expense_krw"] == 0
        else round_to_one_decimal(
            current_statement["operating_income_krw"] / current_statement["interest_expense_krw"]
        )
    )
    recomputed_indicators["free_cash_flow_amount_krw"] = current_free_cash_flow_krw

    # 밸류에이션 (금융업은 EV/EBITDA 판단불가)
    recomputed_indicators["price_to_earnings_ratio"] = (
        round_to_one_decimal(
            market_capitalization_krw / current_statement["controlling_interest_net_income_krw"]
        )
        if current_statement["controlling_interest_net_income_krw"] > 0
        else None
    )
    recomputed_indicators["price_to_book_ratio"] = (
        round_to_one_decimal(
            market_capitalization_krw / current_statement["controlling_interest_equity_krw"]
        )
        if current_statement["controlling_interest_equity_krw"] > 0
        else None
    )
    ebitda_krw = (
        current_statement["operating_income_krw"]
        + current_statement["tangible_asset_depreciation_krw"]
        + current_statement["intangible_asset_amortization_krw"]
    )
    enterprise_value_krw = (
        market_capitalization_krw
        + total_borrowings_krw
        - current_statement["cash_and_cash_equivalents_krw"]
    )
    recomputed_indicators["enterprise_value_to_ebitda_ratio"] = (
        round_to_one_decimal(enterprise_value_krw / ebitda_krw)
        if not is_financial_industry and ebitda_krw > 0
        else None
    )

    # 전기 데이터가 있는 경우 성장성 및 평균자본 지표 계산
    if previous_statement is not None:
        previous_free_cash_flow_krw = calculate_free_cash_flow_amount_from_fixture(
            previous_statement
        )
        recomputed_indicators["revenue_growth_rate_percentage"] = round_to_one_decimal(
            (current_statement["revenue_krw"] - previous_statement["revenue_krw"])
            / previous_statement["revenue_krw"] * 100
        )
        recomputed_indicators["operating_income_growth_rate_percentage"] = round_to_one_decimal(
            (current_statement["operating_income_krw"] - previous_statement["operating_income_krw"])
            / abs(previous_statement["operating_income_krw"]) * 100
        )
        recomputed_indicators["earnings_per_share_growth_rate_percentage"] = round_to_one_decimal(
            (
                current_statement["controlling_interest_net_income_krw"]
                - previous_statement["controlling_interest_net_income_krw"]
            )
            / abs(previous_statement["controlling_interest_net_income_krw"]) * 100
        )
        recomputed_indicators["free_cash_flow_growth_rate_percentage"] = round_to_one_decimal(
            (current_free_cash_flow_krw - previous_free_cash_flow_krw)
            / abs(previous_free_cash_flow_krw) * 100
        )
        recomputed_indicators["return_on_equity_percentage"] = round_to_one_decimal(
            current_statement["controlling_interest_net_income_krw"]
            / (
                (
                    previous_statement["controlling_interest_equity_krw"]
                    + current_statement["controlling_interest_equity_krw"]
                )
                / 2
            )
            * 100
        )
        recomputed_indicators["return_on_assets_percentage"] = round_to_one_decimal(
            current_statement["controlling_interest_net_income_krw"]
            / (
                (previous_statement["total_assets_krw"] + current_statement["total_assets_krw"])
                / 2
            )
            * 100
        )

    return recomputed_indicators


def recompute_latest_and_average_indicators(
    fixture_data: Dict[str, Any],
    is_financial_industry: bool,
) -> tuple:
    """
    fixture 전체 연도를 독립 재계산하여 (최신 연도 지표, 5개년 평균 지표)를 반환합니다.
    (엔진과 동일하게 최신 연도부터 내림차순 정렬, None 은 평균에서 제외)
    """
    statements_descending = sorted(
        fixture_data["annual_financial_statements"],
        key=lambda statement: statement["fiscal_year"],
        reverse=True,
    )
    stock_price_and_market_cap = fixture_data["stock_price_and_market_cap"]

    recomputed_series = []
    for index, current_statement in enumerate(statements_descending):
        previous_statement = (
            statements_descending[index + 1]
            if index + 1 < len(statements_descending)
            else None
        )
        recomputed_series.append(
            recompute_annual_indicators_from_fixture(
                current_statement=current_statement,
                previous_statement=previous_statement,
                stock_price_and_market_cap=stock_price_and_market_cap,
                is_financial_industry=is_financial_industry,
            )
        )

    average_indicators: Dict[str, Any] = {}
    for indicator_key in recomputed_series[0].keys():
        valid_values = [
            series[indicator_key]
            for series in recomputed_series
            if series[indicator_key] is not None
        ]
        if not valid_values:
            average_indicators[f"average_{indicator_key}"] = None
        elif indicator_key == "free_cash_flow_amount_krw":
            average_indicators[f"average_{indicator_key}"] = int(sum(valid_values) / len(valid_values))
        else:
            average_indicators[f"average_{indicator_key}"] = round(
                sum(valid_values) / len(valid_values), 1
            )

    return recomputed_series[0], average_indicators


# ============================================================================
# 2. 공통 검증 유틸리티
# ============================================================================

def assert_indicator_values_match(
    actual_indicators: Dict[str, Any],
    expected_indicators: Dict[str, Any],
    comparison_label: str,
) -> None:
    """지표 딕셔너리의 각 항목이 기대값과 일치하는지 검증합니다 (None 포함)."""
    for indicator_key, expected_value in expected_indicators.items():
        actual_value = actual_indicators.get(indicator_key)

        if expected_value is None:
            assert actual_value is None, (
                f"[{comparison_label}] {indicator_key}: 기대값 None, 실제값 {actual_value}"
            )
        else:
            assert actual_value is not None, (
                f"[{comparison_label}] {indicator_key}: 기대값 {expected_value}, 실제값 None"
            )
            assert abs(actual_value - expected_value) <= INDICATOR_COMPARISON_TOLERANCE, (
                f"[{comparison_label}] {indicator_key}: "
                f"기대값 {expected_value}, 실제값 {actual_value}"
            )


def build_indicator_status_map(evaluation_report: Any) -> Dict[str, IndicatorEvaluationStatus]:
    """지표 한국어 명칭 -> 판정 상태 매핑을 생성합니다."""
    return {
        evaluation.indicator_name_korean: evaluation.evaluation_status
        for evaluation in evaluation_report.evaluations
    }


@pytest.fixture(scope="module")
def pipeline_results_by_stock_code() -> Dict[str, Any]:
    """3개 기업 파이프라인을 1회씩만 실행하고 결과를 캐싱합니다 (fixture 폴백 모드)."""
    cached_results = {}
    for target in REAL_COMPANY_VERIFICATION_TARGETS:
        cached_results[target["stock_code"]] = run_investment_analysis_pipeline(
            stock_code=target["stock_code"],
            fiscal_year=2023,
            number_of_years=5,
            use_fixture_fallback=True,
        )
    return cached_results


# ============================================================================
# 3. 검증 테스트: 지표 재현성 (원본 공시 값 -> 독립 재계산 일치)
# ============================================================================

@pytest.mark.parametrize(
    "target",
    REAL_COMPANY_VERIFICATION_TARGETS,
    ids=[target["company_name"] for target in REAL_COMPANY_VERIFICATION_TARGETS],
)
def test_latest_indicators_match_independent_recomputation(
    target: Dict[str, Any],
    pipeline_results_by_stock_code: Dict[str, Any],
) -> None:
    """최신 연도 15개 지표가 원본 fixture 기반 독립 재계산값과 일치하는지 검증"""
    fixture_data = load_fixture_data_for_target(target)
    recomputed_latest, _ = recompute_latest_and_average_indicators(
        fixture_data=fixture_data,
        is_financial_industry=target["is_financial_industry"],
    )

    actual_latest = pipeline_results_by_stock_code[
        target["stock_code"]
    ].indicators_summary.latest_indicators.to_dictionary()

    assert_indicator_values_match(
        actual_indicators=actual_latest,
        expected_indicators=recomputed_latest,
        comparison_label=f"{target['company_name']} 최신 연도 독립 재계산",
    )


@pytest.mark.parametrize(
    "target",
    REAL_COMPANY_VERIFICATION_TARGETS,
    ids=[target["company_name"] for target in REAL_COMPANY_VERIFICATION_TARGETS],
)
def test_five_year_averages_match_independent_recomputation(
    target: Dict[str, Any],
    pipeline_results_by_stock_code: Dict[str, Any],
) -> None:
    """5개년 평균 지표가 원본 fixture 기반 독립 재계산값과 일치하는지 검증"""
    fixture_data = load_fixture_data_for_target(target)
    _, recomputed_averages = recompute_latest_and_average_indicators(
        fixture_data=fixture_data,
        is_financial_industry=target["is_financial_industry"],
    )

    actual_averages = pipeline_results_by_stock_code[
        target["stock_code"]
    ].indicators_summary.historical_five_year_averages.to_dictionary()

    assert_indicator_values_match(
        actual_indicators=actual_averages,
        expected_indicators=recomputed_averages,
        comparison_label=f"{target['company_name']} 5개년 평균 독립 재계산",
    )


@pytest.mark.parametrize(
    "target",
    REAL_COMPANY_VERIFICATION_TARGETS,
    ids=[target["company_name"] for target in REAL_COMPANY_VERIFICATION_TARGETS],
)
def test_latest_and_average_indicators_match_documented_baseline(
    target: Dict[str, Any],
    pipeline_results_by_stock_code: Dict[str, Any],
) -> None:
    """확정 기준값(baseline)과 일치하는지 검증 (회귀 방지)"""
    pipeline_result = pipeline_results_by_stock_code[target["stock_code"]]

    assert_indicator_values_match(
        actual_indicators=pipeline_result.indicators_summary.latest_indicators.to_dictionary(),
        expected_indicators=target["expected_latest_indicators"],
        comparison_label=f"{target['company_name']} 최신 연도 기준값",
    )
    assert_indicator_values_match(
        actual_indicators=(
            pipeline_result.indicators_summary.historical_five_year_averages.to_dictionary()
        ),
        expected_indicators=target["expected_five_year_averages"],
        comparison_label=f"{target['company_name']} 5개년 평균 기준값",
    )


# ============================================================================
# 4. 검증 테스트: 금융업 예외 처리 (업종별 판정 분기)
# ============================================================================

@pytest.mark.parametrize(
    "target",
    REAL_COMPANY_VERIFICATION_TARGETS,
    ids=[target["company_name"] for target in REAL_COMPANY_VERIFICATION_TARGETS],
)
def test_financial_industry_exception_handling(
    target: Dict[str, Any],
    pipeline_results_by_stock_code: Dict[str, Any],
) -> None:
    """금융업은 3개 지표가 `판단불가`, 일반 제조업은 정상 산출되는지 검증"""
    pipeline_result = pipeline_results_by_stock_code[target["stock_code"]]
    latest_indicators = pipeline_result.indicators_summary.latest_indicators
    indicator_status_map = build_indicator_status_map(pipeline_result.evaluation_report)

    if target["is_financial_industry"]:
        assert latest_indicators.debt_to_equity_ratio_percentage is None
        assert latest_indicators.current_ratio_percentage is None
        assert latest_indicators.enterprise_value_to_ebitda_ratio is None

        for indicator_korean_name in FINANCIAL_INDUSTRY_EXCEPTION_INDICATOR_KOREAN_NAMES:
            assert (
                indicator_status_map[indicator_korean_name]
                == IndicatorEvaluationStatus.NOT_APPLICABLE
            ), (
                f"금융업({target['company_name']})의 {indicator_korean_name}은 "
                f"판단불가여야 합니다."
            )
    else:
        assert latest_indicators.debt_to_equity_ratio_percentage is not None
        assert latest_indicators.current_ratio_percentage is not None
        assert latest_indicators.enterprise_value_to_ebitda_ratio is not None

        for indicator_korean_name in FINANCIAL_INDUSTRY_EXCEPTION_INDICATOR_KOREAN_NAMES:
            assert (
                indicator_status_map[indicator_korean_name]
                != IndicatorEvaluationStatus.NOT_APPLICABLE
            ), (
                f"일반 제조업({target['company_name']})의 {indicator_korean_name}은 "
                f"판단불가가 아니어야 합니다."
            )


# ============================================================================
# 5. 검증 테스트: 시스템 원칙 준수 (규칙 1 투자 권유 금지, 리포트 무결성)
# ============================================================================

@pytest.mark.parametrize(
    "target",
    REAL_COMPANY_VERIFICATION_TARGETS,
    ids=[target["company_name"] for target in REAL_COMPANY_VERIFICATION_TARGETS],
)
def test_report_compliance_with_system_principles(
    target: Dict[str, Any],
    pipeline_results_by_stock_code: Dict[str, Any],
) -> None:
    """리포트가 투자 권유 금지 원칙과 표준 출력 규격을 준수하는지 검증"""
    pipeline_result = pipeline_results_by_stock_code[target["stock_code"]]
    report_text = pipeline_result.report_text_content

    # 규칙 1: 면책 고지 이전 본문에 투자 권유 표현이 존재하지 않아야 함
    disclaimer_position = report_text.find("면책 고지")
    body_text = report_text[:disclaimer_position] if disclaimer_position != -1 else report_text
    detected_violations = check_prohibited_expressions(body_text)
    assert detected_violations == [], (
        f"{target['company_name']} 리포트에서 금지 표현 감지: {detected_violations}"
    )

    # 15개 지표가 모두 리포트에 표기되어야 함
    assert len(pipeline_result.evaluation_report.evaluations) == 15
    for indicator_korean_name in ALL_FIFTEEN_INDICATOR_KOREAN_NAMES:
        assert indicator_korean_name in report_text, (
            f"{target['company_name']} 리포트에 {indicator_korean_name} 지표가 없습니다."
        )

    # 규칙 1·2·6: 객관적 근거(계산공식)와 데이터 출처가 명시되어야 함
    assert "계산공식" in report_text
    assert "출처" in report_text
    assert "DART" in report_text
    assert "매수" not in body_text
    assert "매도" not in body_text



