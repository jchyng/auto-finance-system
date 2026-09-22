"""
투자지표 상태 판정 엔진 (Investment Indicator Evaluator)

15개 핵심 투자지표를 객관적 기준에 따라 4단계(양호/보통/주의/판단불가)로 판정합니다.
- 규칙 1 (투자 권유 금지) 준수: 숫자 기반 객관적 판정만 수행
- 규칙 2 (AI 분리) 준수: 100% Python 코드로 판정 (AI 미사용)
- 규칙 3 (모듈 독립성): 단독 CLI 실행 가능
- 규칙 6 (명확한 명명): 축약어 없는 완전한 함수명
"""

import argparse
import json
from pathlib import Path
from typing import List, Optional, Tuple

from src.models.financial_statement_models import IndustryBenchmarkData
from src.models.investment_indicator_models import (
    CompanyInvestmentIndicatorsSummary,
    AnnualCalculatedIndicators,
    HistoricalFiveYearAverageIndicators,
)
from src.models.indicator_evaluation_models import (
    SingleIndicatorEvaluation,
    CompleteCompanyEvaluationReport,
    IndicatorEvaluationStatus,
    IndicatorCategory,
)


# ============================================================================
# 1. 성장성 지표 판정 함수 (Growth Indicators)
# ============================================================================

def evaluate_revenue_growth_rate(
    current_value: Optional[float],
    five_year_average: Optional[float],
    industry_average: Optional[float]
) -> Tuple[IndicatorEvaluationStatus, str]:
    """
    매출액 성장률 상태를 판정합니다.
    
    판정 기준 (상대 벤치마크):
    - 양호: 현재값 >= 5년평균 AND 현재값 >= 업종평균
    - 주의: 현재값 < 5년평균*0.8 AND 현재값 < 업종평균*0.8
    - 보통: 위 조건 사이
    - 판단불가: 데이터 부족
    
    Returns:
        (판정 상태, 판정 근거 문장) 튜플
    """
    if current_value is None:
        return (
            IndicatorEvaluationStatus.NOT_APPLICABLE,
            "전기 대비 성장률 계산에 필요한 데이터가 부족합니다."
        )
    
    # 5년 평균과 업종 평균이 모두 있는 경우
    if five_year_average is not None and industry_average is not None:
        if current_value >= five_year_average and current_value >= industry_average:
            return (
                IndicatorEvaluationStatus.GOOD,
                f"당기 성장률({current_value}%)이 기업의 5년 평균({five_year_average}%) 및 업종 평균({industry_average}%) 이상입니다."
            )
        elif current_value < five_year_average * 0.8 and current_value < industry_average * 0.8:
            return (
                IndicatorEvaluationStatus.CAUTION,
                f"당기 성장률({current_value}%)이 기업의 5년 평균({five_year_average}%)과 업종 평균({industry_average}%) 대비 20% 이상 낮습니다."
            )
        else:
            return (
                IndicatorEvaluationStatus.NORMAL,
                f"당기 성장률({current_value}%)이 5년 평균 및 업종 평균 수준에 근접합니다."
            )
    
    # 5년 평균만 있는 경우
    elif five_year_average is not None:
        if current_value >= five_year_average:
            return (
                IndicatorEvaluationStatus.GOOD,
                f"당기 성장률({current_value}%)이 기업의 5년 평균({five_year_average}%) 이상입니다."
            )
        elif current_value < five_year_average * 0.8:
            return (
                IndicatorEvaluationStatus.CAUTION,
                f"당기 성장률({current_value}%)이 5년 평균({five_year_average}%) 대비 20% 이상 낮습니다."
            )
        else:
            return (
                IndicatorEvaluationStatus.NORMAL,
                f"당기 성장률({current_value}%)이 5년 평균 수준에 근접합니다."
            )
    
    # 비교 기준이 없는 경우
    else:
        return (
            IndicatorEvaluationStatus.NOT_APPLICABLE,
            f"당기 성장률은 {current_value}%이나, 비교 기준(5년 평균, 업종 평균)이 없어 판정이 어렵습니다."
        )


def evaluate_operating_income_growth_rate(
    current_value: Optional[float],
    turnaround_note: Optional[str],
    five_year_average: Optional[float],
    industry_average: Optional[float]
) -> Tuple[IndicatorEvaluationStatus, str]:
    """
    영업이익 성장률 상태를 판정합니다.
    
    특수 케이스 (적자전환, 흑자전환, 적자지속) 우선 처리
    
    Returns:
        (판정 상태, 판정 근거 문장) 튜플
    """
    # 특수 케이스 처리
    if turnaround_note:
        if turnaround_note == "흑자전환":
            return (
                IndicatorEvaluationStatus.GOOD,
                "전기 영업손실에서 당기 영업이익으로 흑자전환하였습니다."
            )
        elif turnaround_note == "적자전환":
            return (
                IndicatorEvaluationStatus.CAUTION,
                "전기 영업이익에서 당기 영업손실로 적자전환하였습니다."
            )
        elif turnaround_note == "적자지속":
            return (
                IndicatorEvaluationStatus.CAUTION,
                "전기에 이어 당기에도 영업손실이 지속되고 있습니다."
            )
    
    # 일반 성장률 판정 (매출액 성장률과 동일 로직)
    return evaluate_revenue_growth_rate(current_value, five_year_average, industry_average)


# ============================================================================
# 2. 수익성 지표 판정 함수 (Profitability Indicators)
# ============================================================================

