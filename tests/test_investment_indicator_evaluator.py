"""
투자지표 상태 판정 엔진 단위 테스트 (Investment Indicator Evaluator Tests)

pytest 기반 단위 테스트로 15개 지표 판정 로직의 정확성을 검증합니다.
- 성장성 지표 판정 테스트
- 수익성 지표 판정 테스트
- 재무건전성 지표 판정 테스트 (절대 기준)
- 밸류에이션 지표 판정 테스트
- 통합 평가 리포트 생성 테스트
"""

import json
from pathlib import Path

import pytest

from src.engines.investment_indicator_evaluator import (
    evaluate_revenue_growth_rate,
    evaluate_operating_income_growth_rate,
    evaluate_profitability_ratio,
    evaluate_debt_to_equity_ratio,
    evaluate_current_ratio,
    evaluate_interest_coverage_ratio,
    evaluate_free_cash_flow,
    evaluate_valuation_ratio,
    evaluate_all_indicators,
    generate_complete_evaluation_report,
)
from src.models.indicator_evaluation_models import (
    IndicatorEvaluationStatus,
)
from src.models.investment_indicator_models import (
    CompanyInvestmentIndicatorsSummary,
)
from src.models.financial_statement_models import (
    IndustryBenchmarkData,
)


# ============================================================================
# 1. 성장성 지표 판정 테스트
# ============================================================================

def test_evaluate_revenue_growth_rate_good():
    """매출액 성장률 '양호' 판정 테스트"""
    status, reason = evaluate_revenue_growth_rate(
        current_value=15.0,
        five_year_average=10.0,
        industry_average=12.0
    )
    
    assert status == IndicatorEvaluationStatus.GOOD
    assert "15.0%" in reason
    assert "10.0%" in reason
    assert "12.0%" in reason


def test_evaluate_revenue_growth_rate_caution():
    """매출액 성장률 '주의' 판정 테스트"""
    status, reason = evaluate_revenue_growth_rate(
        current_value=5.0,
        five_year_average=15.0,
        industry_average=20.0
    )
    
    assert status == IndicatorEvaluationStatus.CAUTION
    assert "20% 이상 낮습니다" in reason


def test_evaluate_revenue_growth_rate_normal():
    """매출액 성장률 '보통' 판정 테스트"""
    status, reason = evaluate_revenue_growth_rate(
        current_value=12.0,
        five_year_average=10.0,
        industry_average=15.0
    )
    
    assert status == IndicatorEvaluationStatus.NORMAL
    assert "근접합니다" in reason


def test_evaluate_revenue_growth_rate_not_applicable():
    """매출액 성장률 '판단불가' 테스트"""
    status, reason = evaluate_revenue_growth_rate(
        current_value=None,
        five_year_average=10.0,
        industry_average=12.0
    )
    
    assert status == IndicatorEvaluationStatus.NOT_APPLICABLE
    assert "데이터가 부족합니다" in reason


def test_evaluate_operating_income_turnaround_to_profit():
    """영업이익 흑자전환 테스트"""
    status, reason = evaluate_operating_income_growth_rate(
        current_value=None,
        turnaround_note="흑자전환",
        five_year_average=10.0,
        industry_average=12.0
    )
    
    assert status == IndicatorEvaluationStatus.GOOD
    assert "흑자전환" in reason


def test_evaluate_operating_income_turnaround_to_loss():
    """영업이익 적자전환 테스트"""
    status, reason = evaluate_operating_income_growth_rate(
        current_value=None,
        turnaround_note="적자전환",
        five_year_average=10.0,
        industry_average=12.0
    )
    
    assert status == IndicatorEvaluationStatus.CAUTION
    assert "적자전환" in reason


def test_evaluate_operating_income_continued_loss():
    """영업이익 적자지속 테스트"""
    status, reason = evaluate_operating_income_growth_rate(
        current_value=None,
        turnaround_note="적자지속",
        five_year_average=10.0,
        industry_average=12.0
    )
    
    assert status == IndicatorEvaluationStatus.CAUTION
    assert "영업손실이 지속" in reason or "적자지속" in reason


# ============================================================================
# 2. 수익성 지표 판정 테스트
# ============================================================================

def test_evaluate_profitability_ratio_good():
    """수익성 비율 '양호' 판정 테스트"""
    status, reason = evaluate_profitability_ratio(
        indicator_name_korean="영업이익률",
        current_value=15.0,
        five_year_average=12.0,
        industry_average=10.0,
        unit="%"
    )
    
    assert status == IndicatorEvaluationStatus.GOOD
    assert "15.0%" in reason
    assert "이상입니다" in reason


