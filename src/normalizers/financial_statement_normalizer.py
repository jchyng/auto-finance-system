"""
재무제표 정제기 (Financial Statement Normalizer)

DART 원본 재무제표의 상이한 계정과목명을 표준 항목으로 통일하고 
NormalizedFinancialStatement 모델로 변환합니다.

규칙 3(모듈 독립성): 단독 CLI 실행 가능
규칙 6(명확한 명명): 축약어 없는 완전한 함수명
"""

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models.financial_statement_models import NormalizedFinancialStatement


# DART 계정과목명 매핑 테이블 (다양한 표기를 표준명으로 통일)
ACCOUNT_NAME_MAPPING = {
    # 손익계산서 항목
    "매출액": ["매출액", "수익(매출액)", "영업수익",
             "수익(매출액) 기타 부문", "매출액(상품)", "매출액(용역)"],
    "영업이익": ["영업이익", "영업이익(손실)"],
    "당기순이익": ["당기순이익", "당기순이익(손실)", "분기순이익",
                "연결당기순이익", "계속영업연결당기순이익"],
    "지배기업소유주지분순이익": ["지배기업의 소유주에게 귀속되는 당기순이익", "지배기업 소유주지분 순이익", 
                                   "지배주주순이익", "지배기업소유주지분순이익"],
    "법인세비용": ["법인세비용", "법인세등", "법인세비용(수익)", "법인세비용(손실)"],
    "법인세차감전순이익": ["법인세비용차감전순이익", "법인세비용차감전계속사업이익",
                   "법인세차감전순이익", "법인세비용차감전순이익(손실)",
                   "법인세비용차감전계속사업이익(손실)"],
    
    # 재무상태표 항목
    "자산총계": ["자산총계", "자산총액"],
    "부채총계": ["부채총계", "부채총액"],
    "자본총계": ["자본총계", "자본총액"],
    "지배기업소유주지분": ["지배기업의 소유주에게 귀속되는 자본", "지배기업 소유주지분", 
                          "지배주주지분", "지배기업소유주지분"],
    "유동자산": ["유동자산"],
    "유동부채": ["유동부채"],
    "비유동자산": ["비유동자산"],
    "비유동부채": ["비유동부채"],
    
    # 차입금 항목
    "단기차입금": ["단기차입금", "단기금융부채"],
    "유동성장기부채": ["유동성장기부채", "유동성장기차입금"],
    "장기차입금": ["장기차입금", "장기금융부채"],
    "현금및현금성자산": ["현금및현금성자산", "현금및현금등가물"],
    
    # 현금흐름표 항목
    "영업활동현금흐름": ["영업활동으로 인한 현금흐름", "영업활동현금흐름", "영업활동 현금흐름"],
    "유형자산의취득": ["유형자산의 취득", "유형자산취득", "유형자산 취득"],
    "무형자산의취득": ["무형자산의 취득", "무형자산취득", "무형자산 취득"],
    
    # 감가상각 및 이자비용
    "유형자산감가상각비": ["유형자산감가상각비", "감가상각비", "유형자산 감가상각비"],
    "무형자산상각비": ["무형자산상각비", "무형자산 상각비", "무형자산의 상각비"],
    "이자비용": ["이자비용", "금융비용"],

    # 금융업 대용 수익 (매출액 계정 부재 시 사용)
    "이자수익": ["이자수익", "이자 및 배당수익(손실)"],
    "수수료수익": ["수수료수익", "수수료 및 중개수입"],
}


