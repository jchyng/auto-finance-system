"""
투자지표 계산 엔진 (Financial Indicator Calculator)

15개 핵심 투자지표를 순수 수학 공식으로 계산합니다.
- 금융업(은행/증권/보험) 예외: 부채비율, 유동비율, 이자보상배율, ROIC, EV/EBITDA -> 판단불가(업종 특성)
- 외부 API 의존성 없음 (100% 순수 함수)
- 적자, 0나누기, 금융업 예외 처리 포함
- 규칙 2 (AI 분리) 준수: 지표 계산은 100% Python 코드로 수행
- 규칙 3 (모듈 독립성): 단독 CLI 실행 가능
- 규칙 6 (명확한 명명): 축약어 없는 완전한 함수명
"""

import argparse
import json
from pathlib import Path
from typing import List, Optional, Tuple

from src.models.financial_statement_models import (
    NormalizedFinancialStatement,
    StockPriceAndMarketCapData,
)
from src.models.investment_indicator_models import (
    AnnualCalculatedIndicators,
    HistoricalFiveYearAverageIndicators,
    CompanyInvestmentIndicatorsSummary,
)


# ============================================================================
# 1. 성장성 지표 (Growth Indicators)
# ============================================================================

def calculate_revenue_growth_rate(
    current_revenue: int,
    previous_revenue: int
) -> Optional[float]:
    """
    매출액 성장률을 계산합니다 (YoY %).
    
    공식: (당기 매출액 - 전기 매출액) / 전기 매출액 * 100
    
    Args:
        current_revenue: 당기 매출액 (원)
        previous_revenue: 전기 매출액 (원)
    
    Returns:
        성장률 (%) 또는 None (전기 매출이 0일 경우)
    """
    if previous_revenue == 0:
        return None
    
    growth_rate = ((current_revenue - previous_revenue) / previous_revenue) * 100
    return round(growth_rate, 1)


def calculate_operating_income_growth_rate(
    current_operating_income: int,
    previous_operating_income: int
) -> Tuple[Optional[float], Optional[str]]:
    """
    영업이익 성장률을 계산합니다 (YoY %).
    
    공식: (당기 영업이익 - 전기 영업이익) / |전기 영업이익| * 100
    특수 케이스: 흑자전환, 적자지속, 적자전환
    
    Args:
        current_operating_income: 당기 영업이익 (원)
        previous_operating_income: 전기 영업이익 (원)
    
    Returns:
        (성장률 (%), 특수 상태 메모) 튜플
    """
    # 특수 케이스 판정
    if previous_operating_income < 0 and current_operating_income >= 0:
        return (None, "흑자전환")
    elif previous_operating_income < 0 and current_operating_income < 0:
        return (None, "적자지속")
    elif previous_operating_income >= 0 and current_operating_income < 0:
        return (None, "적자전환")
    
    if previous_operating_income == 0:
        return (None, None)
    
    growth_rate = ((current_operating_income - previous_operating_income) 
                   / abs(previous_operating_income)) * 100
    return (round(growth_rate, 1), None)


def calculate_eps_growth_rate(
    current_net_income: int,
    previous_net_income: int,
    current_shares: int,
    previous_shares: int
) -> Optional[float]:
    """
    EPS 성장률을 계산합니다 (YoY %).
    
    공식: (당기 EPS - 전기 EPS) / |전기 EPS| * 100
    EPS = 지배주주순이익 / 상장주식수
    
    Args:
        current_net_income: 당기 지배주주순이익 (원)
        previous_net_income: 전기 지배주주순이익 (원)
        current_shares: 당기 상장주식수
        previous_shares: 전기 상장주식수
    
    Returns:
        성장률 (%) 또는 None
    """
    if current_shares == 0 or previous_shares == 0:
        return None
    
    current_eps = current_net_income / current_shares
    previous_eps = previous_net_income / previous_shares
    
    if previous_eps == 0:
        return None
    
    growth_rate = ((current_eps - previous_eps) / abs(previous_eps)) * 100
    return round(growth_rate, 1)