def evaluate_profitability_ratio(
    indicator_name_korean: str,
    current_value: Optional[float],
    five_year_average: Optional[float],
    industry_average: Optional[float],
    unit: str = "%"
) -> Tuple[IndicatorEvaluationStatus, str]:
    """
    수익성 비율(영업이익률, ROE, ROA, ROIC) 상태를 판정합니다.
    
    판정 기준 (상대 벤치마크):
    - 양호: 현재값 >= 5년평균 AND 현재값 >= 업종평균
    - 주의: 현재값 < 5년평균*0.8 AND 현재값 < 업종평균*0.8
    - 보통: 위 조건 사이
    - 판단불가: 데이터 부족 또는 적자
    
    Returns:
        (판정 상태, 판정 근거 문장) 튜플
    """
    if current_value is None:
        return (
            IndicatorEvaluationStatus.NOT_APPLICABLE,
            f"{indicator_name_korean} 계산에 필요한 데이터가 부족하거나 적자로 인해 판정할 수 없습니다."
        )
    
    # 5년 평균과 업종 평균이 모두 있는 경우
    if five_year_average is not None and industry_average is not None:
        if current_value >= five_year_average and current_value >= industry_average:
            return (
                IndicatorEvaluationStatus.GOOD,
                f"당기 {indicator_name_korean}({current_value}{unit})이 기업의 5년 평균({five_year_average}{unit}) 및 업종 평균({industry_average}{unit}) 이상입니다."
            )
        elif current_value < five_year_average * 0.8 and current_value < industry_average * 0.8:
            return (
                IndicatorEvaluationStatus.CAUTION,
                f"당기 {indicator_name_korean}({current_value}{unit})이 기업의 5년 평균({five_year_average}{unit})과 업종 평균({industry_average}{unit}) 대비 20% 이상 낮습니다."
            )
        else:
            return (
                IndicatorEvaluationStatus.NORMAL,
                f"당기 {indicator_name_korean}({current_value}{unit})이 5년 평균 및 업종 평균 수준에 근접합니다."
            )
    
    # 5년 평균만 있는 경우
    elif five_year_average is not None:
        if current_value >= five_year_average:
            return (
                IndicatorEvaluationStatus.GOOD,
                f"당기 {indicator_name_korean}({current_value}{unit})이 기업의 5년 평균({five_year_average}{unit}) 이상입니다."
            )
        elif current_value < five_year_average * 0.8:
            return (
                IndicatorEvaluationStatus.CAUTION,
                f"당기 {indicator_name_korean}({current_value}{unit})이 5년 평균({five_year_average}{unit}) 대비 20% 이상 낮습니다."
            )
        else:
            return (
                IndicatorEvaluationStatus.NORMAL,
                f"당기 {indicator_name_korean}({current_value}{unit})이 5년 평균 수준에 근접합니다."
            )
    
    # 비교 기준이 없는 경우
    else:
        return (
            IndicatorEvaluationStatus.NOT_APPLICABLE,
            f"당기 {indicator_name_korean}은 {current_value}{unit}이나, 비교 기준(5년 평균, 업종 평균)이 없어 판정이 어렵습니다."
        )


# ============================================================================
# 3. 재무건전성 지표 판정 함수 (Financial Health Indicators)
# ============================================================================

def evaluate_debt_to_equity_ratio(
    current_value: Optional[float],
    five_year_average: Optional[float]
) -> Tuple[IndicatorEvaluationStatus, str]:
    """
    부채비율 상태를 판정합니다.
    
    판정 기준 (절대 기준 우선):
    - 양호: <= 100%
    - 보통: 100% < x <= 200%
    - 주의: > 200%
    - 판단불가: 금융업 또는 데이터 부족
    
    Returns:
        (판정 상태, 판정 근거 문장) 튜플
    """
    if current_value is None:
        return (
            IndicatorEvaluationStatus.NOT_APPLICABLE,
            "금융업 특성상 부채비율 판정이 적합하지 않거나 데이터가 부족합니다."
        )
    
    avg_text = f" (기업 5년 평균: {five_year_average}%)" if five_year_average else ""
    
    if current_value <= 100:
        return (
            IndicatorEvaluationStatus.GOOD,
            f"당기 부채비율({current_value}%)이 권고 기준(100% 이하)을 충족합니다{avg_text}."
        )
    elif current_value <= 200:
        return (
            IndicatorEvaluationStatus.NORMAL,
            f"당기 부채비율({current_value}%)이 권고 범위(100~200%) 내에 있습니다{avg_text}."
        )
    else:
        return (
            IndicatorEvaluationStatus.CAUTION,
            f"당기 부채비율({current_value}%)이 권고 상한선(200%)을 초과합니다{avg_text}."
        )


def evaluate_current_ratio(
    current_value: Optional[float],
    five_year_average: Optional[float]
) -> Tuple[IndicatorEvaluationStatus, str]:
    """
    유동비율 상태를 판정합니다.
    
    판정 기준 (절대 기준 우선):
    - 양호: >= 150%
    - 보통: 100% <= x < 150%
    - 주의: < 100%
    - 판단불가: 금융업 또는 데이터 부족
    
    Returns:
        (판정 상태, 판정 근거 문장) 튜플
    """
    if current_value is None:
        return (
            IndicatorEvaluationStatus.NOT_APPLICABLE,
            "금융업 특성상 유동비율 판정이 적합하지 않거나 데이터가 부족합니다."
        )
    
    avg_text = f" (기업 5년 평균: {five_year_average}%)" if five_year_average else ""
    
    if current_value >= 150:
        return (
            IndicatorEvaluationStatus.GOOD,
            f"당기 유동비율({current_value}%)이 안전 기준(150% 이상)을 충족합니다{avg_text}."
        )
    elif current_value >= 100:
        return (
            IndicatorEvaluationStatus.NORMAL,
            f"당기 유동비율({current_value}%)이 최소 기준(100% 이상)을 충족합니다{avg_text}."
        )
    else:
        return (
            IndicatorEvaluationStatus.CAUTION,
            f"당기 유동비율({current_value}%)이 최소 기준(100%)에 미달합니다{avg_text}."
        )