def find_account_value_by_name(
    accounts_list: List[Dict[str, Any]],
    standard_account_name: str,
    fiscal_year: int
) -> Optional[int]:
    """
    계정과목 리스트에서 표준 계정명에 해당하는 값을 찾습니다.

    Args:
        accounts_list: DART 원본 계정과목 리스트
        standard_account_name: 표준 계정명 (예: "매출액")
        fiscal_year: 사업연도

    Returns:
        계정과목 금액(원) 또는 None (없을 시)

    Note:
        실제 DART 응답은 "법인세비용(수익)", "법인세비용차감전순이익(손실)"처럼
        괄호 설명이 붙는 경우가 있어, 괄호를 제거한 이름도 함께 매칭합니다.
        또한 같은 계정명이 손익계산서(CIS)·현금흐름표(CF)·자본변동표(SCE)에
        중복 등장하므로 손익계산서 항목을 우선 선택합니다.
    """
    if standard_account_name not in ACCOUNT_NAME_MAPPING:
        return None

    possible_names = ACCOUNT_NAME_MAPPING[standard_account_name]

    def strip_parenthetical_description(account_name: str) -> str:
        while True:
            opening_position = account_name.rfind("(")
            if opening_position == -1:
                return account_name.strip()
            account_name = account_name[:opening_position]

    def extract_amount(account: Dict[str, Any]) -> Optional[int]:
        amount_str = account.get("thstrm_amount", "0")
        try:
            return int(str(amount_str).replace(",", ""))
        except (ValueError, AttributeError, TypeError):
            return None

    # 1차: 손익계산서(CIS) 우선 → 2차: 전체 구분
    for section_priority in ({"CIS"}, None):
        for account in accounts_list:
            if section_priority is not None and account.get("sj_div") not in section_priority:
                continue
            account_name = account.get("account_nm", "").strip()
            normalized_account_name = strip_parenthetical_description(account_name)

            if account_name in possible_names or normalized_account_name in possible_names:
                amount = extract_amount(account)
                if amount is not None:
                    return amount

    return None
    
    return None