def test_evaluate_profitability_ratio_caution():
    """수익성 비율 '주의' 판정 테스트"""
    status, reason = evaluate_profitability_ratio(
        indicator_name_korean="ROE",
        current_value=5.0,
        five_year_average=15.0,
        industry_average=20.0,
        unit="%"
    )
    
    assert status == IndicatorEvaluationStatus.CAUTION
    assert "20% 이상 낮습니다" in reason


def test_evaluate_profitability_ratio_not_applicable():
    """수익성 비율 '판단불가' 테스트"""
    status, reason = evaluate_profitability_ratio(
        indicator_name_korean="ROA",
        current_value=None,
        five_year_average=10.0,
        industry_average=12.0,
        unit="%"
    )
    
    assert status == IndicatorEvaluationStatus.NOT_APPLICABLE
    assert "판정할 수 없습니다" in reason


# ============================================================================
# 3. 재무건전성 지표 판정 테스트 (절대 기준)
# ============================================================================

def test_evaluate_debt_to_equity_ratio_good():
    """부채비율 '양호' 판정 테스트 (100% 이하)"""
    status, reason = evaluate_debt_to_equity_ratio(
        current_value=85.0,
        five_year_average=90.0
    )
    
    assert status == IndicatorEvaluationStatus.GOOD
    assert "85.0%" in reason
    assert "권고 기준(100% 이하)" in reason


def test_evaluate_debt_to_equity_ratio_normal():
    """부채비율 '보통' 판정 테스트 (100~200%)"""
    status, reason = evaluate_debt_to_equity_ratio(
        current_value=150.0,
        five_year_average=140.0
    )
    
    assert status == IndicatorEvaluationStatus.NORMAL
    assert "150.0%" in reason
    assert "100~200%" in reason


def test_evaluate_debt_to_equity_ratio_caution():
    """부채비율 '주의' 판정 테스트 (200% 초과)"""
    status, reason = evaluate_debt_to_equity_ratio(
        current_value=250.0,
        five_year_average=220.0
    )
    
    assert status == IndicatorEvaluationStatus.CAUTION
    assert "250.0%" in reason
    assert "초과합니다" in reason


def test_evaluate_debt_to_equity_ratio_not_applicable():
    """부채비율 '판단불가' 테스트 (금융업)"""
    status, reason = evaluate_debt_to_equity_ratio(
        current_value=None,
        five_year_average=None
    )
    
    assert status == IndicatorEvaluationStatus.NOT_APPLICABLE
    assert "금융업" in reason or "데이터가 부족합니다" in reason


def test_evaluate_current_ratio_good():
    """유동비율 '양호' 판정 테스트 (150% 이상)"""
    status, reason = evaluate_current_ratio(
        current_value=200.0,
        five_year_average=180.0
    )
    
    assert status == IndicatorEvaluationStatus.GOOD
    assert "200.0%" in reason
    assert "안전 기준(150% 이상)" in reason


def test_evaluate_current_ratio_normal():
    """유동비율 '보통' 판정 테스트 (100~150%)"""
    status, reason = evaluate_current_ratio(
        current_value=120.0,
        five_year_average=110.0
    )
    
    assert status == IndicatorEvaluationStatus.NORMAL
    assert "120.0%" in reason
    assert "최소 기준(100% 이상)" in reason


def test_evaluate_current_ratio_caution():
    """유동비율 '주의' 판정 테스트 (100% 미만)"""
    status, reason = evaluate_current_ratio(
        current_value=80.0,
        five_year_average=90.0
    )
    
    assert status == IndicatorEvaluationStatus.CAUTION
    assert "80.0%" in reason
    assert "미달합니다" in reason


def test_evaluate_interest_coverage_ratio_good():
    """이자보상배율 '양호' 판정 테스트 (3.0배 이상)"""
    status, reason = evaluate_interest_coverage_ratio(
        current_value=5.0,
        is_debt_free=False,
        five_year_average=4.5
    )
    
    assert status == IndicatorEvaluationStatus.GOOD
    assert "5.0배" in reason
    assert "안전 기준(3.0배 이상)" in reason


def test_evaluate_interest_coverage_ratio_debt_free():
    """이자보상배율 '양호' 판정 테스트 (무차입)"""
    status, reason = evaluate_interest_coverage_ratio(
        current_value=None,
        is_debt_free=True,
        five_year_average=None
    )
    
    assert status == IndicatorEvaluationStatus.GOOD
    assert "무차입" in reason


