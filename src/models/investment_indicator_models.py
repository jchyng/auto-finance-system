"""
투자 지표 데이터 모델 (Investment Indicator Data Models)

본 모듈은 4대 영역(성장성, 수익성, 재무건전성, 밸류에이션) 15개 핵심 투자 지표와
과거 5개년 평균 지표의 엄격한 데이터 규격을 정의합니다.
규칙 6에 따라 모든 필드명은 단위(percentage, krw, ratio)를 포함한 완전한 명칭을 사용합니다.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AnnualCalculatedIndicators:
    """
    특정 사업연도의 15개 계산된 투자 지표
    """
    fiscal_year: int                                                 # 사업연도 (예: 2023)
    
    # 1. 성장성 지표 (Growth Indicators, 단위: %)
    revenue_growth_rate_percentage: Optional[float]                  # 매출액 성장률 (전년 대비)
    operating_income_growth_rate_percentage: Optional[float]         # 영업이익 성장률 (전년 대비)
    operating_income_turnaround_status_note: Optional[str]           # 영업익 상태 비고 ("흑자전환", "적자지속", "적자전환" 등)
    earnings_per_share_growth_rate_percentage: Optional[float]       # EPS 성장률 (수정EPS 기준)
    free_cash_flow_growth_rate_percentage: Optional[float]           # FCF 성장률
    
    # 2. 수익성 지표 (Profitability Indicators, 단위: %)
    operating_profit_margin_percentage: Optional[float]              # 영업이익률
    return_on_equity_percentage: Optional[float]                     # ROE (지배주주자기자본이익률)
    return_on_assets_percentage: Optional[float]                     # ROA (총자산이익률)
    return_on_invested_capital_percentage: Optional[float]           # ROIC (투하자본이익률 - 표준 간이 공식)
    
    # 3. 재무건전성 지표 (Financial Health Indicators)
    debt_to_equity_ratio_percentage: Optional[float]                 # 부채비율 (단위: %, 금융업 None)
    current_ratio_percentage: Optional[float]                        # 유동비율 (단위: %, 금융업 None)
    interest_coverage_ratio: Optional[float]                         # 이자보상배율 (배수, 무차입 시 특수 표기)
    is_debt_free_company: bool                                       # 무차입 경영 여부 (이자비용 0원)
    free_cash_flow_amount_krw: Optional[int]                         # FCF 절대금액 (단위: 원)
    
    # 4. 밸류에이션 지표 (Valuation Indicators, 단위: 배수)
    price_to_earnings_ratio: Optional[float]                         # PER (적자 시 None)
    price_to_book_ratio: Optional[float]                             # PBR (완전자본잠식 시 None)
    enterprise_value_to_ebitda_ratio: Optional[float]                # EV/EBITDA (금융업 None)

    def to_dictionary(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dictionary(cls, data_dictionary: Dict[str, Any]) -> "AnnualCalculatedIndicators":
        return cls(**data_dictionary)


@dataclass(frozen=True)
class HistoricalFiveYearAverageIndicators:
    """
    최근 5개 사업연도의 평균 지표 데이터 모델
    """
    start_fiscal_year: int
    end_fiscal_year: int
    
    average_revenue_growth_rate_percentage: Optional[float]
    average_operating_income_growth_rate_percentage: Optional[float]
    average_earnings_per_share_growth_rate_percentage: Optional[float]
    average_free_cash_flow_growth_rate_percentage: Optional[float]
    
    average_operating_profit_margin_percentage: Optional[float]
    average_return_on_equity_percentage: Optional[float]
    average_return_on_assets_percentage: Optional[float]
    average_return_on_invested_capital_percentage: Optional[float]
    
    average_debt_to_equity_ratio_percentage: Optional[float]
    average_current_ratio_percentage: Optional[float]
    average_interest_coverage_ratio: Optional[float]
    average_free_cash_flow_amount_krw: Optional[int]
    
    average_price_to_earnings_ratio: Optional[float]
    average_price_to_book_ratio: Optional[float]
    average_enterprise_value_to_ebitda_ratio: Optional[float]

    def to_dictionary(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dictionary(cls, data_dictionary: Dict[str, Any]) -> "HistoricalFiveYearAverageIndicators":
        return cls(**data_dictionary)


@dataclass(frozen=True)
class CompanyInvestmentIndicatorsSummary:
    """
    한 기업의 최신 연간 지표와 과거 5개년 평균 지표를 종합한 모델
    """
    stock_code: str
    company_name: str
    latest_fiscal_year: int
    latest_indicators: AnnualCalculatedIndicators
    historical_five_year_averages: HistoricalFiveYearAverageIndicators

    def to_dictionary(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dictionary(cls, data_dictionary: Dict[str, Any]) -> "CompanyInvestmentIndicatorsSummary":
        latest_dict = data_dictionary["latest_indicators"]
        historical_dict = data_dictionary["historical_five_year_averages"]
        return cls(
            stock_code=data_dictionary["stock_code"],
            company_name=data_dictionary["company_name"],
            latest_fiscal_year=data_dictionary["latest_fiscal_year"],
            latest_indicators=AnnualCalculatedIndicators.from_dictionary(latest_dict),
            historical_five_year_averages=HistoricalFiveYearAverageIndicators.from_dictionary(historical_dict),
        )