def normalize_dart_financial_statement(
    stock_code: str,
    company_name: str,
    fiscal_year: int,
    dart_raw_accounts: List[Dict[str, Any]],
    is_financial_industry: bool = False
) -> NormalizedFinancialStatement:
    """
    DART 원본 계정과목 리스트를 NormalizedFinancialStatement로 변환합니다.
    
    Args:
        stock_code: 6자리 종목코드
        company_name: 기업명
        fiscal_year: 사업연도
        dart_raw_accounts: DART API 응답의 계정과목 리스트
        is_financial_industry: 금융업 여부
    
    Returns:
        NormalizedFinancialStatement 모델
    
    Raises:
        ValueError: 필수 계정과목이 누락된 경우
    """
    # 손익계산서 항목 추출
    revenue_krw = find_account_value_by_name(dart_raw_accounts, "매출액", fiscal_year)
    # 금융업은 "매출액" 계정이 없으므로 이자수익+수수료수익을 대용 수익으로 사용
    if revenue_krw is None and is_financial_industry:
        interest_income_krw = find_account_value_by_name(
            dart_raw_accounts, "이자수익", fiscal_year
        ) or 0
        fee_income_krw = find_account_value_by_name(
            dart_raw_accounts, "수수료수익", fiscal_year
        ) or 0
        if interest_income_krw or fee_income_krw:
            revenue_krw = interest_income_krw + fee_income_krw
    operating_income_krw = find_account_value_by_name(dart_raw_accounts, "영업이익", fiscal_year)
    
    # 지배주주순이익 추출 (없으면 당기순이익 사용)
    controlling_interest_net_income_krw = find_account_value_by_name(
        dart_raw_accounts, "지배기업소유주지분순이익", fiscal_year
    )
    if controlling_interest_net_income_krw is None:
        controlling_interest_net_income_krw = find_account_value_by_name(
            dart_raw_accounts, "당기순이익", fiscal_year
        )
    
    income_tax_expense_krw = find_account_value_by_name(dart_raw_accounts, "법인세비용", fiscal_year)
    profit_before_tax_krw = find_account_value_by_name(dart_raw_accounts, "법인세차감전순이익", fiscal_year)
    
    # 재무상태표 항목 추출
    total_assets_krw = find_account_value_by_name(dart_raw_accounts, "자산총계", fiscal_year)
    total_liabilities_krw = find_account_value_by_name(dart_raw_accounts, "부채총계", fiscal_year)
    
    # 지배주주자본 추출 (없으면 자본총계 사용)
    controlling_interest_equity_krw = find_account_value_by_name(
        dart_raw_accounts, "지배기업소유주지분", fiscal_year
    )
    if controlling_interest_equity_krw is None:
        controlling_interest_equity_krw = find_account_value_by_name(
            dart_raw_accounts, "자본총계", fiscal_year
        )
    
    # 유동자산/부채 (금융업은 None)
    current_assets_krw = None if is_financial_industry else find_account_value_by_name(
        dart_raw_accounts, "유동자산", fiscal_year
    )
    current_liabilities_krw = None if is_financial_industry else find_account_value_by_name(
        dart_raw_accounts, "유동부채", fiscal_year
    )
    
    # 차입금 및 현금
    short_term_borrowings_krw = find_account_value_by_name(
        dart_raw_accounts, "단기차입금", fiscal_year
    ) or 0
    
    # 장기차입금 = 장기차입금 + 유동성장기부채
    long_term_borrowings_krw = (
        find_account_value_by_name(dart_raw_accounts, "장기차입금", fiscal_year) or 0
    ) + (
        find_account_value_by_name(dart_raw_accounts, "유동성장기부채", fiscal_year) or 0
    )
    
    cash_and_cash_equivalents_krw = find_account_value_by_name(
        dart_raw_accounts, "현금및현금성자산", fiscal_year
    ) or 0
    
    # 현금흐름 및 감가상각
    operating_cash_flow_krw = find_account_value_by_name(
        dart_raw_accounts, "영업활동현금흐름", fiscal_year
    ) or 0
    
    acquisition_of_tangible_assets_krw = find_account_value_by_name(
        dart_raw_accounts, "유형자산의취득", fiscal_year
    ) or 0
    
    acquisition_of_intangible_assets_krw = find_account_value_by_name(
        dart_raw_accounts, "무형자산의취득", fiscal_year
    ) or 0
    
    tangible_asset_depreciation_krw = find_account_value_by_name(
        dart_raw_accounts, "유형자산감가상각비", fiscal_year
    ) or 0
    
    intangible_asset_amortization_krw = find_account_value_by_name(
        dart_raw_accounts, "무형자산상각비", fiscal_year
    ) or 0
    
    interest_expense_krw = find_account_value_by_name(
        dart_raw_accounts, "이자비용", fiscal_year
    ) or 0
    
    # 필수 항목 검증
    if revenue_krw is None or operating_income_krw is None:
        raise ValueError(
            f"필수 계정과목 누락: 매출액 또는 영업이익이 존재하지 않습니다 "
            f"(종목: {stock_code}, 연도: {fiscal_year})"
        )
    
    if total_assets_krw is None or total_liabilities_krw is None:
        raise ValueError(
            f"필수 계정과목 누락: 자산총계 또는 부채총계가 존재하지 않습니다 "
            f"(종목: {stock_code}, 연도: {fiscal_year})"
        )
    
    return NormalizedFinancialStatement(
        stock_code=stock_code,
        company_name=company_name,
        fiscal_year=fiscal_year,
        revenue_krw=revenue_krw,
        operating_income_krw=operating_income_krw,
        controlling_interest_net_income_krw=controlling_interest_net_income_krw or 0,
        income_tax_expense_krw=income_tax_expense_krw or 0,
        profit_before_tax_krw=profit_before_tax_krw or 0,
        total_assets_krw=total_assets_krw,
        total_liabilities_krw=total_liabilities_krw,
        controlling_interest_equity_krw=controlling_interest_equity_krw or 0,
        current_assets_krw=current_assets_krw,
        current_liabilities_krw=current_liabilities_krw,
        short_term_borrowings_krw=short_term_borrowings_krw,
        long_term_borrowings_krw=long_term_borrowings_krw,
        cash_and_cash_equivalents_krw=cash_and_cash_equivalents_krw,
        operating_cash_flow_krw=operating_cash_flow_krw,
        acquisition_of_tangible_assets_krw=acquisition_of_tangible_assets_krw,
        acquisition_of_intangible_assets_krw=acquisition_of_intangible_assets_krw,
        tangible_asset_depreciation_krw=tangible_asset_depreciation_krw,
        intangible_asset_amortization_krw=intangible_asset_amortization_krw,
        interest_expense_krw=interest_expense_krw,
        is_financial_industry=is_financial_industry,
        data_source_name="DART 전자공시"
    )