def evaluate_interest_coverage_ratio(
    current_value: Optional[float],
    is_debt_free: bool,
    five_year_average: Optional[float],
    is_financial_industry: bool = False
) -> Tuple[IndicatorEvaluationStatus, str]:
    """
    이자보상배율 상태를 판정합니다.
    
    판정 기준 (절대 기준 우선):
    - 양호: >= 3.0배 또는 무차입
    - 보통: 1.0 <= x < 3.0배
    - 주의: < 1.0배
    - 판단불가: 데이터 부족
    
    Returns:
        (판정 상태, 판정 근거 문장) 튜플
    """
    # 금융업 예외: 이자비용이 본업의 원가이므로 잠재부실 판정에 사용 불가
    if is_financial_industry:
        return (
            IndicatorEvaluationStatus.NOT_APPLICABLE,
            "금융업 특성상 이자보상배율 판정이 적합하지 않거나 데이터가 부족합니다."
        )

    if is_debt_free:
        return (
            IndicatorEvaluationStatus.GOOD,
            "무차입 기업으로 이자비용이 없습니다."
        )
    
    if current_value is None:
        return (
            IndicatorEvaluationStatus.NOT_APPLICABLE,
            "이자보상배율 계산에 필요한 데이터가 부족합니다."
        )
    
    avg_text = f" (기업 5년 평균: {five_year_average}배)" if five_year_average else ""
    
    if current_value >= 3.0:
        return (
            IndicatorEvaluationStatus.GOOD,
            f"당기 이자보상배율({current_value}배)이 안전 기준(3.0배 이상)을 충족합니다{avg_text}."
        )
    elif current_value >= 1.0:
        return (
            IndicatorEvaluationStatus.NORMAL,
            f"당기 이자보상배율({current_value}배)이 최소 기준(1.0배 이상)을 충족합니다{avg_text}."
        )
    else:
        return (
            IndicatorEvaluationStatus.CAUTION,
            f"당기 이자보상배율({current_value}배)이 최소 기준(1.0배)에 미달하여 잠재적 부실 위험이 있습니다{avg_text}."
        )


def evaluate_free_cash_flow(
    current_fcf: Optional[int],
    historical_indicators: List[AnnualCalculatedIndicators]
) -> Tuple[IndicatorEvaluationStatus, str]:
    """
    잉여현금흐름(FCF) 상태를 판정합니다.
    
    판정 기준:
    - 양호: 최근 3년 연속 흑자(+)
    - 보통: 당기 흑자(+)
    - 주의: 당기 적자(-) 또는 2년 연속 적자
    - 판단불가: 데이터 부족
    
    Returns:
        (판정 상태, 판정 근거 문장) 튜플
    """
    if current_fcf is None:
        return (
            IndicatorEvaluationStatus.NOT_APPLICABLE,
            "FCF 계산에 필요한 데이터가 부족합니다."
        )
    
    # 최근 3년 FCF 수집 (최신 연도부터)
    recent_fcfs = []
    for annual in historical_indicators[:3]:  # 최신 3개 연도
        if annual.free_cash_flow_amount_krw is not None:
            recent_fcfs.append(annual.free_cash_flow_amount_krw)
    
    # 최근 3년 모두 흑자
    if len(recent_fcfs) >= 3 and all(fcf > 0 for fcf in recent_fcfs):
        return (
            IndicatorEvaluationStatus.GOOD,
            f"최근 3년 연속 FCF 흑자를 유지하고 있습니다 (당기: {current_fcf:,}원)."
        )
    
    # 당기 흑자
    if current_fcf > 0:
        return (
            IndicatorEvaluationStatus.NORMAL,
            f"당기 FCF는 흑자입니다 ({current_fcf:,}원)."
        )
    
    # 당기 적자 또는 2년 연속 적자
    consecutive_deficits = 0
    for fcf in recent_fcfs[:2]:  # 최신 2개 연도
        if fcf < 0:
            consecutive_deficits += 1
    
    if consecutive_deficits >= 2:
        return (
            IndicatorEvaluationStatus.CAUTION,
            f"최근 2년 연속 FCF 적자가 발생했습니다 (당기: {current_fcf:,}원)."
        )
    else:
        return (
            IndicatorEvaluationStatus.CAUTION,
            f"당기 FCF가 적자입니다 ({current_fcf:,}원)."
        )


# ============================================================================
# 4. 밸류에이션 지표 판정 함수 (Valuation Indicators)
# ============================================================================