def calculate_free_cash_flow(
    operating_cash_flow: int,
    acquisition_of_tangible_assets: int,
    acquisition_of_intangible_assets: int
) -> int:
    """
    잉여현금흐름(FCF)을 계산합니다.
    
    공식: 영업활동현금흐름 - (유형자산취득 + 무형자산취득)
    
    Args:
        operating_cash_flow: 영업활동현금흐름 (원)
        acquisition_of_tangible_assets: 유형자산취득 (원, 양수)
        acquisition_of_intangible_assets: 무형자산취득 (원, 양수)
    
    Returns:
        FCF (원)
    """
    fcf = operating_cash_flow - (acquisition_of_tangible_assets + acquisition_of_intangible_assets)
    return fcf


def calculate_fcf_growth_rate(
    current_fcf: int,
    previous_fcf: int
) -> Optional[float]:
    """
    FCF 성장률을 계산합니다 (YoY %).
    
    공식: (당기 FCF - 전기 FCF) / |전기 FCF| * 100
    
    Args:
        current_fcf: 당기 FCF (원)
        previous_fcf: 전기 FCF (원)
    
    Returns:
        성장률 (%) 또는 None
    """
    if previous_fcf == 0:
        return None
    
    growth_rate = ((current_fcf - previous_fcf) / abs(previous_fcf)) * 100
    return round(growth_rate, 1)


# ============================================================================
# 2. 수익성 지표 (Profitability Indicators)
# ============================================================================

def calculate_operating_profit_margin(
    operating_income: int,
    revenue: int
) -> Optional[float]:
    """
    영업이익률을 계산합니다 (%).
    
    공식: 영업이익 / 매출액 * 100
    
    Args:
        operating_income: 영업이익 (원)
        revenue: 매출액 (원)
    
    Returns:
        영업이익률 (%) 또는 None
    """
    if revenue == 0:
        return None
    
    margin = (operating_income / revenue) * 100
    return round(margin, 1)


def calculate_return_on_equity(
    net_income: int,
    beginning_equity: int,
    ending_equity: int
) -> Optional[float]:
    """
    ROE(자기자본이익률)를 계산합니다 (%).
    
    공식: 당기순이익 / 평균 자기자본 * 100
    평균 자기자본 = (기초자본 + 기말자본) / 2
    
    Args:
        net_income: 지배주주순이익 (원)
        beginning_equity: 기초 자기자본 (원)
        ending_equity: 기말 자기자본 (원)
    
    Returns:
        ROE (%) 또는 None
    """
    average_equity = (beginning_equity + ending_equity) / 2
    
    if average_equity == 0:
        return None
    
    roe = (net_income / average_equity) * 100
    return round(roe, 1)


def calculate_return_on_assets(
    net_income: int,
    beginning_assets: int,
    ending_assets: int
) -> Optional[float]:
    """
    ROA(총자산이익률)를 계산합니다 (%).
    
    공식: 당기순이익 / 평균 총자산 * 100
    평균 총자산 = (기초자산 + 기말자산) / 2
    
    Args:
        net_income: 지배주주순이익 (원)
        beginning_assets: 기초 총자산 (원)
        ending_assets: 기말 총자산 (원)
    
    Returns:
        ROA (%) 또는 None
    """
    average_assets = (beginning_assets + ending_assets) / 2
    
    if average_assets == 0:
        return None
    
    roa = (net_income / average_assets) * 100
    return round(roa, 1)


