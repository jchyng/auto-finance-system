"""
투자 지표 상태 판정 데이터 모델 (Indicator Evaluation Models)

본 모듈은 각 지표의 객관적 판정 상태(양호, 보통, 주의, 판단불가)와
수치적 근거, 비교 결과, 최종 리포트의 데이터 규격을 정의합니다.
규칙 1(투자 권유 금지) 및 규칙 6(명확한 명명)을 철저히 준수합니다.
"""

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class IndicatorEvaluationStatus(str, Enum):
    """지표의 4단계 객관적 상태"""
    GOOD = "양호"
    NORMAL = "보통"
    CAUTION = "주의"
    NOT_APPLICABLE = "판단불가"


class IndicatorCategory(str, Enum):
    """지표의 4대 분류"""
    GROWTH = "성장성"
    PROFITABILITY = "수익성"
    FINANCIAL_HEALTH = "재무건전성"
    VALUATION = "밸류에이션"


@dataclass(frozen=True)
class SingleIndicatorEvaluation:
    """
    개별 지표의 상태 판정 및 비교 결과
    """
    indicator_category: IndicatorCategory                            # 지표 분류 (성장성/수익성/재무건전성/밸류에이션)
    indicator_name_korean: str                                       # 한글 지표명 (예: "부채비율")
    indicator_name_english: str                                      # 영문 지표명 (예: "Debt to Equity Ratio")
    
    current_value_formatted: str                                     # 현재값 (예: "26.4%", "12.3배", "데이터 부족")
    historical_five_year_average_formatted: str                      # 5개년 평균 (예: "35.2%", "해당 없음")
    industry_benchmark_average_formatted: str                        # 동일 업종 평균 (예: "100.0% 이하 권고선", "24.1배")
    
    evaluation_status: IndicatorEvaluationStatus                     # 상태 (양호/보통/주의/판단불가)
    evaluation_reason_description: str                               # 객관적 판정 근거 (임의 판단 배제된 수치적 사실)
    calculation_formula_description: str                             # 사용자가 검증할 수 있는 계산 공식
    data_source_and_base_date_description: str                       # 데이터 출처 및 결산 기준일

    def to_dictionary(self) -> Dict[str, Any]:
        result = asdict(self)
        result["indicator_category"] = self.indicator_category.value
        result["evaluation_status"] = self.evaluation_status.value
        return result

    @classmethod
    def from_dictionary(cls, data_dictionary: Dict[str, Any]) -> "SingleIndicatorEvaluation":
        return cls(
            indicator_category=IndicatorCategory(data_dictionary["indicator_category"]),
            indicator_name_korean=data_dictionary["indicator_name_korean"],
            indicator_name_english=data_dictionary["indicator_name_english"],
            current_value_formatted=data_dictionary["current_value_formatted"],
            historical_five_year_average_formatted=data_dictionary["historical_five_year_average_formatted"],
            industry_benchmark_average_formatted=data_dictionary["industry_benchmark_average_formatted"],
            evaluation_status=IndicatorEvaluationStatus(data_dictionary["evaluation_status"]),
            evaluation_reason_description=data_dictionary["evaluation_reason_description"],
            calculation_formula_description=data_dictionary["calculation_formula_description"],
            data_source_and_base_date_description=data_dictionary["data_source_and_base_date_description"],
        )


@dataclass(frozen=True)
class CompleteCompanyEvaluationReport:
    """
    기업 투자 검토 자료 최종 완성 리포트 모델
    """
    stock_code: str                                                  # 종목코드
    company_name: str                                                # 기업명
    industry_classification_name: str                                # 업종명
    fiscal_year: int                                                 # 분석 사업연도
    
    closing_price_krw: int                                           # 분석 시점 주가
    market_capitalization_krw: int                                   # 시가총액
    
    evaluations: List[SingleIndicatorEvaluation]                     # 15개 지표 판정 결과 목록
    plain_korean_summary_text: str                                   # 객관적 사실 요약 문장 (매수/매도 권유 배제)
    financial_term_glossary_dictionary: Dict[str, str]               # 초보자용 용어 해설 매핑
    disclaimer_text: str                                             # 면책 고지

    def to_dictionary(self) -> Dict[str, Any]:
        result = asdict(self)
        result["evaluations"] = [item.to_dictionary() for item in self.evaluations]
        return result

    @classmethod
    def from_dictionary(cls, data_dictionary: Dict[str, Any]) -> "CompleteCompanyEvaluationReport":
        evaluations_list = [
            SingleIndicatorEvaluation.from_dictionary(item) for item in data_dictionary["evaluations"]
        ]
        return cls(
            stock_code=data_dictionary["stock_code"],
            company_name=data_dictionary["company_name"],
            industry_classification_name=data_dictionary["industry_classification_name"],
            fiscal_year=data_dictionary["fiscal_year"],
            closing_price_krw=data_dictionary["closing_price_krw"],
            market_capitalization_krw=data_dictionary["market_capitalization_krw"],
            evaluations=evaluations_list,
            plain_korean_summary_text=data_dictionary["plain_korean_summary_text"],
            financial_term_glossary_dictionary=data_dictionary["financial_term_glossary_dictionary"],
            disclaimer_text=data_dictionary["disclaimer_text"],
        )
