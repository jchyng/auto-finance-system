"""
투자 분석 리포트 설명 및 포맷팅 엔진 (Financial Report Explainer)

평가 결과 JSON을 읽기 쉬운 텍스트 리포트로 변환합니다.
- 규칙 1 (투자 권유 금지) 준수: 매수/매도 권유 표현 필터링
- 규칙 2 (AI 분리) 준수: 템플릿 기반 출력 (AI 선택적 사용)
- 규칙 3 (모듈 독립성): 단독 CLI 실행 가능
- 규칙 6 (명확한 명명): 축약어 없는 완전한 함수명
"""

import argparse
import json
import re
from pathlib import Path
from typing import List

from src.models.indicator_evaluation_models import (
    CompleteCompanyEvaluationReport,
    SingleIndicatorEvaluation,
    IndicatorEvaluationStatus,
    IndicatorCategory,
)
from src.explainers.financial_term_dictionary import (
    get_term_explanation,
    format_term_glossary_section,
)


# ============================================================================
# 1. 투자 권유 표현 필터링 (Safety Guard)
# ============================================================================

# 금지된 투자 권유 표현 패턴
PROHIBITED_INVESTMENT_ADVICE_PATTERNS = [
    r"매수\s*(?:추천|권유|하세요|하십시오)",
    r"매도\s*(?:추천|권유|하세요|하십시오)",
    r"투자\s*(?:추천|권유|하세요|하십시오)",
    r"(?:적극|강력)\s*(?:추천|권장)",
    r"(?:저평가|고평가)\s*(?:확정|단정)",
    r"(?:좋은|나쁜|우량|부실)\s*기업",
    r"(?:반드시|꼭)\s*(?:사세요|파세요|투자하세요)",
    r"지금\s*(?:사야|팔아야)\s*(?:합니다|한다)",
]


def check_prohibited_expressions(text: str) -> List[str]:
    """
    텍스트에서 금지된 투자 권유 표현을 검사합니다.
    
    Args:
        text: 검사할 텍스트
    
    Returns:
        발견된 금지 표현 리스트 (없으면 빈 리스트)
    """
    found_violations = []
    
    for pattern in PROHIBITED_INVESTMENT_ADVICE_PATTERNS:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            found_violations.append(match.group(0))
    
    return found_violations


# ============================================================================
# 2. 텍스트 리포트 포맷팅 함수
# ============================================================================

def format_indicator_category_header(category: IndicatorCategory) -> str:
    """
    지표 분류 헤더를 포맷팅합니다.
    
    Args:
        category: 지표 분류
    
    Returns:
        포맷팅된 헤더 문자열
    """
    category_names = {
        IndicatorCategory.GROWTH: "1. 성장성 지표",
        IndicatorCategory.PROFITABILITY: "2. 수익성 지표",
        IndicatorCategory.FINANCIAL_HEALTH: "3. 재무건전성 지표",
        IndicatorCategory.VALUATION: "4. 밸류에이션 지표",
    }
    
    header = category_names.get(category, str(category.value))
    return f"\n{'=' * 80}\n{header}\n{'=' * 80}"


def format_status_badge(status: IndicatorEvaluationStatus) -> str:
    """
    판정 상태를 뱃지 형태로 포맷팅합니다.
    
    Args:
        status: 판정 상태
    
    Returns:
        포맷팅된 상태 뱃지
    """
    badges = {
        IndicatorEvaluationStatus.GOOD: "[양호]",
        IndicatorEvaluationStatus.NORMAL: "[보통]",
        IndicatorEvaluationStatus.CAUTION: "[주의]",
        IndicatorEvaluationStatus.NOT_APPLICABLE: "[판단불가]",
    }
    
    return badges.get(status, "[미정]")


def format_single_indicator(evaluation: SingleIndicatorEvaluation) -> str:
    """
    개별 지표 평가 결과를 텍스트로 포맷팅합니다.
    
    Args:
        evaluation: 개별 지표 평가 결과
    
    Returns:
        포맷팅된 텍스트
    """
    lines = []
    
    # 지표명 및 상태
    status_badge = format_status_badge(evaluation.evaluation_status)
    lines.append(f"\n■ {evaluation.indicator_name_korean} ({evaluation.indicator_name_english})")
    lines.append(f"   상태: {status_badge}")
    
    # 지표 값
    lines.append(f"   • 현재값: {evaluation.current_value_formatted}")
    lines.append(f"   • 5년평균: {evaluation.historical_five_year_average_formatted}")
    lines.append(f"   • 업종평균: {evaluation.industry_benchmark_average_formatted}")
    
    # 판정 근거
    lines.append(f"   • 판정근거: {evaluation.evaluation_reason_description}")
    
    # 계산 공식
    lines.append(f"   • 계산공식: {evaluation.calculation_formula_description}")
    
    # 데이터 출처
    lines.append(f"   • 출처: {evaluation.data_source_and_base_date_description}")
    
    return "\n".join(lines)