def calculate_return_on_invested_capital(
    operating_income: int,
    income_tax_expense: int,
    profit_before_tax: int,
    total_borrowings: int,
    equity: int,
    cash: int,
    is_financial_industry: bool
) -> Optional[float]:
    """
    ROIC(투하자본이익률)를 계산합니다 (%).
    
    공식: NOPAT / 투하자본 * 100
    NOPAT = 영업이익 * (1 - 실효세율)
    실효세율 = 법인세비용 / 법인세차감전순이익 (비정상시 20% 사용)
    투하자본 = 순차입금 + 자기자본
    순차입금 = 총차입금 - 현금성자산
    
    Args:
        operating_income: 영업이익 (원)
        income_tax_expense: 법인세비용 (원)
        profit_before_tax: 법인세차감전순이익 (원)
        total_borrowings: 총차입금 (원)
        equity: 자기자본 (원)
        cash: 현금및현금성자산 (원)
    
    Returns:
        ROIC (%) 또는 None (금융업 또는 투하자본이 0일 경우)
    """
    # 금융업 예외: 업종 특성상 ROIC 판정 부적합
    if is_financial_industry:
        return None

    # 실효세율 계산
    if profit_before_tax != 0 and income_tax_expense >= 0:
        effective_tax_rate = income_tax_expense / profit_before_tax
        # 실효세율이 비정상적인 경우 (음수, 100% 초과) 법정세율 20% 사용
        if effective_tax_rate < 0 or effective_tax_rate > 1:
            effective_tax_rate = 0.2
    else:
        effective_tax_rate = 0.2
    
    # NOPAT 계산
    nopat = operating_income * (1 - effective_tax_rate)
    
    # 투하자본 계산
    net_debt = total_borrowings - cash
    invested_capital = net_debt + equity
    
    if invested_capital == 0:
        return None
    
    roic = (nopat / invested_capital) * 100
    return round(roic, 1)


# ============================================================================
# 3. 재무건전성 지표 (Financial Health Indicators)
# ============================================================================

def calculate_debt_to_equity_ratio(
    total_liabilities: int,
    equity: int,
    is_financial_industry: bool
) -> Optional[float]:
    """
    부채비율을 계산합니다 (%).
    
    공식: 총부채 / 총자본 * 100
    
    Args:
        total_liabilities: 총부채 (원)
        equity: 총자본 (원)
        is_financial_industry: 금융업 여부
    
    Returns:
        부채비율 (%) 또는 None (금융업 또는 자본이 0일 경우)
    """
    if is_financial_industry:
        return None
    
    if equity == 0:
        return None
    
    debt_ratio = (total_liabilities / equity) * 100
    return round(debt_ratio, 1)


def calculate_current_ratio(
    current_assets: Optional[int],
    current_liabilities: Optional[int],
    is_financial_industry: bool
) -> Optional[float]:
    """
    유동비율을 계산합니다 (%).
    
    공식: 유동자산 / 유동부채 * 100
    
    Args:
        current_assets: 유동자산 (원) 또는 None
        current_liabilities: 유동부채 (원) 또는 None
        is_financial_industry: 금융업 여부
    
    Returns:
        유동비율 (%) 또는 None (금융업 또는 데이터 없을 경우)
    """
    if is_financial_industry or current_assets is None or current_liabilities is None:
        return None
    
    if current_liabilities == 0:
        return None
    
    current_ratio = (current_assets / current_liabilities) * 100
    return round(current_ratio, 1)


def calculate_interest_coverage_ratio(
    operating_income: int,
    interest_expense: int,
    is_financial_industry: bool
) -> Tuple[Optional[float], bool]:
    """
    이자보상배율을 계산합니다 (배).
    
    공식: 영업이익 / 이자비용
    
    Args:
        operating_income: 영업이익 (원)
        interest_expense: 이자비용 (원)
    
    Returns:
        (이자보상배율 (배), 무차입여부) 튜플 (금융업은 (None, False))
    """
    # 금융업 예외: 업종 특성상 이자보상배율 판정 부적합
    if is_financial_industry:
        return (None, False)

    # 무차입 기업 (이자비용 = 0)
    if interest_expense == 0:
        return (None, True)
    
    coverage_ratio = operating_income / interest_expense
    return (round(coverage_ratio, 1), False)


# ============================================================================
# 4. 밸류에이션 지표 (Valuation Indicators)
# ============================================================================

def calculate_price_to_earnings_ratio(
    market_capitalization: int,
    net_income: int
) -> Optional[float]:
    """
    PER(주가수익비율)을 계산합니다 (배).
    
    공식: 시가총액 / 지배주주순이익
    
    Args:
        market_capitalization: 시가총액 (원)
        net_income: 지배주주순이익 (원)
    
    Returns:
        PER (배) 또는 None (적자일 경우)
    """
    if net_income <= 0:
        return None
    
    per = market_capitalization / net_income
    return round(per, 1)