def evaluate_valuation_ratio(
    indicator_name_korean: str,
    current_value: Optional[float],
    five_year_average: Optional[float],
    industry_average: Optional[float],
    unit: str = "배"
) -> Tuple[IndicatorEvaluationStatus, str]:
    """
    밸류에이션 비율(PER, PBR, EV/EBITDA) 상태를 판정합니다.
    
    판정 기준 (상대 비교, 낮을수록 저평가):
    - 과거/업종 대비 낮음: 현재값 < 5년평균 AND 현재값 < 업종평균
    - 과거/업종 대비 높음: 현재값 > 5년평균 AND 현재값 > 업종평균
    - 보통: 평균치 ±15% 이내
    - 판단불가: 적자 또는 데이터 부족
    
    Returns:
        (판정 상태, 판정 근거 문장) 튜플
    """
    if current_value is None:
        return (
            IndicatorEvaluationStatus.NOT_APPLICABLE,
            f"{indicator_name_korean} 계산에 필요한 데이터가 부족하거나 적자로 인해 판정할 수 없습니다."
        )
    
    # 5년 평균과 업종 평균이 모두 있는 경우
    if five_year_average is not None and industry_average is not None:
        if current_value < five_year_average and current_value < industry_average:
            return (
                IndicatorEvaluationStatus.NORMAL,
                f"당기 {indicator_name_korean}({current_value}{unit})이 기업의 5년 평균({five_year_average}{unit}) 및 업종 평균({industry_average}{unit})보다 낮습니다."
            )
        elif current_value > five_year_average and current_value > industry_average:
            return (
                IndicatorEvaluationStatus.NORMAL,
                f"당기 {indicator_name_korean}({current_value}{unit})이 기업의 5년 평균({five_year_average}{unit}) 및 업종 평균({industry_average}{unit})보다 높습니다."
            )
        else:
            return (
                IndicatorEvaluationStatus.NORMAL,
                f"당기 {indicator_name_korean}({current_value}{unit})이 5년 평균 및 업종 평균 수준에 근접합니다."
            )
    
    # 5년 평균만 있는 경우
    elif five_year_average is not None:
        tolerance = five_year_average * 0.15
        if abs(current_value - five_year_average) <= tolerance:
            return (
                IndicatorEvaluationStatus.NORMAL,
                f"당기 {indicator_name_korean}({current_value}{unit})이 기업의 5년 평균({five_year_average}{unit}) 수준에 근접합니다."
            )
        elif current_value < five_year_average:
            return (
                IndicatorEvaluationStatus.NORMAL,
                f"당기 {indicator_name_korean}({current_value}{unit})이 기업의 5년 평균({five_year_average}{unit})보다 낮습니다."
            )
        else:
            return (
                IndicatorEvaluationStatus.NORMAL,
                f"당기 {indicator_name_korean}({current_value}{unit})이 기업의 5년 평균({five_year_average}{unit})보다 높습니다."
            )
    
    # 비교 기준이 없는 경우
    else:
        return (
            IndicatorEvaluationStatus.NOT_APPLICABLE,
            f"당기 {indicator_name_korean}은 {current_value}{unit}이나, 비교 기준(5년 평균, 업종 평균)이 없어 판정이 어렵습니다."
        )


# ============================================================================
# 통합 평가 함수
# ============================================================================

def format_optional_value(
    value: Optional[float],
    unit: str,
    decimal_places: int = 1
) -> str:
    """
    Optional 값을 형식화된 문자열로 변환합니다.
    
    Args:
        value: 변환할 값
        unit: 단위 (%, 배 등)
        decimal_places: 소수점 자릿수
    
    Returns:
        형식화된 문자열
    """
    if value is None:
        return "데이터 부족"
    
    return f"{value:.{decimal_places}f}{unit}"


def format_optional_value_int(value: Optional[int]) -> str:
    """
    Optional 정수 값을 형식화된 문자열로 변환합니다.
    
    Args:
        value: 변환할 값
    
    Returns:
        형식화된 문자열
    """
    if value is None:
        return "데이터 부족"
    
    # 조 단위
    if abs(value) >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:.1f}조원"
    # 억 단위
    elif abs(value) >= 100_000_000:
        return f"{value / 100_000_000:.0f}억원"
    # 만 단위
    elif abs(value) >= 10_000:
        return f"{value / 10_000:.0f}만원"
    else:
        return f"{value:,}원"


def create_single_indicator_evaluation(
    category: IndicatorCategory,
    name_korean: str,
    name_english: str,
    current_value: str,
    five_year_average: str,
    industry_benchmark: str,
    status: IndicatorEvaluationStatus,
    reason: str,
    formula: str,
    data_source: str
) -> SingleIndicatorEvaluation:
    """
    개별 지표 평가 결과를 생성합니다.
    
    Returns:
        SingleIndicatorEvaluation 모델
    """
    return SingleIndicatorEvaluation(
        indicator_category=category,
        indicator_name_korean=name_korean,
        indicator_name_english=name_english,
        current_value_formatted=current_value,
        historical_five_year_average_formatted=five_year_average,
        industry_benchmark_average_formatted=industry_benchmark,
        evaluation_status=status,
        evaluation_reason_description=reason,
        calculation_formula_description=formula,
        data_source_and_base_date_description=data_source
    )


