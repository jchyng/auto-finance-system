"""
리포트 설명 및 포맷터 모듈 (Explainers & Formatters)

본 패키지는 평가 리포트를 사용자가 이해하기 쉬운 형태로 변환합니다.
- 금융 용어 사전: 초보 투자자를 위한 용어 해설
- 리포트 포맷터: JSON을 텍스트 리포트로 변환
- 규칙 1(투자 권유 금지) 준수: 모든 출력에서 매수/매도 권유 배제
"""

from src.explainers.financial_term_dictionary import FINANCIAL_TERM_DICTIONARY

__all__ = [
    "FINANCIAL_TERM_DICTIONARY",
]