def calculate_price_to_book_ratio(
    market_capitalization: int,
    equity: int
) -> Optional[float]:
    """
    PBR(주가순자산비율)을 계산합니다 (배).
    
    공식: 시가총액 / 지배주주자기자본
    
    Args:
        market_capitalization: 시가총액 (원)
        equity: 지배주주자기자본 (원)
    
    Returns:
        PBR (배) 또는 None (자본잠식일 경우)
    """
    if equity <= 0:
        return None
    
    pbr = market_capitalization / equity
    return round(pbr, 1)


def calculate_enterprise_value_to_ebitda_ratio(
    market_capitalization: int,
    total_borrowings: int,
    cash: int,
    operating_income: int,
    depreciation: int,
    amortization: int,
    is_financial_industry: bool
) -> Optional[float]:
    """
    EV/EBITDA를 계산합니다 (배).
    
    공식: EV / EBITDA
    EV = 시가총액 + 총차입금 - 현금성자산
    EBITDA = 영업이익 + 감가상각비 + 무형자산상각비
    
    Args:
        market_capitalization: 시가총액 (원)
        total_borrowings: 총차입금 (원)
        cash: 현금및현금성자산 (원)
        operating_income: 영업이익 (원)
        depreciation: 유형자산감가상각비 (원)
        amortization: 무형자산상각비 (원)
        is_financial_industry: 금융업 여부
    
    Returns:
        EV/EBITDA (배) 또는 None (금융업 또는 EBITDA가 0 이하일 경우)
    """
    if is_financial_industry:
        return None
    
    # EV 계산
    enterprise_value = market_capitalization + total_borrowings - cash
    
    # EBITDA 계산
    ebitda = operating_income + depreciation + amortization
    
    if ebitda <= 0:
        return None
    
    ev_ebitda = enterprise_value / ebitda
    return round(ev_ebitda, 1)


# ============================================================================
# 통합 계산 함수
# ============================================================================