def evaluate_all_indicators(
    indicators_summary: CompanyInvestmentIndicatorsSummary,
    industry_benchmark: Optional[IndustryBenchmarkData],
    base_fiscal_year: int
) -> List[SingleIndicatorEvaluation]:
    """
    15개 모든 지표를 평가하여 SingleIndicatorEvaluation 리스트로 반환합니다.
    
    Args:
        indicators_summary: 기업 투자지표 요약
        industry_benchmark: 업종 벤치마크 데이터
        base_fiscal_year: 기준 사업연도
    
    Returns:
        15개 지표 평가 결과 리스트
    """
    latest = indicators_summary.latest_indicators
    averages = indicators_summary.historical_five_year_averages
    
    # 데이터 출처 기본 정보
    data_source_base = f"DART 사업보고서 ({base_fiscal_year}년 결산 기준)"
    
    # 과거 5개 연도 지표 수집 (FCF 판정용)
    # Note: 실제 구현에서는 indicators_summary에 연도별 리스트가 필요
    # 현재는 latest만 있으므로 간소화
    historical_list = [latest]  # 실제로는 5개년 리스트 필요
    
    evaluations = []
    
    # ========== 1. 성장성 지표 ==========
    
    # 1-1. 매출액 성장률
    status, reason = evaluate_revenue_growth_rate(
        latest.revenue_growth_rate_percentage,
        averages.average_revenue_growth_rate_percentage,
        None  # 업종 평균 미제공
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.GROWTH,
        name_korean="매출액 성장률",
        name_english="Revenue Growth Rate (YoY)",
        current_value=format_optional_value(latest.revenue_growth_rate_percentage, "%"),
        five_year_average=format_optional_value(averages.average_revenue_growth_rate_percentage, "%"),
        industry_benchmark="업종 데이터 없음",
        status=status,
        reason=reason,
        formula="(당기 매출액 - 전기 매출액) / 전기 매출액 × 100",
        data_source=data_source_base
    ))
    
    # 1-2. 영업이익 성장률
    status, reason = evaluate_operating_income_growth_rate(
        latest.operating_income_growth_rate_percentage,
        latest.operating_income_turnaround_status_note,
        averages.average_operating_income_growth_rate_percentage,
        None
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.GROWTH,
        name_korean="영업이익 성장률",
        name_english="Operating Income Growth Rate (YoY)",
        current_value=format_optional_value(latest.operating_income_growth_rate_percentage, "%") if not latest.operating_income_turnaround_status_note else latest.operating_income_turnaround_status_note,
        five_year_average=format_optional_value(averages.average_operating_income_growth_rate_percentage, "%"),
        industry_benchmark="업종 데이터 없음",
        status=status,
        reason=reason,
        formula="(당기 영업이익 - 전기 영업이익) / |전기 영업이익| × 100",
        data_source=data_source_base
    ))
    
    # 1-3. EPS 성장률
    status, reason = evaluate_revenue_growth_rate(
        latest.earnings_per_share_growth_rate_percentage,
        averages.average_earnings_per_share_growth_rate_percentage,
        None
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.GROWTH,
        name_korean="EPS 성장률",
        name_english="EPS Growth Rate (YoY)",
        current_value=format_optional_value(latest.earnings_per_share_growth_rate_percentage, "%"),
        five_year_average=format_optional_value(averages.average_earnings_per_share_growth_rate_percentage, "%"),
        industry_benchmark="업종 데이터 없음",
        status=status,
        reason=reason,
        formula="(당기 EPS - 전기 EPS) / |전기 EPS| × 100",
        data_source=data_source_base
    ))
    
    # 1-4. FCF 성장률
    status, reason = evaluate_revenue_growth_rate(
        latest.free_cash_flow_growth_rate_percentage,
        averages.average_free_cash_flow_growth_rate_percentage,
        None
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.GROWTH,
        name_korean="FCF 성장률",
        name_english="Free Cash Flow Growth Rate (YoY)",
        current_value=format_optional_value(latest.free_cash_flow_growth_rate_percentage, "%"),
        five_year_average=format_optional_value(averages.average_free_cash_flow_growth_rate_percentage, "%"),
        industry_benchmark="업종 데이터 없음",
        status=status,
        reason=reason,
        formula="(당기 FCF - 전기 FCF) / |전기 FCF| × 100",
        data_source=data_source_base
    ))
    
    # ========== 2. 수익성 지표 ==========
    
    # 2-1. 영업이익률
    status, reason = evaluate_profitability_ratio(
        "영업이익률",
        latest.operating_profit_margin_percentage,
        averages.average_operating_profit_margin_percentage,
        industry_benchmark.average_operating_profit_margin_percentage if industry_benchmark else None,
        "%"
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.PROFITABILITY,
        name_korean="영업이익률",
        name_english="Operating Profit Margin",
        current_value=format_optional_value(latest.operating_profit_margin_percentage, "%"),
        five_year_average=format_optional_value(averages.average_operating_profit_margin_percentage, "%"),
        industry_benchmark=format_optional_value(industry_benchmark.average_operating_profit_margin_percentage, "%") if industry_benchmark else "업종 데이터 없음",
        status=status,
        reason=reason,
        formula="영업이익 / 매출액 × 100",
        data_source=data_source_base
    ))
    
    # 2-2. ROE
    status, reason = evaluate_profitability_ratio(
        "ROE",
        latest.return_on_equity_percentage,
        averages.average_return_on_equity_percentage,
        industry_benchmark.average_return_on_equity_percentage if industry_benchmark else None,
        "%"
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.PROFITABILITY,
        name_korean="ROE",
        name_english="Return on Equity",
        current_value=format_optional_value(latest.return_on_equity_percentage, "%"),
        five_year_average=format_optional_value(averages.average_return_on_equity_percentage, "%"),
        industry_benchmark=format_optional_value(industry_benchmark.average_return_on_equity_percentage, "%") if industry_benchmark else "업종 데이터 없음",
        status=status,
        reason=reason,
        formula="지배주주순이익 / 평균 자기자본 × 100",
        data_source=data_source_base
    ))
    
    # 2-3. ROA
    status, reason = evaluate_profitability_ratio(
        "ROA",
        latest.return_on_assets_percentage,
        averages.average_return_on_assets_percentage,
        None,  # 업종 평균 미제공
        "%"
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.PROFITABILITY,
        name_korean="ROA",
        name_english="Return on Assets",
        current_value=format_optional_value(latest.return_on_assets_percentage, "%"),
        five_year_average=format_optional_value(averages.average_return_on_assets_percentage, "%"),
        industry_benchmark="업종 데이터 없음",
        status=status,
        reason=reason,
        formula="당기순이익 / 평균 총자산 × 100",
        data_source=data_source_base
    ))
    
    # 2-4. ROIC (금융업은 순차입금 개념이 상이하여 판단불가)
    if indicators_summary.is_financial_industry:
        status = IndicatorEvaluationStatus.NOT_APPLICABLE
        reason = "금융업 특성상 ROIC 판정이 적합하지 않거나 데이터가 부족합니다."
    else:
        status, reason = evaluate_profitability_ratio(
            "ROIC",
            latest.return_on_invested_capital_percentage,
            averages.average_return_on_invested_capital_percentage,
            None,  # 업종 평균 미제공
            "%"
        )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.PROFITABILITY,
        name_korean="ROIC",
        name_english="Return on Invested Capital",
        current_value=format_optional_value(latest.return_on_invested_capital_percentage, "%"),
        five_year_average=format_optional_value(averages.average_return_on_invested_capital_percentage, "%"),
        industry_benchmark="업종 데이터 없음",
        status=status,
        reason=reason,
        formula="NOPAT / 투하자본 × 100 (NOPAT = 영업이익 × (1 - 실효세율))",
        data_source=data_source_base
    ))
    
    # ========== 3. 재무건전성 지표 ==========
    
    # 3-1. 부채비율
    status, reason = evaluate_debt_to_equity_ratio(
        latest.debt_to_equity_ratio_percentage,
        averages.average_debt_to_equity_ratio_percentage
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.FINANCIAL_HEALTH,
        name_korean="부채비율",
        name_english="Debt to Equity Ratio",
        current_value=format_optional_value(latest.debt_to_equity_ratio_percentage, "%"),
        five_year_average=format_optional_value(averages.average_debt_to_equity_ratio_percentage, "%"),
        industry_benchmark=format_optional_value(industry_benchmark.average_debt_to_equity_ratio_percentage, "%") if industry_benchmark else "업종 데이터 없음",
        status=status,
        reason=reason,
        formula="총부채 / 총자본 × 100",
        data_source=data_source_base
    ))
    
    # 3-2. 유동비율
    status, reason = evaluate_current_ratio(
        latest.current_ratio_percentage,
        averages.average_current_ratio_percentage
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.FINANCIAL_HEALTH,
        name_korean="유동비율",
        name_english="Current Ratio",
        current_value=format_optional_value(latest.current_ratio_percentage, "%"),
        five_year_average=format_optional_value(averages.average_current_ratio_percentage, "%"),
        industry_benchmark="업종 데이터 없음",
        status=status,
        reason=reason,
        formula="유동자산 / 유동부채 × 100",
        data_source=data_source_base
    ))
    
    # 3-3. 이자보상배율
    status, reason = evaluate_interest_coverage_ratio(
        latest.interest_coverage_ratio,
        latest.is_debt_free_company,
        averages.average_interest_coverage_ratio,
        indicators_summary.is_financial_industry
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.FINANCIAL_HEALTH,
        name_korean="이자보상배율",
        name_english="Interest Coverage Ratio",
        current_value="무차입" if (latest.is_debt_free_company and not indicators_summary.is_financial_industry) else format_optional_value(latest.interest_coverage_ratio, "배"),
        five_year_average=format_optional_value(averages.average_interest_coverage_ratio, "배"),
        industry_benchmark="업종 데이터 없음",
        status=status,
        reason=reason,
        formula="영업이익 / 이자비용",
        data_source=data_source_base
    ))
    
    # 3-4. FCF 절대금액
    status, reason = evaluate_free_cash_flow(
        latest.free_cash_flow_amount_krw,
        historical_list
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.FINANCIAL_HEALTH,
        name_korean="잉여현금흐름(FCF)",
        name_english="Free Cash Flow",
        current_value=format_optional_value_int(latest.free_cash_flow_amount_krw),
        five_year_average=format_optional_value_int(averages.average_free_cash_flow_amount_krw),
        industry_benchmark="업종 데이터 없음",
        status=status,
        reason=reason,
        formula="영업활동현금흐름 - (유형자산취득 + 무형자산취득)",
        data_source=data_source_base
    ))
    
    # ========== 4. 밸류에이션 지표 ==========
    
    # 4-1. PER
    status, reason = evaluate_valuation_ratio(
        "PER",
        latest.price_to_earnings_ratio,
        averages.average_price_to_earnings_ratio,
        industry_benchmark.average_price_to_earnings_ratio if industry_benchmark else None,
        "배"
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.VALUATION,
        name_korean="PER",
        name_english="Price to Earnings Ratio",
        current_value=format_optional_value(latest.price_to_earnings_ratio, "배"),
        five_year_average=format_optional_value(averages.average_price_to_earnings_ratio, "배"),
        industry_benchmark=format_optional_value(industry_benchmark.average_price_to_earnings_ratio, "배") if industry_benchmark else "업종 데이터 없음",
        status=status,
        reason=reason,
        formula="시가총액 / 지배주주순이익",
        data_source=f"{data_source_base}, KRX 시가총액"
    ))
    
    # 4-2. PBR
    status, reason = evaluate_valuation_ratio(
        "PBR",
        latest.price_to_book_ratio,
        averages.average_price_to_book_ratio,
        industry_benchmark.average_price_to_book_ratio if industry_benchmark else None,
        "배"
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.VALUATION,
        name_korean="PBR",
        name_english="Price to Book Ratio",
        current_value=format_optional_value(latest.price_to_book_ratio, "배"),
        five_year_average=format_optional_value(averages.average_price_to_book_ratio, "배"),
        industry_benchmark=format_optional_value(industry_benchmark.average_price_to_book_ratio, "배") if industry_benchmark else "업종 데이터 없음",
        status=status,
        reason=reason,
        formula="시가총액 / 지배주주자기자본",
        data_source=f"{data_source_base}, KRX 시가총액"
    ))
    
    # 4-3. EV/EBITDA
    status, reason = evaluate_valuation_ratio(
        "EV/EBITDA",
        latest.enterprise_value_to_ebitda_ratio,
        averages.average_enterprise_value_to_ebitda_ratio,
        None,  # 업종 평균 미제공
        "배"
    )
    evaluations.append(create_single_indicator_evaluation(
        category=IndicatorCategory.VALUATION,
        name_korean="EV/EBITDA",
        name_english="Enterprise Value to EBITDA",
        current_value=format_optional_value(latest.enterprise_value_to_ebitda_ratio, "배"),
        five_year_average=format_optional_value(averages.average_enterprise_value_to_ebitda_ratio, "배"),
        industry_benchmark="업종 데이터 없음",
        status=status,
        reason=reason,
        formula="(시가총액 + 총차입금 - 현금) / EBITDA",
        data_source=f"{data_source_base}, KRX 시가총액"
    ))
    
    return evaluations