def normalize_multiple_years_from_dart_response(
    dart_response_data: Dict[str, Any]
) -> List[NormalizedFinancialStatement]:
    """
    DART API 응답 전체를 받아 여러 연도의 정제된 재무제표 리스트를 반환합니다.
    
    Args:
        dart_response_data: DART API fnlttSinglAcntAll.json 응답 데이터
    
    Returns:
        NormalizedFinancialStatement 리스트 (최신 연도부터 내림차순)
    """
    # 실제 DART API 응답 구조에 맞춰 구현
    # 현재는 fixture 기반 구조로 간소화
    
    stock_code = dart_response_data.get("stock_code", "")
    company_name = dart_response_data.get("company_name", "")
    is_financial = dart_response_data.get("is_financial_industry", False)
    
    # fixture는 이미 정제된 데이터이므로 그대로 변환
    statements_data = dart_response_data.get("annual_financial_statements", [])
    
    normalized_statements = []
    for stmt_dict in statements_data:
        normalized_statements.append(
            NormalizedFinancialStatement.from_dictionary(stmt_dict)
        )
    
    # 최신 연도부터 내림차순 정렬
    normalized_statements.sort(key=lambda x: x.fiscal_year, reverse=True)
    
    return normalized_statements


def save_normalized_statements_to_json_file(
    statements: List[NormalizedFinancialStatement],
    output_file_path: str
) -> None:
    """
    정제된 재무제표 리스트를 JSON 파일로 저장합니다.
    
    Args:
        statements: NormalizedFinancialStatement 리스트
        output_file_path: 저장할 JSON 파일 경로
    """
    output_data = {
        "normalized_statements": [stmt.to_dictionary() for stmt in statements],
        "total_years": len(statements)
    }
    
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(output_data, file, ensure_ascii=False, indent=2)
    
    print(f"Success: 정제된 재무제표를 {output_file_path}에 저장 완료")


def main():
    """
    단독 CLI 실행 진입점
    
    Example:
        python -m src.normalizers.financial_statement_normalizer \
            --input data/fixtures/005930_samsung_electronics_dart_financials.json \
            --output data/processed/005930_normalized.json
    """
    parser = argparse.ArgumentParser(
        description="재무제표 정제기 (독립 실행 모드)"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="입력 JSON 파일 경로 (DART 원본 또는 fixture)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/processed/normalized_statements.json",
        help="출력 JSON 파일 경로"
    )
    
    args = parser.parse_args()
    
    try:
        # 입력 JSON 로드
        input_path = Path(args.input)
        if not input_path.exists():
            raise FileNotFoundError(f"입력 파일이 존재하지 않습니다: {args.input}")
        
        with open(input_path, "r", encoding="utf-8") as file:
            input_data = json.load(file)
        
        # 정제 수행
        print(f"Info: {args.input}에서 재무제표 정제 시작")
        normalized_statements = normalize_multiple_years_from_dart_response(input_data)
        
        # 저장
        save_normalized_statements_to_json_file(normalized_statements, args.output)
        
        print("\n=== 정제 요약 ===")
        print(f"종목코드: {normalized_statements[0].stock_code}")
        print(f"기업명: {normalized_statements[0].company_name}")
        print(f"정제 연도 수: {len(normalized_statements)}")
        print(f"연도 범위: {normalized_statements[-1].fiscal_year} ~ {normalized_statements[0].fiscal_year}")
        print(f"금융업 여부: {normalized_statements[0].is_financial_industry}")
        print(f"출력 파일: {args.output}")
        
    except Exception as error:
        print(f"\nError: 재무제표 정제 실패 - {error}")
        exit(1)


if __name__ == "__main__":
    main()