def calculate_annual_indicators(
    current_statement: NormalizedFinancialStatement,
    previous_statement: Optional[NormalizedFinancialStatement],
    stock_price_data: StockPriceAndMarketCapData
) -> AnnualCalculatedIndicators:
    """
    한 해의 15개 투자지표를 모두 계산합니다.
    
    Args:
        current_statement: 당기 재무제표
        previous_statement: 전기 재무제표 (없으면 성장률 계산 불가)
        stock_price_data: 주가 및 시가총액 데이터
    
    Returns:
        AnnualCalculatedIndicators 모델
    """
    fiscal_year = current_statement.fiscal_year
    
    # FCF 계산 (성장률 계산 전 필요)
    current_fcf = calculate_free_cash_flow(
        current_statement.operating_cash_flow_krw,
        current_statement.acquisition_of_tangible_assets_krw,
        current_statement.acquisition_of_intangible_assets_krw
    )
    
    # 성장률 지표 (전기 데이터 필요)
    revenue_growth = None
    operating_income_growth = None
    operating_income_note = None
    eps_growth = None
    fcf_growth = None
    
    if previous_statement:
        revenue_growth = calculate_revenue_growth_rate(
            current_statement.revenue_krw,
            previous_statement.revenue_krw
        )
        
        operating_income_growth, operating_income_note = calculate_operating_income_growth_rate(
            current_statement.operating_income_krw,
            previous_statement.operating_income_krw
        )
        
        eps_growth = calculate_eps_growth_rate(
            current_statement.controlling_interest_net_income_krw,
            previous_statement.controlling_interest_net_income_krw,
            stock_price_data.total_shares_outstanding,
            stock_price_data.total_shares_outstanding  # 간소화: 동일 주식수 사용
        )
        
        previous_fcf = calculate_free_cash_flow(
            previous_statement.operating_cash_flow_krw,
            previous_statement.acquisition_of_tangible_assets_krw,
            previous_statement.acquisition_of_intangible_assets_krw
        )
        fcf_growth = calculate_fcf_growth_rate(current_fcf, previous_fcf)
    
    # 수익성 지표
    operating_margin = calculate_operating_profit_margin(
        current_statement.operating_income_krw,
        current_statement.revenue_krw
    )
    
    roe = None
    roa = None
    if previous_statement:
        roe = calculate_return_on_equity(
            current_statement.controlling_interest_net_income_krw,
            previous_statement.controlling_interest_equity_krw,
            current_statement.controlling_interest_equity_krw
        )
        roa = calculate_return_on_assets(
            current_statement.controlling_interest_net_income_krw,
            previous_statement.total_assets_krw,
            current_statement.total_assets_krw
        )
    
    total_borrowings = (current_statement.short_term_borrowings_krw + 
                       current_statement.long_term_borrowings_krw)
    
    roic = calculate_return_on_invested_capital(
        current_statement.operating_income_krw,
        current_statement.income_tax_expense_krw,
        current_statement.profit_before_tax_krw,
        total_borrowings,
        current_statement.controlling_interest_equity_krw,
        current_statement.cash_and_cash_equivalents_krw,
        current_statement.is_financial_industry
    )
    
    # 재무건전성 지표
    debt_ratio = calculate_debt_to_equity_ratio(
        current_statement.total_liabilities_krw,
        current_statement.controlling_interest_equity_krw,
        current_statement.is_financial_industry
    )
    
    current_ratio = calculate_current_ratio(
        current_statement.current_assets_krw,
        current_statement.current_liabilities_krw,
        current_statement.is_financial_industry
    )
    
    interest_coverage, is_debt_free = calculate_interest_coverage_ratio(
        current_statement.operating_income_krw,
        current_statement.interest_expense_krw,
        current_statement.is_financial_industry
    )
    
    # 밸류에이션 지표
    per = calculate_price_to_earnings_ratio(
        stock_price_data.market_capitalization_krw,
        current_statement.controlling_interest_net_income_krw
    )
    
    pbr = calculate_price_to_book_ratio(
        stock_price_data.market_capitalization_krw,
        current_statement.controlling_interest_equity_krw
    )
    
    ev_ebitda = calculate_enterprise_value_to_ebitda_ratio(
        stock_price_data.market_capitalization_krw,
        total_borrowings,
        current_statement.cash_and_cash_equivalents_krw,
        current_statement.operating_income_krw,
        current_statement.tangible_asset_depreciation_krw,
        current_statement.intangible_asset_amortization_krw,
        current_statement.is_financial_industry
    )
    
    return AnnualCalculatedIndicators(
        fiscal_year=fiscal_year,
        revenue_growth_rate_percentage=revenue_growth,
        operating_income_growth_rate_percentage=operating_income_growth,
        operating_income_turnaround_status_note=operating_income_note,
        earnings_per_share_growth_rate_percentage=eps_growth,
        free_cash_flow_growth_rate_percentage=fcf_growth,
        operating_profit_margin_percentage=operating_margin,
        return_on_equity_percentage=roe,
        return_on_assets_percentage=roa,
        return_on_invested_capital_percentage=roic,
        debt_to_equity_ratio_percentage=debt_ratio,
        current_ratio_percentage=current_ratio,
        interest_coverage_ratio=interest_coverage,
        is_debt_free_company=is_debt_free,
        free_cash_flow_amount_krw=current_fcf,
        price_to_earnings_ratio=per,
        price_to_book_ratio=pbr,
        enterprise_value_to_ebitda_ratio=ev_ebitda
    )




# ============================================================================
# 5개년 평균 계산
# ============================================================================