def generate_complete_evaluation_report(
    indicators_summary: CompanyInvestmentIndicatorsSummary,
    industry_benchmark: Optional[IndustryBenchmarkData],
    closing_price: int,
    market_cap: int
) -> CompleteCompanyEvaluationReport:
    """
    최종 완성 평가 리포트를 생성합니다.
    
    Args:
        indicators_summary: 기업 투자지표 요약
        industry_benchmark: 업종 벤치마크 데이터
        closing_price: 분석 시점 주가
        market_cap: 시가총액
    
    Returns:
        CompleteCompanyEvaluationReport 모델
    """
    # 15개 지표 평가
    evaluations = evaluate_all_indicators(
        indicators_summary,
        industry_benchmark,
        indicators_summary.latest_fiscal_year
    )
    
    # 간단한 사실 요약 (AI 없이 템플릿 기반, 4단계 상태 개수 전체 표기)
    good_count = sum(1 for e in evaluations if e.evaluation_status == IndicatorEvaluationStatus.GOOD)
    normal_count = sum(1 for e in evaluations if e.evaluation_status == IndicatorEvaluationStatus.NORMAL)
    caution_count = sum(1 for e in evaluations if e.evaluation_status == IndicatorEvaluationStatus.CAUTION)
    not_applicable_count = sum(1 for e in evaluations if e.evaluation_status == IndicatorEvaluationStatus.NOT_APPLICABLE)
    
    summary_text = (
        f"{indicators_summary.company_name}({indicators_summary.stock_code})의 {indicators_summary.latest_fiscal_year}년 "
        f"재무 분석 결과, 총 {len(evaluations)}개 지표 중 양호 {good_count}개, 보통 {normal_count}개, "
        f"주의 {caution_count}개, 판단불가 {not_applicable_count}개입니다. "
        f"상세한 지표별 판정 근거는 아래 평가 내역을 참조하시기 바랍니다."
    )
    
    # 용어 사전 (기본)
    glossary = {
        "ROE": "자기자본이익률. 주주가 맡긴 돈으로 회사가 한 해 동안 벌어들인 순이익의 비율입니다.",
        "ROA": "총자산이익률. 회사가 보유한 모든 자산으로 얼마나 효율적으로 이익을 창출했는지 나타냅니다.",
        "ROIC": "투하자본이익률. 회사가 실제 사업에 투입한 자본 대비 영업이익 창출 능력을 나타냅니다.",
        "부채비율": "총부채를 총자본으로 나눈 비율. 낮을수록 재무 건전성이 좋습니다.",
        "유동비율": "1년 안에 현금화할 수 있는 자산이 1년 안에 갚아야 할 빚보다 얼마나 많은지를 나타냅니다.",
        "이자보상배율": "영업이익으로 이자비용을 몇 배나 감당할 수 있는지 나타내는 지표입니다.",
        "FCF": "잉여현금흐름. 영업활동으로 번 현금에서 자산 투자에 쓴 돈을 뺀 나머지 현금입니다.",
        "PER": "주가수익비율. 주가를 주당순이익으로 나눈 값으로, 몇 년치 이익으로 현재 주가를 회수할 수 있는지 나타냅니다.",
        "PBR": "주가순자산비율. 주가를 주당순자산으로 나눈 값으로, 장부상 자산 대비 시장 평가를 나타냅니다.",
        "EV/EBITDA": "기업가치를 상각 전 영업이익으로 나눈 배수. 인수합병 시 많이 활용되는 밸류에이션 지표입니다."
    }
    
    # 면책 문구
    disclaimer = (
        "본 자료는 공개된 재무제표 및 시장 데이터를 기반으로 한 객관적 분석 결과이며, "
        "투자 권유나 매수/매도 추천을 목적으로 하지 않습니다. "
        "투자 결정은 투자자 본인의 판단과 책임 하에 이루어져야 합니다."
    )
    
    return CompleteCompanyEvaluationReport(
        stock_code=indicators_summary.stock_code,
        company_name=indicators_summary.company_name,
        industry_classification_name=industry_benchmark.industry_classification_name if industry_benchmark else "미분류",
        fiscal_year=indicators_summary.latest_fiscal_year,
        closing_price_krw=closing_price,
        market_capitalization_krw=market_cap,
        evaluations=evaluations,
        plain_korean_summary_text=summary_text,
        financial_term_glossary_dictionary=glossary,
        disclaimer_text=disclaimer
    )