def format_indicators_by_category(
    evaluations: List[SingleIndicatorEvaluation]
) -> str:
    """
    지표 평가 결과를 분류별로 그룹화하여 포맷팅합니다.
    
    Args:
        evaluations: 15개 지표 평가 결과 리스트
    
    Returns:
        포맷팅된 텍스트
    """
    lines = []
    
    # 분류별로 그룹화
    categories_order = [
        IndicatorCategory.GROWTH,
        IndicatorCategory.PROFITABILITY,
        IndicatorCategory.FINANCIAL_HEALTH,
        IndicatorCategory.VALUATION,
    ]
    
    for category in categories_order:
        # 해당 분류의 지표만 필터링
        category_evaluations = [
            e for e in evaluations if e.indicator_category == category
        ]
        
        if not category_evaluations:
            continue
        
        # 분류 헤더
        lines.append(format_indicator_category_header(category))
        
        # 각 지표 출력
        for evaluation in category_evaluations:
            lines.append(format_single_indicator(evaluation))
    
    return "\n".join(lines)


def format_summary_statistics(evaluations: List[SingleIndicatorEvaluation]) -> str:
    """
    판정 결과 요약 통계를 포맷팅합니다.
    
    Args:
        evaluations: 15개 지표 평가 결과 리스트
    
    Returns:
        포맷팅된 요약 통계
    """
    status_counts = {
        IndicatorEvaluationStatus.GOOD: 0,
        IndicatorEvaluationStatus.NORMAL: 0,
        IndicatorEvaluationStatus.CAUTION: 0,
        IndicatorEvaluationStatus.NOT_APPLICABLE: 0,
    }
    
    for evaluation in evaluations:
        status_counts[evaluation.evaluation_status] += 1
    
    lines = [
        "\n" + "=" * 80,
        "판정 결과 요약",
        "=" * 80,
        f"총 {len(evaluations)}개 지표 중:",
        f"  • 양호: {status_counts[IndicatorEvaluationStatus.GOOD]}개",
        f"  • 보통: {status_counts[IndicatorEvaluationStatus.NORMAL]}개",
        f"  • 주의: {status_counts[IndicatorEvaluationStatus.CAUTION]}개",
        f"  • 판단불가: {status_counts[IndicatorEvaluationStatus.NOT_APPLICABLE]}개",
    ]
    
    return "\n".join(lines)


def format_report_header(report: CompleteCompanyEvaluationReport) -> str:
    """
    리포트 헤더를 포맷팅합니다.
    
    Args:
        report: 완성된 평가 리포트
    
    Returns:
        포맷팅된 헤더
    """
    lines = [
        "=" * 80,
        f"투자 검토 자료",
        "=" * 80,
        f"종목코드: {report.stock_code}",
        f"기업명: {report.company_name}",
        f"업종: {report.industry_classification_name}",
        f"분석 기준: {report.fiscal_year}년 사업연도 결산",
        "=" * 80,
    ]
    
    if report.closing_price_krw > 0:
        lines.insert(-1, f"현재가: {report.closing_price_krw:,}원")
    
    if report.market_capitalization_krw > 0:
        market_cap_trillion = report.market_capitalization_krw / 1_000_000_000_000
        lines.insert(-1, f"시가총액: {market_cap_trillion:.1f}조원")
    
    return "\n".join(lines)


def format_report_footer(report: CompleteCompanyEvaluationReport) -> str:
    """
    리포트 푸터를 포맷팅합니다.
    
    Args:
        report: 완성된 평가 리포트
    
    Returns:
        포맷팅된 푸터
    """
    lines = [
        "\n" + "=" * 80,
        "면책 고지",
        "=" * 80,
        report.disclaimer_text,
        "=" * 80,
    ]
    
    return "\n".join(lines)


# ============================================================================
# 3. 메인 리포트 생성 함수
# ============================================================================

