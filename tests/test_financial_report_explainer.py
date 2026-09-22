"""
리포트 생성기 단위 테스트 (Financial Report Explainer Tests)

pytest 기반 단위 테스트로 리포트 생성 로직의 정확성을 검증합니다.
- 금융 용어 사전 테스트
- 투자 권유 표현 필터링 테스트
- 텍스트 리포트 포맷팅 테스트
- CLI 실행 테스트
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.explainers.financial_term_dictionary import (
    FINANCIAL_TERM_DICTIONARY,
    get_term_explanation,
    get_all_terms,
    format_term_glossary_section,
)
from src.explainers.financial_report_explainer import (
    check_prohibited_expressions,
    format_status_badge,
    generate_text_report,
)
from src.models.indicator_evaluation_models import (
    CompleteCompanyEvaluationReport,
    IndicatorEvaluationStatus,
)


# ============================================================================
# 1. 금융 용어 사전 테스트
# ============================================================================

def test_financial_term_dictionary_exists():
    """금융 용어 사전이 정의되어 있는지 테스트"""
    assert len(FINANCIAL_TERM_DICTIONARY) > 0
    assert "ROE" in FINANCIAL_TERM_DICTIONARY
    assert "PER" in FINANCIAL_TERM_DICTIONARY
    assert "부채비율" in FINANCIAL_TERM_DICTIONARY


def test_financial_term_dictionary_completeness():
    """15개 핵심 지표가 모두 사전에 포함되어 있는지 테스트"""
    required_terms = [
        "매출액 성장률", "영업이익 성장률", "EPS", "FCF",
        "영업이익률", "ROE", "ROA", "ROIC",
        "부채비율", "유동비율", "이자보상배율",
        "PER", "PBR", "EV/EBITDA"
    ]
    
    for term in required_terms:
        assert term in FINANCIAL_TERM_DICTIONARY, f"{term}이 사전에 없습니다"
        assert len(FINANCIAL_TERM_DICTIONARY[term]) > 10, f"{term}의 설명이 너무 짧습니다"


def test_get_term_explanation():
    """용어 설명 조회 함수 테스트"""
    roe_explanation = get_term_explanation("ROE")
    assert len(roe_explanation) > 0
    assert "자기자본" in roe_explanation
    
    # 존재하지 않는 용어
    invalid_explanation = get_term_explanation("INVALID_TERM")
    assert invalid_explanation == ""


def test_get_all_terms():
    """전체 용어 사전 조회 함수 테스트"""
    all_terms = get_all_terms()
    assert isinstance(all_terms, dict)
    assert len(all_terms) == len(FINANCIAL_TERM_DICTIONARY)


def test_format_term_glossary_section():
    """용어 사전 섹션 포맷팅 테스트"""
    glossary_text = format_term_glossary_section()
    
    assert "[금융 용어 해설]" in glossary_text
    assert "ROE" in glossary_text
    assert "PER" in glossary_text
    assert "부채비율" in glossary_text


# ============================================================================
# 2. 투자 권유 표현 필터링 테스트
# ============================================================================

def test_check_prohibited_expressions_clean_text():
    """권유 표현이 없는 깨끗한 텍스트 테스트"""
    clean_text = "당기 영업이익률은 10.5%이며, 5년 평균 12.3%보다 낮습니다."
    violations = check_prohibited_expressions(clean_text)
    assert len(violations) == 0


def test_check_prohibited_expressions_with_violations():
    """권유 표현이 포함된 텍스트 테스트"""
    violation_texts = [
        "매수 추천합니다",
        "매도 권유드립니다",
        "저평가 확정입니다",
        "좋은 기업입니다",
        "적극 추천합니다",
    ]
    
    for text in violation_texts:
        violations = check_prohibited_expressions(text)
        assert len(violations) > 0, f"'{text}'에서 권유 표현을 감지하지 못했습니다"


# ============================================================================
# 3. 포맷팅 함수 테스트
# ============================================================================

def test_format_status_badge():
    """상태 뱃지 포맷팅 테스트"""
    assert format_status_badge(IndicatorEvaluationStatus.GOOD) == "[양호]"
    assert format_status_badge(IndicatorEvaluationStatus.NORMAL) == "[보통]"
    assert format_status_badge(IndicatorEvaluationStatus.CAUTION) == "[주의]"
    assert format_status_badge(IndicatorEvaluationStatus.NOT_APPLICABLE) == "[판단불가]"


# ============================================================================
# 4. 실제 데이터 기반 통합 테스트
# ============================================================================

@pytest.fixture
def samsung_evaluation_report():
    """삼성전자 평가 리포트 로드"""
    data_path = Path("data/evaluation/005930_evaluation.json")
    
    if not data_path.exists():
        pytest.skip("삼성전자 평가 데이터 파일이 없습니다")
    
    with open(data_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    return CompleteCompanyEvaluationReport.from_dictionary(data)


def test_generate_text_report_with_real_data(samsung_evaluation_report):
    """실제 삼성전자 데이터로 텍스트 리포트 생성 테스트"""
    report_text = generate_text_report(samsung_evaluation_report)
    
    # 기본 구조 확인
    assert "투자 검토 자료" in report_text
    assert "삼성전자" in report_text
    assert "005930" in report_text
    
    # 4개 분류 헤더 확인
    assert "1. 성장성 지표" in report_text
    assert "2. 수익성 지표" in report_text
    assert "3. 재무건전성 지표" in report_text
    assert "4. 밸류에이션 지표" in report_text
    
    # 판정 상태 뱃지 확인
    assert "[양호]" in report_text or "[보통]" in report_text or "[주의]" in report_text
    
    # 용어 사전 확인
    assert "[금융 용어 해설]" in report_text
    assert "ROE" in report_text
    assert "PER" in report_text
    
    # 면책 고지 확인
    assert "면책 고지" in report_text
    assert "투자" in report_text


def test_generate_text_report_without_glossary(samsung_evaluation_report):
    """용어 사전 제외 옵션 테스트"""
    report_text = generate_text_report(
        samsung_evaluation_report,
        include_glossary=False
    )
    
    # 용어 사전 섹션이 없어야 함
    assert "[금융 용어 해설]" not in report_text
    
    # 나머지 내용은 있어야 함
    assert "투자 검토 자료" in report_text
    assert "삼성전자" in report_text


def test_generate_text_report_without_summary(samsung_evaluation_report):
    """사실 요약 제외 옵션 테스트"""
    report_text = generate_text_report(
        samsung_evaluation_report,
        include_summary=False
    )
    
    # 분석 요약 섹션이 없어야 함
    assert "[분석 요약]" not in report_text
    
    # 나머지 내용은 있어야 함
    assert "투자 검토 자료" in report_text
    assert "1. 성장성 지표" in report_text


def test_report_text_no_prohibited_expressions(samsung_evaluation_report):
    """생성된 리포트에 투자 권유 표현이 없는지 테스트"""
    report_text = generate_text_report(samsung_evaluation_report)
    
    # 면책 고지 섹션 제외 (면책 고지에는 "권유하지 않습니다"라는 표현이 정당하게 포함됨)
    disclaimer_start = report_text.find("면책 고지")
    if disclaimer_start != -1:
        report_without_disclaimer = report_text[:disclaimer_start]
    else:
        report_without_disclaimer = report_text
    
    violations = check_prohibited_expressions(report_without_disclaimer)
    assert len(violations) == 0, f"리포트에 권유 표현이 발견되었습니다: {violations}"


# ============================================================================
# 5. 다양한 기업 데이터 테스트
# ============================================================================

@pytest.mark.parametrize("stock_code,company_name", [
    ("005930", "삼성전자"),
    ("005380", "현대자동차"),
    ("055550", "신한지주"),
])
def test_generate_report_for_multiple_companies(stock_code, company_name):
    """여러 기업의 리포트 생성 테스트"""
    data_path = Path(f"data/evaluation/{stock_code}_evaluation.json")
    
    if not data_path.exists():
        pytest.skip(f"{company_name} 평가 데이터 파일이 없습니다")
    
    with open(data_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    report = CompleteCompanyEvaluationReport.from_dictionary(data)
    report_text = generate_text_report(report)
    
    # 기업명 확인
    assert company_name in report_text
    assert stock_code in report_text
    
    # 15개 지표 평가 확인
    assert len(report.evaluations) == 15
    
    # 투자 권유 표현 부재 확인 (면책 고지 제외)
    disclaimer_start = report_text.find("면책 고지")
    if disclaimer_start != -1:
        report_without_disclaimer = report_text[:disclaimer_start]
    else:
        report_without_disclaimer = report_text
    
    violations = check_prohibited_expressions(report_without_disclaimer)
    assert len(violations) == 0


def test_financial_industry_special_case():
    """금융업 예외 처리 확인 (신한지주)"""
    data_path = Path("data/evaluation/055550_evaluation.json")
    
    if not data_path.exists():
        pytest.skip("신한지주 평가 데이터 파일이 없습니다")
    
    with open(data_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    report = CompleteCompanyEvaluationReport.from_dictionary(data)
    report_text = generate_text_report(report)
    
    # 금융업 특성 언급 확인
    assert "금융업" in report_text or "판단불가" in report_text


# ============================================================================
# 6. CLI 실행 통합 테스트
# ============================================================================

def test_cli_execution_with_samsung_data():
    """CLI 단독 실행 테스트 (삼성전자 데이터)"""
    input_path = Path("data/evaluation/005930_evaluation.json")
    output_path = Path("reports/test_005930_report.txt")
    
    if not input_path.exists():
        pytest.skip("테스트 데이터 파일이 없습니다")
    
    # 기존 출력 파일 삭제
    if output_path.exists():
        output_path.unlink()
    
    # CLI 실행
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.explainers.financial_report_explainer",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--format",
            "text"
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    )
    
    # 실행 성공 확인
    assert result.returncode == 0, f"CLI 실행 실패 (exit code: {result.returncode})"
    
    # 출력 파일 생성 확인
    assert output_path.exists(), "출력 파일이 생성되지 않았습니다"
    
    # 출력 파일 내용 확인
    with open(output_path, "r", encoding="utf-8") as file:
        report_text = file.read()
    
    assert "투자 검토 자료" in report_text
    assert "삼성전자" in report_text
    assert "005930" in report_text
    
    # 테스트 파일 정리
    output_path.unlink()


def test_cli_execution_with_no_glossary_option():
    """CLI 용어 사전 제외 옵션 테스트"""
    input_path = Path("data/evaluation/005930_evaluation.json")
    output_path = Path("reports/test_005930_no_glossary.txt")
    
    if not input_path.exists():
        pytest.skip("테스트 데이터 파일이 없습니다")
    
    # 기존 출력 파일 삭제
    if output_path.exists():
        output_path.unlink()
    
    # CLI 실행 (용어 사전 제외)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.explainers.financial_report_explainer",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--no-glossary"
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    )
    
    # 실행 성공 확인
    assert result.returncode == 0
    assert output_path.exists()
    
    # 용어 사전이 없는지 확인
    with open(output_path, "r", encoding="utf-8") as file:
        report_text = file.read()
    
    assert "[금융 용어 해설]" not in report_text
    
    # 테스트 파일 정리
    output_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