# ============================================================================
# CLI 실행 함수
# ============================================================================

def save_evaluation_report_to_json_file(
    report: CompleteCompanyEvaluationReport,
    output_file_path: str
) -> None:
    """
    평가 리포트를 JSON 파일로 저장합니다.
    
    Args:
        report: CompleteCompanyEvaluationReport 모델
        output_file_path: 저장할 JSON 파일 경로
    """
    output_data = report.to_dictionary()
    
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(output_data, file, ensure_ascii=False, indent=2)
    
    print(f"Success: 평가 리포트를 {output_file_path}에 저장 완료")


def main():
    """
    단독 CLI 실행 진입점
    
    Example:
        python -m src.engines.investment_indicator_evaluator \
            --metrics data/metrics/005930_indicators.json \
            --industry data/raw/005930_industry.json \
            --output data/evaluation/005930_evaluation.json
    """
    parser = argparse.ArgumentParser(
        description="투자지표 상태 판정 엔진 (독립 실행 모드)"
    )
    parser.add_argument(
        "--metrics",
        type=str,
        required=True,
        help="계산된 지표 JSON 파일 경로"
    )
    parser.add_argument(
        "--industry",
        type=str,
        default=None,
        help="업종 벤치마크 JSON 파일 경로 (선택)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/evaluation/evaluation_report.json",
        help="출력 JSON 파일 경로"
    )
    
    args = parser.parse_args()
    
    try:
        # 지표 데이터 로드
        metrics_path = Path(args.metrics)
        if not metrics_path.exists():
            raise FileNotFoundError(f"지표 파일이 존재하지 않습니다: {args.metrics}")
        
        with open(metrics_path, "r", encoding="utf-8") as file:
            metrics_data = json.load(file)
        
        indicators_summary = CompanyInvestmentIndicatorsSummary.from_dictionary(metrics_data)
        
        # 업종 벤치마크 로드 (선택)
        industry_benchmark = None
        if args.industry:
            industry_path = Path(args.industry)
            if industry_path.exists():
                with open(industry_path, "r", encoding="utf-8") as file:
                    industry_data = json.load(file)
                
                benchmark_dict = industry_data.get("industry_benchmark", industry_data)
                industry_benchmark = IndustryBenchmarkData.from_dictionary(benchmark_dict)
                print(f"Info: 업종 벤치마크 로드 완료 ({industry_benchmark.industry_classification_name})")
            else:
                print(f"Warning: 업종 파일이 존재하지 않습니다: {args.industry}")
        
        # 평가 리포트 생성
        print(f"Info: {indicators_summary.company_name} 투자지표 상태 판정 시작")
        
        # 주가/시총 정보는 지표 데이터에 포함되어 있지 않으므로 기본값 사용
        # 실제로는 별도 입력 필요
        closing_price = 0  # TODO: 주가 데이터 연동
        market_cap = 0  # TODO: 시총 데이터 연동
        
        report = generate_complete_evaluation_report(
            indicators_summary,
            industry_benchmark,
            closing_price,
            market_cap
        )
        
        # 저장
        save_evaluation_report_to_json_file(report, args.output)
        
        print("\n=== 판정 요약 ===")
        print(f"종목코드: {report.stock_code}")
        print(f"기업명: {report.company_name}")
        print(f"업종: {report.industry_classification_name}")
        print(f"분석 연도: {report.fiscal_year}")
        print(f"\n지표별 판정 결과:")
        
        status_counts = {
            IndicatorEvaluationStatus.GOOD: 0,
            IndicatorEvaluationStatus.NORMAL: 0,
            IndicatorEvaluationStatus.CAUTION: 0,
            IndicatorEvaluationStatus.NOT_APPLICABLE: 0
        }
        
        for evaluation in report.evaluations:
            status_counts[evaluation.evaluation_status] += 1
        
        print(f"  양호: {status_counts[IndicatorEvaluationStatus.GOOD]}개")
        print(f"  보통: {status_counts[IndicatorEvaluationStatus.NORMAL]}개")
        print(f"  주의: {status_counts[IndicatorEvaluationStatus.CAUTION]}개")
        print(f"  판단불가: {status_counts[IndicatorEvaluationStatus.NOT_APPLICABLE]}개")
        print(f"\n출력 파일: {args.output}")
        
    except Exception as error:
        print(f"\nError: 투자지표 판정 실패 - {error}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