def calculate_five_year_average_indicators(
    annual_indicators_list: List[AnnualCalculatedIndicators]
) -> HistoricalFiveYearAverageIndicators:
    """
    5개년 지표의 평균을 계산합니다.
    
    Args:
        annual_indicators_list: 5개 연도의 AnnualCalculatedIndicators 리스트
    
    Returns:
        HistoricalFiveYearAverageIndicators 모델
    """
    if not annual_indicators_list:
        raise ValueError("지표 리스트가 비어있습니다")
    
    years = [ind.fiscal_year for ind in annual_indicators_list]
    start_year = min(years)
    end_year = max(years)
    
    def safe_average(values: List[Optional[float]]) -> Optional[float]:
        """None을 제외한 평균 계산"""
        valid_values = [v for v in values if v is not None]
        if not valid_values:
            return None
        return round(sum(valid_values) / len(valid_values), 1)
    
    def safe_average_int(values: List[Optional[int]]) -> Optional[int]:
        """None을 제외한 정수 평균 계산"""
        valid_values = [v for v in values if v is not None]
        if not valid_values:
            return None
        return int(sum(valid_values) / len(valid_values))
    
    return HistoricalFiveYearAverageIndicators(
        start_fiscal_year=start_year,
        end_fiscal_year=end_year,
        average_revenue_growth_rate_percentage=safe_average(
            [ind.revenue_growth_rate_percentage for ind in annual_indicators_list]
        ),
        average_operating_income_growth_rate_percentage=safe_average(
            [ind.operating_income_growth_rate_percentage for ind in annual_indicators_list]
        ),
        average_earnings_per_share_growth_rate_percentage=safe_average(
            [ind.earnings_per_share_growth_rate_percentage for ind in annual_indicators_list]
        ),
        average_free_cash_flow_growth_rate_percentage=safe_average(
            [ind.free_cash_flow_growth_rate_percentage for ind in annual_indicators_list]
        ),
        average_operating_profit_margin_percentage=safe_average(
            [ind.operating_profit_margin_percentage for ind in annual_indicators_list]
        ),
        average_return_on_equity_percentage=safe_average(
            [ind.return_on_equity_percentage for ind in annual_indicators_list]
        ),
        average_return_on_assets_percentage=safe_average(
            [ind.return_on_assets_percentage for ind in annual_indicators_list]
        ),
        average_return_on_invested_capital_percentage=safe_average(
            [ind.return_on_invested_capital_percentage for ind in annual_indicators_list]
        ),
        average_debt_to_equity_ratio_percentage=safe_average(
            [ind.debt_to_equity_ratio_percentage for ind in annual_indicators_list]
        ),
        average_current_ratio_percentage=safe_average(
            [ind.current_ratio_percentage for ind in annual_indicators_list]
        ),
        average_interest_coverage_ratio=safe_average(
            [ind.interest_coverage_ratio for ind in annual_indicators_list]
        ),
        average_free_cash_flow_amount_krw=safe_average_int(
            [ind.free_cash_flow_amount_krw for ind in annual_indicators_list]
        ),
        average_price_to_earnings_ratio=safe_average(
            [ind.price_to_earnings_ratio for ind in annual_indicators_list]
        ),
        average_price_to_book_ratio=safe_average(
            [ind.price_to_book_ratio for ind in annual_indicators_list]
        ),
        average_enterprise_value_to_ebitda_ratio=safe_average(
            [ind.enterprise_value_to_ebitda_ratio for ind in annual_indicators_list]
        )
    )


def calculate_company_indicators_summary(
    financial_statements: List[NormalizedFinancialStatement],
    stock_price_data: StockPriceAndMarketCapData
) -> CompanyInvestmentIndicatorsSummary:
    """
    기업의 전체 투자지표 요약을 계산합니다.
    
    Args:
        financial_statements: 5개년 재무제표 리스트 (최신년도부터 내림차순)
        stock_price_data: 주가 및 시가총액 데이터
    
    Returns:
        CompanyInvestmentIndicatorsSummary 모델
    """
    if not financial_statements:
        raise ValueError("재무제표 리스트가 비어있습니다")
    
    # 최신 연도부터 내림차순 정렬 확인
    financial_statements_sorted = sorted(financial_statements, key=lambda x: x.fiscal_year, reverse=True)
    
    # 각 연도별 지표 계산
    annual_indicators = []
    for i, current_stmt in enumerate(financial_statements_sorted):
        previous_stmt = financial_statements_sorted[i + 1] if i + 1 < len(financial_statements_sorted) else None
        
        indicators = calculate_annual_indicators(current_stmt, previous_stmt, stock_price_data)
        annual_indicators.append(indicators)
    
    # 5개년 평균 계산
    five_year_averages = calculate_five_year_average_indicators(annual_indicators)
    
    # 최신 연도 정보
    latest_statement = financial_statements_sorted[0]
    latest_indicators = annual_indicators[0]
    
    return CompanyInvestmentIndicatorsSummary(
        stock_code=latest_statement.stock_code,
        company_name=latest_statement.company_name,
        latest_fiscal_year=latest_statement.fiscal_year,
        latest_indicators=latest_indicators,
        historical_five_year_averages=five_year_averages,
        is_financial_industry=latest_statement.is_financial_industry
    )