def test_evaluate_interest_coverage_ratio_normal():
    """이자보상배율 '보통' 판정 테스트 (1.0~3.0배)"""
    status, reason = evaluate_interest_coverage_ratio(
        current_value=2.0,
        is_debt_free=False,
        five_year_average=2.5
    )
    
    assert status == IndicatorEvaluationStatus.NORMAL
    assert "2.0배" in reason
    assert "최소 기준(1.0배 이상)" in reason


def test_evaluate_interest_coverage_ratio_caution():
    """이자보상배율 '주의' 판정 테스트 (1.0배 미만)"""
    status, reason = evaluate_interest_coverage_ratio(
        current_value=0.5,
        is_debt_free=False,
        five_year_average=0.8
    )
    
    assert status == IndicatorEvaluationStatus.CAUTION
    assert "0.5배" in reason
    assert "잠재적 부실 위험" in reason


# ============================================================================
# 4. 밸류에이션 지표 판정 테스트
# ============================================================================

def test_evaluate_valuation_ratio_lower_than_average():
    """밸류에이션 비율 '과거/업종 대비 낮음' 테스트"""
    status, reason = evaluate_valuation_ratio(
        indicator_name_korean="PER",
        current_value=10.0,
        five_year_average=15.0,
        industry_average=20.0,
        unit="배"
    )
    
    assert status == IndicatorEvaluationStatus.NORMAL
    assert "10.0배" in reason
    assert "낮습니다" in reason


def test_evaluate_valuation_ratio_higher_than_average():
    """밸류에이션 비율 '과거/업종 대비 높음' 테스트"""
    status, reason = evaluate_valuation_ratio(
        indicator_name_korean="PBR",
        current_value=25.0,
        five_year_average=15.0,
        industry_average=18.0,
        unit="배"
    )
    
    assert status == IndicatorEvaluationStatus.NORMAL
    assert "25.0배" in reason
    assert "높습니다" in reason


def test_evaluate_valuation_ratio_near_average():
    """밸류에이션 비율 '평균 수준' 테스트"""
    status, reason = evaluate_valuation_ratio(
        indicator_name_korean="EV/EBITDA",
        current_value=15.5,
        five_year_average=15.0,
        industry_average=None,
        unit="배"
    )
    
    assert status == IndicatorEvaluationStatus.NORMAL
    assert "15.5배" in reason
    assert "근접합니다" in reason


def test_evaluate_valuation_ratio_not_applicable():
    """밸류에이션 비율 '판단불가' 테스트"""
    status, reason = evaluate_valuation_ratio(
        indicator_name_korean="PER",
        current_value=None,
        five_year_average=15.0,
        industry_average=20.0,
        unit="배"
    )
    
    assert status == IndicatorEvaluationStatus.NOT_APPLICABLE
    assert "판정할 수 없습니다" in reason


# ============================================================================
# 5. 실제 데이터 기반 통합 테스트
# ============================================================================

