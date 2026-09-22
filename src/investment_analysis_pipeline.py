"""
투자 분석 전체 파이프라인 (Investment Analysis Pipeline)

모듈 2(수집)부터 모듈 6(설명/리포트)까지 순차적으로 연계하여
종목코드 입력 시 완결된 투자 분석 리포트를 생성하는 통합 오케스트레이터입니다.

[준수 규칙]
- 규칙 1 (투자 권유 금지): 주관적 추천 없이 객관적 지표와 사실만 전달
- 규칙 2 (엔지니어링과 AI 분리): 지표 수집, 정제, 계산, 평가는 100% Python 코드로 수행
- 규칙 3 (모듈 독립성): 각 하위 모듈의 독립 인터페이스를 조합하여 파이프라인 구성
- 규칙 4 (미니멀리즘): 불필요한 외부 의존성 없이 표준 라이브러리와 기존 모듈 활용
- 규칙 6 (명확한 명명): 축약어 없는 완전한 함수명 및 변수명 사용
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models.financial_statement_models import (
    NormalizedFinancialStatement,
    StockPriceAndMarketCapData,
    IndustryBenchmarkData,
)
from src.models.investment_indicator_models import (
    CompanyInvestmentIndicatorsSummary,
)
from src.models.indicator_evaluation_models import (
    CompleteCompanyEvaluationReport,
)
from src.collectors.dart_financial_statement_collector import (
    collect_normalized_financial_statements,
)
from src.collectors.krx_stock_price_collector import (
    collect_stock_price_and_market_cap,
)
from src.collectors.krx_industry_benchmark_collector import (
    collect_industry_benchmark_data,
)
from src.engines.financial_indicator_calculator import (
    calculate_company_indicators_summary,
)
from src.engines.investment_indicator_evaluator import (
    generate_complete_evaluation_report,
)
from src.explainers.financial_report_explainer import (
    generate_text_report,
    save_text_report_to_file,
)


@dataclass
class InvestmentAnalysisPipelineResult:
    """
    통합 투자 분석 파이프라인 실행 결과 데이터 모델
    """
    stock_code: str
    company_name: str
    fiscal_year: int
    financial_statements: List[NormalizedFinancialStatement]
    stock_price_data: StockPriceAndMarketCapData
    industry_benchmark_data: Optional[IndustryBenchmarkData]
    indicators_summary: CompanyInvestmentIndicatorsSummary
    evaluation_report: CompleteCompanyEvaluationReport
    report_text_content: str
    output_report_file_path: Optional[str] = None
    saved_artifact_file_paths: Dict[str, str] = field(default_factory=dict)

    def to_dictionary(self) -> Dict[str, Any]:
        """결과를 딕셔너리로 직렬화합니다."""
        return {
            "stock_code": self.stock_code,
            "company_name": self.company_name,
            "fiscal_year": self.fiscal_year,
            "stock_price_data": self.stock_price_data.to_dictionary(),
            "industry_benchmark_data": (
                self.industry_benchmark_data.to_dictionary()
                if self.industry_benchmark_data
                else None
            ),
            "indicators_summary": self.indicators_summary.to_dictionary(),
            "evaluation_report": self.evaluation_report.to_dictionary(),
            "output_report_file_path": self.output_report_file_path,
            "saved_artifact_file_paths": self.saved_artifact_file_paths,
        }


def save_intermediate_artifacts_to_disk(
    stock_code: str,
    base_directory: str,
    financial_statements: List[NormalizedFinancialStatement],
    stock_price_data: StockPriceAndMarketCapData,
    industry_benchmark_data: Optional[IndustryBenchmarkData],
    indicators_summary: CompanyInvestmentIndicatorsSummary,
    evaluation_report: CompleteCompanyEvaluationReport,
) -> Dict[str, str]:
    """
    파이프라인 각 단계별 중간 산출물을 JSON 파일로 저장합니다.
    
    Args:
        stock_code: 6자리 종목코드
        base_directory: 저장 루트 디렉터리 (예: "data")
        financial_statements: 정제 재무제표 리스트
        stock_price_data: 주가/시가총액 데이터
        industry_benchmark_data: 업종 벤치마크 데이터
        indicators_summary: 지표 계산 요약
        evaluation_report: 지표 평가 리포트
    
    Returns:
        저장된 파일 경로 딕셔너리
    """
    base_path = Path(base_directory)
    saved_paths = {}

    # 1. 정제 재무제표 저장
    processed_dir = base_path / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    financials_file = processed_dir / f"{stock_code}_normalized_financials.json"
    with open(financials_file, "w", encoding="utf-8") as file:
        json.dump(
            {
                "stock_code": stock_code,
                "statements": [statement.to_dictionary() for statement in financial_statements],
            },
            file,
            ensure_ascii=False,
            indent=2,
        )
    saved_paths["normalized_financials"] = str(financials_file)

    # 2. 주가 및 시가총액 저장
    raw_dir = base_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    price_file = raw_dir / f"{stock_code}_stock_price.json"
    with open(price_file, "w", encoding="utf-8") as file:
        json.dump(stock_price_data.to_dictionary(), file, ensure_ascii=False, indent=2)
    saved_paths["stock_price"] = str(price_file)

    # 3. 업종 벤치마크 저장
    if industry_benchmark_data:
        benchmark_file = raw_dir / f"{stock_code}_industry_benchmark.json"
        with open(benchmark_file, "w", encoding="utf-8") as file:
            json.dump(industry_benchmark_data.to_dictionary(), file, ensure_ascii=False, indent=2)
        saved_paths["industry_benchmark"] = str(benchmark_file)

    # 4. 계산된 15개 지표 저장
    metrics_dir = base_path / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    metrics_file = metrics_dir / f"{stock_code}_calculated_metrics.json"
    with open(metrics_file, "w", encoding="utf-8") as file:
        json.dump(indicators_summary.to_dictionary(), file, ensure_ascii=False, indent=2)
    saved_paths["calculated_metrics"] = str(metrics_file)

    # 5. 상태 평가 결과 JSON 저장
    evaluation_dir = base_path / "evaluation"
    evaluation_dir.mkdir(parents=True, exist_ok=True)
    evaluation_file = evaluation_dir / f"{stock_code}_evaluation_report.json"
    with open(evaluation_file, "w", encoding="utf-8") as file:
        json.dump(evaluation_report.to_dictionary(), file, ensure_ascii=False, indent=2)
    saved_paths["evaluation_report"] = str(evaluation_file)

    return saved_paths


def run_investment_analysis_pipeline(
    stock_code: str,
    fiscal_year: int = 2023,
    number_of_years: int = 5,
    output_report_file_path: Optional[str] = None,
    report_format: str = "text",
    save_intermediate_artifacts: bool = False,
    artifacts_directory: str = "data",
    include_glossary: bool = True,
    include_summary: bool = True,
    use_fixture_fallback: bool = True,
) -> InvestmentAnalysisPipelineResult:
    """
    모듈 2~6을 순차적으로 결합하여 투자 분석 전체 과정을 실행합니다.

    Args:
        stock_code: 6자리 종목코드 (예: "005930")
        fiscal_year: 기준 사업연도 (기본값: 2023)
        number_of_years: 수집 및 분석 연도 수 (기본값: 5)
        output_report_file_path: 최종 리포트 저장 경로 (None일 경우 파일 저장 안 함)
        report_format: 리포트 출력 형식 ("text" 또는 "json")
        save_intermediate_artifacts: 각 단계 중간 산출물(JSON) 저장 여부
        artifacts_directory: 중간 산출물 저장 디렉터리 경로
        include_glossary: 금융 용어 해설 사전 포함 여부
        include_summary: 사실 요약 섹션 포함 여부
        use_fixture_fallback: 외부 API 실패/미설정 시 로컬 fixture 사용 여부

    Returns:
        InvestmentAnalysisPipelineResult 결과 객체

    Raises:
        ValueError: 파이프라인 단계 중 필수 데이터 누락 또는 처리 실패 시
    """
    print("=" * 80)
    print(f"투자 분석 파이프라인 시작 (종목코드: {stock_code}, 기준연도: {fiscal_year})")
    print("=" * 80)

    # ------------------------------------------------------------------------
    # [Step 1 / 모듈 2 & 3] 재무제표 수집 및 정제
    # ------------------------------------------------------------------------
    print(f"[1/5] 재무제표 수집 중... ({number_of_years}개년)")
    financial_statements = collect_normalized_financial_statements(
        stock_code=stock_code,
        fiscal_year=fiscal_year,
        number_of_years=number_of_years,
        use_fixture_fallback=use_fixture_fallback,
    )
    if not financial_statements:
        raise ValueError(f"종목코드 {stock_code}의 재무제표 데이터를 수집하지 못했습니다.")
    company_name = financial_statements[0].company_name
    print(f"  -> 기업명: {company_name}, 수집 연도: {len(financial_statements)}개")

    # ------------------------------------------------------------------------
    # [Step 2 / 모듈 2] KRX 주가 및 시가총액 수집
    # ------------------------------------------------------------------------
    print("[2/5] 주가 및 시가총액 수집 중...")
    stock_price_data = collect_stock_price_and_market_cap(
        stock_code=stock_code,
        use_fixture_fallback=use_fixture_fallback,
    )
    print(
        f"  -> 종가: {stock_price_data.closing_price_krw:,}원, "
        f"시가총액: {stock_price_data.market_capitalization_krw / 1_000_000_000_000:.1f}조원"
    )

    # ------------------------------------------------------------------------
    # [Step 3 / 모듈 2] KRX 업종 벤치마크 수집
    # ------------------------------------------------------------------------
    print("[3/5] 업종 벤치마크 수집 중...")
    try:
        industry_benchmark_data = collect_industry_benchmark_data(
            stock_code=stock_code,
            use_fixture_fallback=use_fixture_fallback,
        )
        print(f"  -> 업종명: {industry_benchmark_data.industry_classification_name}")
    except Exception as benchmark_error:
        print(f"  -> 업종 벤치마크 수집 생략 (단독 분석 진행): {benchmark_error}")
        industry_benchmark_data = None

    # ------------------------------------------------------------------------
    # [Step 4 / 모듈 4] 15개 핵심 투자지표 및 5개년 평균 계산
    # ------------------------------------------------------------------------
    print("[4/5] 15개 핵심 투자지표 수학 계산 중...")
    indicators_summary = calculate_company_indicators_summary(
        financial_statements=financial_statements,
        stock_price_data=stock_price_data,
    )
    print(f"  -> {indicators_summary.latest_fiscal_year}년 지표 및 5년 평균 산출 완료")

    # ------------------------------------------------------------------------
    # [Step 5 / 모듈 5] 규칙 기반 지표 상태 판정
    # ------------------------------------------------------------------------
    print("[5/5] 객관적 규칙 기반 상태 판정 중...")
    evaluation_report = generate_complete_evaluation_report(
        indicators_summary=indicators_summary,
        industry_benchmark=industry_benchmark_data,
        closing_price=stock_price_data.closing_price_krw,
        market_cap=stock_price_data.market_capitalization_krw,
    )
    print(f"  -> 총 {len(evaluation_report.evaluations)}개 지표 평가 완료")

    # ------------------------------------------------------------------------
    # [중간 산출물 저장 (선택)]
    # ------------------------------------------------------------------------
    saved_artifact_file_paths = {}
    if save_intermediate_artifacts:
        print(f"중간 산출물 저장 중 ({artifacts_directory}/)...")
        saved_artifact_file_paths = save_intermediate_artifacts_to_disk(
            stock_code=stock_code,
            base_directory=artifacts_directory,
            financial_statements=financial_statements,
            stock_price_data=stock_price_data,
            industry_benchmark_data=industry_benchmark_data,
            indicators_summary=indicators_summary,
            evaluation_report=evaluation_report,
        )
        for artifact_key, artifact_path in saved_artifact_file_paths.items():
            print(f"  - {artifact_key}: {artifact_path}")

    # ------------------------------------------------------------------------
    # [Step 6 / 모듈 6] 최종 리포트 생성 및 저장
    # ------------------------------------------------------------------------
    report_text_content = generate_text_report(
        report=evaluation_report,
        include_glossary=include_glossary,
        include_summary=include_summary,
    )

    if output_report_file_path:
        output_path = Path(output_report_file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if report_format == "json":
            with open(output_path, "w", encoding="utf-8") as file:
                json.dump(evaluation_report.to_dictionary(), file, ensure_ascii=False, indent=2)
        else:
            save_text_report_to_file(report_text_content, output_report_file_path)

        print(f"최종 리포트 파일 저장 완료: {output_report_file_path}")

    print("=" * 80)
    print(f"파이프라인 실행 완료: {company_name} ({stock_code})")
    print("=" * 80)

    return InvestmentAnalysisPipelineResult(
        stock_code=stock_code,
        company_name=company_name,
        fiscal_year=indicators_summary.latest_fiscal_year,
        financial_statements=financial_statements,
        stock_price_data=stock_price_data,
        industry_benchmark_data=industry_benchmark_data,
        indicators_summary=indicators_summary,
        evaluation_report=evaluation_report,
        report_text_content=report_text_content,
        output_report_file_path=output_report_file_path,
        saved_artifact_file_paths=saved_artifact_file_paths,
    )