def save_indicators_summary_to_json_file(
    summary: CompanyInvestmentIndicatorsSummary,
    output_file_path: str
) -> None:
    """
    투자지표 요약을 JSON 파일로 저장합니다.
    
    Args:
        summary: CompanyInvestmentIndicatorsSummary 모델
        output_file_path: 저장할 JSON 파일 경로
    """
    output_data = summary.to_dictionary()
    
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(output_data, file, ensure_ascii=False, indent=2)
    
    print(f"Success: 투자지표를 {output_file_path}에 저장 완료")


def main():
    """
    단독 CLI 실행 진입점
    
    Example:
        python -m src.engines.financial_indicator_calculator \
            --financials data/processed/005930_normalized.json \
            --price data/raw/005930_price.json \
            --output data/metrics/005930_indicators.json
    """
    parser = argparse.ArgumentParser(
        description="투자지표 계산 엔진 (독립 실행 모드)"
    )
    parser.add_argument(
        "--financials",
        type=str,
        required=True,
        help="정제된 재무제표 JSON 파일 경로"
    )
    parser.add_argument(
        "--price",
        type=str,
        required=True,
        help="주가 데이터 JSON 파일 경로"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/metrics/indicators.json",
        help="출력 JSON 파일 경로"
    )
    
    args = parser.parse_args()
    
    try:
        # 재무제표 로드
        financials_path = Path(args.financials)
        if not financials_path.exists():
            raise FileNotFoundError(f"재무제표 파일이 존재하지 않습니다: {args.financials}")
        
        with open(financials_path, "r", encoding="utf-8") as file:
            financials_data = json.load(file)
        
        statements_list = financials_data.get("normalized_statements", [])
        if not statements_list:
            raise ValueError("재무제표 데이터가 비어있습니다")
        
        financial_statements = [
            NormalizedFinancialStatement.from_dictionary(stmt)
            for stmt in statements_list
        ]
        
        # 주가 데이터 로드
        price_path = Path(args.price)
        if not price_path.exists():
            raise FileNotFoundError(f"주가 파일이 존재하지 않습니다: {args.price}")
        
        with open(price_path, "r", encoding="utf-8") as file:
            price_data = json.load(file)
        
        stock_price = StockPriceAndMarketCapData.from_dictionary(
            price_data.get("stock_price_data", price_data)
        )
        
        # 지표 계산
        print(f"Info: {financial_statements[0].company_name} 투자지표 계산 시작")
        summary = calculate_company_indicators_summary(financial_statements, stock_price)
        
        # 저장
        save_indicators_summary_to_json_file(summary, args.output)
        
        print("\n=== 계산 요약 ===")
        print(f"종목코드: {summary.stock_code}")
        print(f"기업명: {summary.company_name}")
        print(f"최신 연도: {summary.latest_fiscal_year}")
        print(f"5개년 평균 기간: {summary.historical_five_year_averages.start_fiscal_year} ~ {summary.historical_five_year_averages.end_fiscal_year}")
        print(f"\n주요 지표 (최신 연도):")
        print(f"  매출액 성장률: {summary.latest_indicators.revenue_growth_rate_percentage}%")
        print(f"  영업이익률: {summary.latest_indicators.operating_profit_margin_percentage}%")
        print(f"  ROE: {summary.latest_indicators.return_on_equity_percentage}%")
        print(f"  부채비율: {summary.latest_indicators.debt_to_equity_ratio_percentage}%")
        print(f"  PER: {summary.latest_indicators.price_to_earnings_ratio}배")
        print(f"\n출력 파일: {args.output}")
        
    except Exception as error:
        print(f"\nError: 투자지표 계산 실패 - {error}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