def generate_text_report(
    report: CompleteCompanyEvaluationReport,
    include_glossary: bool = True,
    include_summary: bool = True
) -> str:
    """
    평가 리포트를 텍스트 형식으로 생성합니다.
    
    Args:
        report: 완성된 평가 리포트
        include_glossary: 용어 사전 포함 여부
        include_summary: 사실 요약 포함 여부
    
    Returns:
        완성된 텍스트 리포트
    """
    sections = []
    
    # 1. 헤더
    sections.append(format_report_header(report))
    
    # 2. 사실 요약 (선택)
    if include_summary and report.plain_korean_summary_text:
        sections.append("\n[분석 요약]")
        sections.append(report.plain_korean_summary_text)
    
    # 3. 판정 결과 통계
    sections.append(format_summary_statistics(report.evaluations))
    
    # 4. 지표별 상세 판정
    sections.append(format_indicators_by_category(report.evaluations))
    
    # 5. 용어 사전 (선택)
    if include_glossary:
        sections.append("\n" + format_term_glossary_section())
    
    # 6. 푸터
    sections.append(format_report_footer(report))
    
    # 전체 리포트 조합
    full_report = "\n".join(sections)
    
    # 안전 검사: 금지된 투자 권유 표현 확인 (정당한 권유 배제 문구가 포함된 면책 고지 섹션 제외)
    disclaimer_start = full_report.find("면책 고지")
    content_to_check = full_report[:disclaimer_start] if disclaimer_start != -1 else full_report
    violations = check_prohibited_expressions(content_to_check)
    if violations:
        print(f"Warning: 다음 투자 권유 표현이 발견되었습니다: {violations}")
        print("Warning: 규칙 1 위반 가능성이 있으니 수동 확인이 필요합니다.")
    
    return full_report


def save_text_report_to_file(
    report_text: str,
    output_file_path: str
) -> None:
    """
    텍스트 리포트를 파일로 저장합니다.
    
    Args:
        report_text: 리포트 텍스트
        output_file_path: 저장할 파일 경로
    """
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as file:
        file.write(report_text)
    
    print(f"Success: 리포트를 {output_file_path}에 저장 완료")


# ============================================================================
# 4. CLI 실행 함수
# ============================================================================

def main():
    """
    단독 CLI 실행 진입점
    
    Example:
        python -m src.explainers.financial_report_explainer \
            --input data/evaluation/005930_evaluation.json \
            --output reports/005930_report.txt \
            --format text
    """
    parser = argparse.ArgumentParser(
        description="투자 분석 리포트 생성기 (독립 실행 모드)"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="평가 결과 JSON 파일 경로"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/investment_analysis_report.txt",
        help="출력 리포트 파일 경로"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["text", "json"],
        default="text",
        help="출력 형식 (text: 텍스트 리포트, json: JSON 그대로)"
    )
    parser.add_argument(
        "--no-glossary",
        action="store_true",
        help="용어 사전 제외"
    )
    parser.add_argument(
        "--no-summary",
        action="store_true",
        help="사실 요약 제외"
    )
    
    args = parser.parse_args()
    
    try:
        # 평가 리포트 로드
        input_path = Path(args.input)
        if not input_path.exists():
            raise FileNotFoundError(f"입력 파일이 존재하지 않습니다: {args.input}")
        
        with open(input_path, "r", encoding="utf-8") as file:
            report_data = json.load(file)
        
        report = CompleteCompanyEvaluationReport.from_dictionary(report_data)
        
        print(f"Info: {report.company_name}({report.stock_code}) 리포트 생성 시작")
        
        # 리포트 생성
        if args.format == "text":
            report_text = generate_text_report(
                report,
                include_glossary=not args.no_glossary,
                include_summary=not args.no_summary
            )
            save_text_report_to_file(report_text, args.output)
        else:
            # JSON 형식은 그대로 복사
            with open(args.output, "w", encoding="utf-8") as file:
                json.dump(report_data, file, ensure_ascii=False, indent=2)
            print(f"Success: JSON 리포트를 {args.output}에 저장 완료")
        
        print("\n=== 리포트 생성 완료 ===")
        print(f"종목: {report.company_name} ({report.stock_code})")
        print(f"분석 연도: {report.fiscal_year}")
        print(f"평가 지표 수: {len(report.evaluations)}개")
        print(f"출력 파일: {args.output}")
        
    except Exception as error:
        print(f"\nError: 리포트 생성 실패 - {error}")
        import traceback
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
