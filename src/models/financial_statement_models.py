"""
재무제표 데이터 모델 (Financial Statement Data Models)

본 모듈은 원본 공시 재무제표 및 표준화 정제된 재무제표의 엄격한 데이터 규격을 정의합니다.
규칙 6에 따라 모든 필드명은 축약 없이 완전한 설명적 명칭과 단위(KRW 등)를 포함합니다.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class NormalizedFinancialStatement:
    """
    15개 지표 계산에 사용되는 표준 정제 연간 재무제표 데이터 모델
    """
    stock_code: str                                        # 종목코드 (예: "005930")
    company_name: str                                      # 기업명 (예: "삼성전자")
    fiscal_year: int                                       # 사업연도 (예: 2023)
    
    # 손익계산서 항목 (원 단위)
    revenue_krw: int                                       # 매출액
    operating_income_krw: int                              # 영업이익
    controlling_interest_net_income_krw: int               # 지배주주순이익
    income_tax_expense_krw: int                            # 법인세비용
    profit_before_tax_krw: int                             # 법인세차감전순이익
    
    # 재무상태표 항목 (원 단위)
    total_assets_krw: int                                  # 자산총계
    total_liabilities_krw: int                             # 부채총계
    controlling_interest_equity_krw: int                   # 지배주주자본총계
    current_assets_krw: Optional[int]                      # 유동자산 (금융업종은 미구분으로 None 가능)
    current_liabilities_krw: Optional[int]                 # 유동부채 (금융업종은 미구분으로 None 가능)
    
    # 차입금 및 현금성자산 (EV/EBITDA, 투하자본 산출용, 원 단위)
    short_term_borrowings_krw: int                         # 단기차입금
    long_term_borrowings_krw: int                          # 장기차입금 (유동성장기부채 포함)
    cash_and_cash_equivalents_krw: int                     # 현금및현금성자산
    
    # 현금흐름표 및 감가상각 항목 (FCF, EBITDA 산출용, 원 단위)
    # None = 계정 미매칭(결측). 0으로 치환하지 않음(무차입·FCF=0 오판 방지)
    operating_cash_flow_krw: Optional[int]                 # 영업활동현금흐름
    acquisition_of_tangible_assets_krw: Optional[int]      # 유형자산의취득 (CAPEX, DART는 음수 유출일 수 있음)
    acquisition_of_intangible_assets_krw: Optional[int]    # 무형자산의취득 (CAPEX)
    tangible_asset_depreciation_krw: int                   # 유형자산감가상각비
    intangible_asset_amortization_krw: int                 # 무형자산상각비
    interest_expense_krw: Optional[int]                    # 이자비용 (None=미매칭, 0=무차입)
    
    # 메타데이터
    is_financial_industry: bool                            # 금융업종 여부 (은행/증권/보험 등)
    data_source_name: str                                  # 데이터 출처 (예: "DART 전자공시")
    adjusted_basic_shares_outstanding: Optional[int] = None # 수정기본EPS 역산 주식수

    def to_dictionary(self) -> Dict[str, Any]:
        """데이터 클래스를 딕셔너리로 변환합니다."""
        return asdict(self)

    @classmethod
    def from_dictionary(cls, data_dictionary: Dict[str, Any]) -> "NormalizedFinancialStatement":
        """딕셔너리로부터 데이터 클래스 인스턴스를 복원합니다."""
        return cls(**data_dictionary)


@dataclass(frozen=True)
class StockPriceAndMarketCapData:
    """
    주가 및 시가총액 데이터 모델 (KRX 기준)
    """
    stock_code: str                                        # 종목코드
    company_name: str                                      # 기업명
    closing_price_krw: int                                 # 종가
    market_capitalization_krw: int                         # 시가총액
    total_shares_outstanding: int                          # 상장주식수
    base_trading_date: str                                 # 거래기준일자 (예: "2024-03-29")
    data_source_name: str                                  # 출처 (예: "KRX 정보데이터시스템")

    def to_dictionary(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dictionary(cls, data_dictionary: Dict[str, Any]) -> "StockPriceAndMarketCapData":
        return cls(**data_dictionary)


@dataclass(frozen=True)
class IndustryBenchmarkData:
    """
    동일 업종 벤치마크 지표 모델 (KRX / WICS 기준)
    """
    industry_classification_code: str                      # 업종 분류 코드
    industry_classification_name: str                      # 업종명 (예: "반도체와반도체장비")
    average_operating_profit_margin_percentage: Optional[float]  # 업종 평균 영업이익률 (%)
    average_return_on_equity_percentage: Optional[float]         # 업종 평균 ROE (%)
    average_debt_to_equity_ratio_percentage: Optional[float]     # 업종 평균 부채비율 (%)
    average_price_to_earnings_ratio: Optional[float]             # 업종 평균 PER (배)
    average_price_to_book_ratio: Optional[float]                 # 업종 평균 PBR (배)
    base_date: str                                         # 기준일자
    data_source_name: str                                  # 출처 (예: "KRX 업종 지수")

    def to_dictionary(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dictionary(cls, data_dictionary: Dict[str, Any]) -> "IndustryBenchmarkData":
        return cls(**data_dictionary)
