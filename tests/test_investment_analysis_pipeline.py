"""
투자 분석 파이프라인 및 CLI 통합 테스트 (Investment Analysis Pipeline Tests)

모듈 7(전체 파이프라인 및 CLI)의 기능 및 규칙 준수 여부를 검증합니다.
- 삼성전자(005930), 현대자동차(005380), 신한지주(055550) 대상 파이프라인 실행
- 중간 산출물(JSON) 및 최종 리포트(TXT/JSON) 저장 검증
- 금융업(신한지주) 예외 처리 검증
- 투자 권유 표현 부재(규칙 1) 검증
- CLI 단독 실행 및 옵션 동작 검증
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.investment_analysis_pipeline import (
    InvestmentAnalysisPipelineResult,
    run_investment_analysis_pipeline,
)
from src.explainers.financial_report_explainer import check_prohibited_expressions
from src.models.indicator_evaluation_models import IndicatorEvaluationStatus


# ============================================================================
# 1. 기업별 파이프라인 통합 실행 테스트
# ============================================================================

def test_pipeline_execution_samsung_electronics(tmp_path):
    """삼성전자 대상 파이프라인 실행 및 결과 모델 무결성 테스트"""
    output_report_file = tmp_path / "005930_report.txt"

    result = run_investment_analysis_pipeline(
        stock_code="005930",
        fiscal_year=2023,
        number_of_years=5,
        output_report_file_path=str(output_report_file),
        use_fixture_fallback=True,
    )

    assert isinstance(result, InvestmentAnalysisPipelineResult)
    assert result.stock_code == "005930"
    assert result.company_name == "삼성전자"
    assert result.fiscal_year == 2023

    # 수집 및 계산 데이터 확인
    assert len(result.financial_statements) == 5
    assert result.stock_price_data.closing_price_krw > 0
    assert result.indicators_summary.latest_fiscal_year == 2023
    assert len(result.evaluation_report.evaluations) == 15

    # 출력 파일 생성 및 내용 확인
    assert output_report_file.exists()
    content = output_report_file.read_text(encoding="utf-8")
    assert "투자 검토 자료" in content
    assert "삼성전자" in content
    assert "005930" in content
    assert "[금융 용어 해설]" in content

    # 규칙 1: 투자 권유 표현 부재 확인 (면책 고지 제외)
    disclaimer_start = content.find("면책 고지")
    content_to_check = content[:disclaimer_start] if disclaimer_start != -1 else content
    violations = check_prohibited_expressions(content_to_check)
    assert len(violations) == 0, f"투자 권유 표현 감지: {violations}"


def test_pipeline_execution_hyundai_motor(tmp_path):
    """현대자동차 대상 파이프라인 실행 테스트"""
    output_report_file = tmp_path / "005380_report.txt"

    result = run_investment_analysis_pipeline(
        stock_code="005380",
        fiscal_year=2023,
        number_of_years=5,
        output_report_file_path=str(output_report_file),
        use_fixture_fallback=True,
    )

    assert result.stock_code == "005380"
    assert result.company_name == "현대자동차"
    assert len(result.evaluation_report.evaluations) == 15

    content = output_report_file.read_text(encoding="utf-8")
    assert "현대자동차" in content
    assert "005380" in content

    disclaimer_start = content.find("면책 고지")
    content_to_check = content[:disclaimer_start] if disclaimer_start != -1 else content
    violations = check_prohibited_expressions(content_to_check)
    assert len(violations) == 0


def test_pipeline_execution_shinhan_financial_industry_exception(tmp_path):
    """금융업(신한지주) 예외 처리 검증 테스트"""
    output_report_file = tmp_path / "055550_report.txt"

    result = run_investment_analysis_pipeline(
        stock_code="055550",
        fiscal_year=2023,
        number_of_years=5,
        output_report_file_path=str(output_report_file),
        use_fixture_fallback=True,
    )

    assert result.stock_code == "055550"
    assert result.company_name == "신한지주"

    # 금융업 특성으로 인한 판단불가 지표 확인
    evaluations_dict = {
        evaluation.indicator_name_korean: evaluation
        for evaluation in result.evaluation_report.evaluations
    }

    # 부채비율, 유동비율, EV/EBITDA는 금융업 특성상 판단불가
    assert evaluations_dict["부채비율"].evaluation_status == IndicatorEvaluationStatus.NOT_APPLICABLE
    assert evaluations_dict["유동비율"].evaluation_status == IndicatorEvaluationStatus.NOT_APPLICABLE
    assert evaluations_dict["EV/EBITDA"].evaluation_status == IndicatorEvaluationStatus.NOT_APPLICABLE

    content = output_report_file.read_text(encoding="utf-8")
    assert "신한지주" in content
    assert "판단불가" in content


# ============================================================================
# 2. 파이프라인 옵션 및 산출물 테스트
# ============================================================================

def test_pipeline_save_intermediate_artifacts(tmp_path):
    """중간 산출물(JSON) 저장 옵션 동작 테스트"""
    artifacts_dir = tmp_path / "artifacts"

    result = run_investment_analysis_pipeline(
        stock_code="005930",
        save_intermediate_artifacts=True,
        artifacts_directory=str(artifacts_dir),
        use_fixture_fallback=True,
    )

    saved_paths = result.saved_artifact_file_paths
    assert "normalized_financials" in saved_paths
    assert "stock_price" in saved_paths
    assert "calculated_metrics" in saved_paths
    assert "evaluation_report" in saved_paths

    for artifact_name, file_path_str in saved_paths.items():
        artifact_path = Path(file_path_str)
        assert artifact_path.exists(), f"산출물 파일 누락: {artifact_name}"
        with open(artifact_path, "r", encoding="utf-8") as file:
            loaded_json = json.load(file)
            assert isinstance(loaded_json, dict)


def test_pipeline_json_format_output(tmp_path):
    """JSON 리포트 출력 포맷 테스트"""
    output_json_file = tmp_path / "005930_report.json"

    result = run_investment_analysis_pipeline(
        stock_code="005930",
        output_report_file_path=str(output_json_file),
        report_format="json",
        use_fixture_fallback=True,
    )

    assert output_json_file.exists()
    with open(output_json_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    assert data["stock_code"] == "005930"
    assert data["company_name"] == "삼성전자"
    assert "evaluations" in data
    assert len(data["evaluations"]) == 15


def test_pipeline_options_no_glossary_and_no_summary():
    """용어사전 및 요약문 제외 옵션 테스트"""
    result = run_investment_analysis_pipeline(
        stock_code="005930",
        include_glossary=False,
        include_summary=False,
        use_fixture_fallback=True,
    )

    report_text = result.report_text_content
    assert "[금융 용어 해설]" not in report_text
    assert "[분석 요약]" not in report_text
    assert "투자 검토 자료" in report_text
    assert "1. 성장성 지표" in report_text


# ============================================================================
# 3. CLI 통합 실행 테스트
# ============================================================================

def test_cli_execution_basic(tmp_path):
    """CLI 기본 실행 및 리포트 파일 생성 테스트"""
    output_file = tmp_path / "cli_samsung_report.txt"

    process_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.investment_analysis_cli",
            "--ticker",
            "005930",
            "--output",
            str(output_file),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )

    assert process_result.returncode == 0, f"CLI 실패: {process_result.stderr}"
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "삼성전자" in content
    assert "투자 검토 자료" in content


def test_cli_execution_json_format_and_intermediate(tmp_path):
    """CLI JSON 포맷 및 중간 산출물 저장 옵션 테스트"""
    output_file = tmp_path / "cli_hyundai_report.json"

    process_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.investment_analysis_cli",
            "--ticker",
            "005380",
            "--output",
            str(output_file),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )

    assert process_result.returncode == 0
    assert output_file.exists()
    with open(output_file, "r", encoding="utf-8") as file:
        json_data = json.load(file)
    assert json_data["stock_code"] == "005380"
    assert json_data["company_name"] == "현대자동차"


def test_cli_execution_unknown_ticker_fails():
    """미등록/미지원 종목코드 입력 시 적절한 오류 반환 테스트"""
    process_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.investment_analysis_cli",
            "--ticker",
            "999999",
            "--no-fixture",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
    )

    # 실패 코드(1)로 정상 종료되어야 함
    assert process_result.returncode != 0