@pytest.fixture
def samsung_indicators_data():
    """삼성전자 지표 데이터 로드"""
    data_path = Path("data/metrics/005930_indicators.json")
    
    if not data_path.exists():
        pytest.skip("삼성전자 지표 데이터 파일이 없습니다")
    
    with open(data_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    return CompanyInvestmentIndicatorsSummary.from_dictionary(data)


@pytest.fixture
def samsung_industry_data():
    """삼성전자 업종 벤치마크 데이터 로드"""
    data_path = Path("data/raw/005930_industry.json")
    
    if not data_path.exists():
        pytest.skip("삼성전자 업종 데이터 파일이 없습니다")
    
    with open(data_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    
    benchmark_dict = data.get("industry_benchmark", data)
    return IndustryBenchmarkData.from_dictionary(benchmark_dict)


def test_evaluate_all_indicators_with_real_data(samsung_indicators_data, samsung_industry_data):
    """실제 삼성전자 데이터로 15개 지표 평가 테스트"""
    evaluations = evaluate_all_indicators(
        samsung_indicators_data,
        samsung_industry_data,
        samsung_indicators_data.latest_fiscal_year
    )
    
    # 15개 지표 모두 평가되었는지 확인
    assert len(evaluations) == 15
    
    # 각 지표가 올바른 카테고리를 가지는지 확인
    categories = [e.indicator_category for e in evaluations]
    assert "성장성" in [str(c.value) for c in categories]
    assert "수익성" in [str(c.value) for c in categories]
    assert "재무건전성" in [str(c.value) for c in categories]
    assert "밸류에이션" in [str(c.value) for c in categories]
    
    # 모든 지표가 판정 상태를 가지는지 확인
    for evaluation in evaluations:
        assert evaluation.evaluation_status in [
            IndicatorEvaluationStatus.GOOD,
            IndicatorEvaluationStatus.NORMAL,
            IndicatorEvaluationStatus.CAUTION,
            IndicatorEvaluationStatus.NOT_APPLICABLE
        ]
        assert len(evaluation.evaluation_reason_description) > 0
        assert len(evaluation.calculation_formula_description) > 0


def test_generate_complete_evaluation_report_with_real_data(samsung_indicators_data, samsung_industry_data):
    """실제 삼성전자 데이터로 최종 리포트 생성 테스트"""
    report = generate_complete_evaluation_report(
        samsung_indicators_data,
        samsung_industry_data,
        closing_price=72000,
        market_cap=429_800_000_000_000
    )
    
    # 기본 정보 확인
    assert report.stock_code == "005930"
    assert report.company_name == "삼성전자"
    assert report.industry_classification_name == "반도체와반도체장비"
    assert report.fiscal_year == samsung_indicators_data.latest_fiscal_year
    
    # 평가 결과 확인
    assert len(report.evaluations) == 15
    
    # 요약 텍스트 확인
    assert len(report.plain_korean_summary_text) > 0
    assert "삼성전자" in report.plain_korean_summary_text
    
    # 용어 사전 확인
    assert len(report.financial_term_glossary_dictionary) > 0
    assert "ROE" in report.financial_term_glossary_dictionary
    assert "PER" in report.financial_term_glossary_dictionary
    
    # 면책 문구 확인
    assert len(report.disclaimer_text) > 0
    assert "투자 권유" in report.disclaimer_text or "추천" in report.disclaimer_text


def test_report_json_serialization(samsung_indicators_data, samsung_industry_data):
    """리포트 JSON 직렬화/역직렬화 테스트"""
    report = generate_complete_evaluation_report(
        samsung_indicators_data,
        samsung_industry_data,
        closing_price=72000,
        market_cap=429_800_000_000_000
    )
    
    # JSON으로 변환
    report_dict = report.to_dictionary()
    
    # 기본 필드 확인
    assert "stock_code" in report_dict
    assert "company_name" in report_dict
    assert "evaluations" in report_dict
    assert isinstance(report_dict["evaluations"], list)
    assert len(report_dict["evaluations"]) == 15
    
    # 역직렬화 테스트
    from src.models.indicator_evaluation_models import CompleteCompanyEvaluationReport
    restored_report = CompleteCompanyEvaluationReport.from_dictionary(report_dict)
    
    assert restored_report.stock_code == report.stock_code
    assert restored_report.company_name == report.company_name
    assert len(restored_report.evaluations) == len(report.evaluations)


# ============================================================================
# 6. CLI 실행 통합 테스트
# ============================================================================

def test_cli_execution_with_samsung_data():
    """CLI 단독 실행 테스트 (삼성전자 데이터)"""
    import subprocess
    import sys
    
    metrics_path = Path("data/metrics/005930_indicators.json")
    industry_path = Path("data/raw/005930_industry.json")
    output_path = Path("data/evaluation/test_005930_evaluation.json")
    
    if not metrics_path.exists() or not industry_path.exists():
        pytest.skip("테스트 데이터 파일이 없습니다")
    
    # 기존 출력 파일 삭제
    if output_path.exists():
        output_path.unlink()
    
    # CLI 실행
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.engines.investment_indicator_evaluator",
            "--metrics",
            str(metrics_path),
            "--industry",
            str(industry_path),
            "--output",
            str(output_path)
        ],
        capture_output=True,
        text=True,
        encoding="utf-8"
    )
    
    # 실행 성공 확인 (exit code로 판단)
    assert result.returncode == 0, f"CLI 실행 실패 (exit code: {result.returncode})\nstderr: {result.stderr}\nstdout: {result.stdout}"
    
    # 출력 파일 생성 확인
    assert output_path.exists(), "출력 파일이 생성되지 않았습니다"
    
    # 출력 파일 내용 확인
    with open(output_path, "r", encoding="utf-8") as file:
        output_data = json.load(file)
    
    assert "stock_code" in output_data
    assert output_data["stock_code"] == "005930"
    assert "evaluations" in output_data
    assert len(output_data["evaluations"]) == 15
    
    # 평가 결과 샘플 확인
    first_eval = output_data["evaluations"][0]
    assert "indicator_category" in first_eval
    assert "evaluation_status" in first_eval
    assert "evaluation_reason_description" in first_eval
    
    # 테스트 파일 정리
    output_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
