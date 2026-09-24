"""
통합 투자 분석 명령행 인터페이스 (Investment Analysis CLI)

사용자가 6자리 종목코드를 입력하면 모듈 2~6 전 과정을 오케스트레이션하여
투자 검토 기초 분석 리포트를 생성하는 원클릭 CLI 프로그램입니다.

[사용 예시]
    # 삼성전자 원클릭 리포트 생성 (기본 텍스트 리포트)
    python -m src.investment_analysis_cli --ticker 005930

    # JSON 형식 리포트 및 단계별 중간 산출물 동시 저장
    python -m src.investment_analysis_cli --ticker 005930 --format json --save-intermediate

    # 콘솔 화면에 리포트 전문 즉시 출력
    python -m src.investment_analysis_cli --ticker 005930 --print-to-console

[준수 규칙]
- 규칙 1 (투자 권유 금지): 매수/매도 권유 없이 객관적 숫자와 사실만 리포팅
- 규칙 2 (엔지니어링과 AI 분리): 100% Python 코드로 결정론적 파이프라인 수행
- 규칙 3 (모듈 독립성): 독립 실행 가능한 CLI 진입점 제공
- 규칙 6 (명확한 명명): 축약어 없는 완전한 함수명 및 변수명 사용
"""

import argparse
import sys
from pathlib import Path

from src.investment_analysis_pipeline import run_investment_analysis_pipeline
from src.models.indicator_evaluation_models import IndicatorEvaluationStatus


def build_command_line_argument_parser() -> argparse.ArgumentParser:
    """
    통합 분석 CLI의 인자 파서를 구성합니다.
    """
    parser = argparse.ArgumentParser(
        description="주식 투자 분석 시스템 통합 파이프라인 CLI (원클릭 분석)",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--ticker",
        type=str,
        required=True,
        help="분석할 6자리 종목코드 (예: 005930)",
    )
    parser.add_argument(
        "--fiscal-year",
        type=int,
        default=None,
        help="분석 기준 최신 사업연도 (미지정 시 최신 공시 사업연도 자동 탐색)",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="수집 및 추이 분석 연도 수 (기본값: 5)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help=(
            "출력 리포트 파일 경로\n"
            "(미지정 시 'reports/{ticker}_investment_analysis_report.{ext}' 자동 지정)"
        ),
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="리포트 출력 포맷 ('text': 텍스트 리포트, 'json': 구조화 JSON 데이터)",
    )
    parser.add_argument(
        "--save-intermediate",
        action="store_true",
        help="단계별 중간 산출물(정제재무, 주가, 벤치마크, 지표, 평가 JSON)을 data/ 디렉터리에 저장",
    )
    parser.add_argument(
        "--no-glossary",
        action="store_true",
        help="리포트에서 금융 용어 해설 섹션 제외",
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="리포트에서 사실 요약 섹션 제외",
    )
    parser.add_argument(
        "--no-fixture",
        action="store_true",
        help="Fixture fallback 사용 안 함 (실제 외부 API 전용 모드)",
    )
    parser.add_argument(
        "--print-to-console",
        action="store_true",
        help="생성된 리포트 전문을 콘솔 화면에 즉시 출력",
    )

    return parser


def main() -> None:
    """
    통합 CLI 실행 진입점 함수
    """
    parser = build_command_line_argument_parser()
    arguments = parser.parse_args()

    stock_code = arguments.ticker.strip()
    extension = "json" if arguments.format == "json" else "txt"
    default_output_file_path = f"reports/{stock_code}_investment_analysis_report.{extension}"
    target_output_file_path = arguments.output or default_output_file_path

    try:
        pipeline_result = run_investment_analysis_pipeline(
            stock_code=stock_code,
            fiscal_year=arguments.fiscal_year,
            number_of_years=arguments.years,
            output_report_file_path=target_output_file_path,
            report_format=arguments.format,
            save_intermediate_artifacts=arguments.save_intermediate,
            include_glossary=not arguments.no_glossary,
            include_summary=not arguments.no_summary,
            use_fixture_fallback=not arguments.no_fixture,
        )

        # 결과 요약 출력
        evaluations = pipeline_result.evaluation_report.evaluations
        good_count = sum(
            1 for evaluation in evaluations if evaluation.evaluation_status == IndicatorEvaluationStatus.GOOD
        )
        normal_count = sum(
            1 for evaluation in evaluations if evaluation.evaluation_status == IndicatorEvaluationStatus.NORMAL
        )
        caution_count = sum(
            1 for evaluation in evaluations if evaluation.evaluation_status == IndicatorEvaluationStatus.CAUTION
        )
        not_applicable_count = sum(
            1 for evaluation in evaluations if evaluation.evaluation_status == IndicatorEvaluationStatus.NOT_APPLICABLE
        )

        print("\n" + "=" * 80)
        print("  [투자 분석 리포트 생성 완료]")
        print("=" * 80)
        print(f"  - 대상 기업 : {pipeline_result.company_name} ({pipeline_result.stock_code})")
        print(f"  - 기준 연도 : {pipeline_result.fiscal_year}년 사업보고서 결산 기준")
        print(f"  - 판정 통계 : 총 {len(evaluations)}개 지표")
        print(f"    * 양호 [양호] : {good_count}개")
        print(f"    * 보통 [보통] : {normal_count}개")
        print(f"    * 주의 [주의] : {caution_count}개")
        print(f"    * 판단불가 : {not_applicable_count}개")
        print(f"  - 출력 파일 : {target_output_file_path}")
        print("=" * 80)

        if arguments.print_to_console:
            print("\n" + pipeline_result.report_text_content)

    except Exception as execution_error:
        print(f"\n[오류] 분석 파이프라인 실행 실패: {execution_error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
