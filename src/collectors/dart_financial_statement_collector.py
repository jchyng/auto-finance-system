"""
DART Open API 재무제표 수집기 (DART Financial Statement Collector)

금융감독원 전자공시(DART) Open API를 통해 사업보고서 기반 5개년 연간 재무제표를 수집합니다.
- API Key가 없는 경우 로컬 fixture JSON을 fallback으로 사용 (오프라인 개발/테스트 지원)
- 규칙 3(모듈 독립성) 준수: 단독 CLI 실행 가능
- 규칙 6(명확한 명명) 준수: 축약어 없이 완전한 함수명 및 변수명 사용
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime

from src.models.financial_statement_models import NormalizedFinancialStatement


# DART Open API 엔드포인트
DART_API_BASE_URL = "https://opendart.fss.or.kr/api"
DART_CORP_CODE_URL = f"{DART_API_BASE_URL}/corpCode.xml"
DART_FINANCIAL_STATEMENT_URL = f"{DART_API_BASE_URL}/fnlttSinglAcntAll.json"


def get_dart_api_key_from_environment() -> Optional[str]:
    """
    환경변수에서 DART API Key를 가져옵니다.
    
    Returns:
        API Key 문자열 또는 None (미설정 시)
    """
    return os.environ.get("DART_API_KEY")


FIXTURE_SAMPLE_DATA_DESCRIPTION = (
    "공시 기반 샘플/근사 데이터 "
    "(손익계산서 헤드라인은 실측, 재무상태표 세부 계정은 근사 포함 가능)"
)
FIXTURE_SAMPLE_DATA_SHORT_LABEL = "공시 기반 샘플/근사 fixture"


def get_fixture_sample_data_description() -> str:
    """fixture 성격 설명 문구를 반환합니다 (G2(b) 재라벨링).

    Returns:
        fixture 데이터 성격 설명 문자열
    """
    return FIXTURE_SAMPLE_DATA_DESCRIPTION


def parse_corporation_code_mapping_from_corp_code_xml(
    corp_code_xml_bytes: bytes
) -> Dict[str, str]:
    """DART corpCode.xml 응답에서 종목코드→DART 기업코드 매핑을 파싱합니다 (G4).

    Args:
        corp_code_xml_bytes: corpCode.xml ZIP 해제 후 XML 바이트

    Returns:
        종목코드(6자리) → DART 기업코드(8자리) 매핑 딕셔너리

    Note:
        offline-first 원칙에 따라 네트워크 호출은 별도 함수로 분리하고,
        본 함수는 순수 파싱만 담당합니다 (단위 테스트 가능).
    """
    import xml.etree.ElementTree as xml_element_tree

    stock_to_corporation_mapping: Dict[str, str] = {}
    root_element = xml_element_tree.fromstring(corp_code_xml_bytes)

    for result_element in root_element.findall("list"):
        stock_code_element = result_element.find("stock_code")
        corporation_code_element = result_element.find("corp_code")

        if stock_code_element is None or corporation_code_element is None:
            continue

        stock_code_text = (stock_code_element.text or "").strip()
        corporation_code_text = (corporation_code_element.text or "").strip()

        if len(stock_code_text) == 6 and len(corporation_code_text) == 8:
            stock_to_corporation_mapping[stock_code_text] = corporation_code_text

    return stock_to_corporation_mapping


def download_corp_code_xml_bytes_from_dart(api_key: str) -> bytes:
    """DART corpCode.xml ZIP을 다운로드해 해제된 XML 바이트를 반환합니다 (G4).

    Args:
        api_key: DART API Key

    Returns:
        corpCode.xml 해제 바이트

    Raises:
        RuntimeError: 다운로드/해제 실패 시
    """
    import io
    import zipfile

    download_url = f"{DART_CORP_CODE_URL}?crtfc_key={urllib.parse.quote(api_key)}"

    try:
        with urllib.request.urlopen(download_url, timeout=30) as response:
            zipped_bytes = response.read()
    except Exception as download_error:
        raise RuntimeError(f"DART corpCode.xml 다운로드 실패: {download_error}")

    try:
        with zipfile.ZipFile(io.BytesIO(zipped_bytes)) as zip_archive:
            xml_member_name = next(
                member_name
                for member_name in zip_archive.namelist()
                if member_name.lower().endswith(".xml")
            )
            return zip_archive.read(xml_member_name)
    except Exception as unzip_error:
        raise RuntimeError(f"DART corpCode.xml 압축 해제 실패: {unzip_error}")


def fetch_corporation_code_from_dart(stock_code: str, api_key: str) -> Optional[str]:

    """
    종목코드(6자리)로부터 DART 고유 기업코드(8자리)를 조회합니다.
    
    Args:
        stock_code: 6자리 종목코드 (예: "005930")
        api_key: DART API Key
    
    Returns:
        8자리 DART 기업코드 또는 None (실패 시)
    
    Note:
        corpCode.xml 실다운로드 매핑을 우선 시도하고, 실패 시 검증된
        하드코딩 매핑으로 폴백합니다 (offline-first).
    """
    try:
        downloaded_xml_bytes = download_corp_code_xml_bytes_from_dart(api_key)
        downloaded_mapping = parse_corporation_code_mapping_from_corp_code_xml(
            downloaded_xml_bytes
        )
        if stock_code in downloaded_mapping:
            return downloaded_mapping[stock_code]
    except Exception as download_error:
        print(f"Warning: corpCode.xml 조회 실패, 하드코딩 매핑으로 폴백: {download_error}")

    hardcoded_mapping = {
        "005930": "00126380",  # 삼성전자
        "005380": "00164779",  # 현대자동차
        "055550": "00115912",  # 신한지주
    }
    
    return hardcoded_mapping.get(stock_code)


def fetch_annual_financial_statements_from_dart_api(
    stock_code: str,
    corporation_code: str,
    api_key: str,
    fiscal_year: int = 2023,
    number_of_years: int = 5
) -> List[Dict[str, Any]]:
    """
    DART API로부터 지정 사업연도 기준 N개년 연간 재무제표를 수집합니다.
    
    Args:
        stock_code: 6자리 종목코드
        corporation_code: 8자리 DART 기업코드
        api_key: DART API Key
        fiscal_year: 최신 사업연도 (기본값: 2023)
        number_of_years: 수집할 연도 수 (기본값: 5)
    
    Returns:
        연도별 재무제표 원본 데이터 리스트
    
    Raises:
        RuntimeError: API 호출 실패 시
    """
    collected_statements = []
    
    for year_offset in range(number_of_years):
        target_year = fiscal_year - year_offset
        
        params = {
            "crtfc_key": api_key,
            "corp_code": corporation_code,
            "bsns_year": str(target_year),
            "reprt_code": "11011",  # 사업보고서 코드
            "fs_div": "CFS"         # 연결재무제표 (개별: OFS)
        }
        
        url = f"{DART_FINANCIAL_STATEMENT_URL}?{urllib.parse.urlencode(params)}"
        
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                response_data = json.loads(response.read().decode("utf-8"))
                
                if response_data.get("status") == "000":
                    collected_statements.append({
                        "fiscal_year": target_year,
                        "raw_data": response_data.get("list", [])
                    })
                else:
                    error_message = response_data.get("message", "Unknown error")
                    print(f"Warning: DART API 호출 실패 (연도 {target_year}): {error_message}")
        
        except urllib.error.URLError as url_error:
            print(f"Warning: DART API 네트워크 오류 (연도 {target_year}): {url_error}")
        except Exception as general_error:
            print(f"Warning: DART API 처리 중 오류 (연도 {target_year}): {general_error}")
    
    return collected_statements


def load_financial_statements_from_fixture(stock_code: str) -> Optional[List[Dict[str, Any]]]:
    """
    로컬 fixture JSON에서 재무제표 데이터를 로드합니다 (API Key 없을 때 fallback).
    
    Args:
        stock_code: 6자리 종목코드
    
    Returns:
        재무제표 데이터 또는 None (fixture 없을 시)
    """
    fixture_mapping = {
        "005930": "005930_samsung_electronics_dart_financials.json",
        "005380": "005380_hyundai_motor_dart_financials.json",
        "055550": "055550_shinhan_financial_dart_financials.json",
    }
    
    fixture_filename = fixture_mapping.get(stock_code)
    if not fixture_filename:
        return None
    
    fixture_path = Path(__file__).parent.parent.parent / "data" / "fixtures" / fixture_filename
    
    if not fixture_path.exists():
        return None
    
    try:
        with open(fixture_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            statements = data.get("annual_financial_statements", [])
            # 최신 연도부터 내림차순 정렬
            return sorted(statements, key=lambda x: x["fiscal_year"], reverse=True)
    except Exception as error:
        print(f"Warning: Fixture 로드 실패 ({fixture_path}): {error}")
        return None


def collect_normalized_financial_statements(
    stock_code: str,
    fiscal_year: int = 2023,
    number_of_years: int = 5,
    use_fixture_fallback: bool = True
) -> List[NormalizedFinancialStatement]:
    """
    종목코드로부터 정규화된 재무제표 모델 리스트를 수집합니다.
    
    Args:
        stock_code: 6자리 종목코드 (예: "005930")
        fiscal_year: 최신 사업연도 (기본값: 2023)
        number_of_years: 수집할 연도 수 (기본값: 5)
        use_fixture_fallback: API Key 없을 때 fixture 사용 여부
    
    Returns:
        NormalizedFinancialStatement 모델 리스트
    
    Raises:
        ValueError: API Key도 없고 fixture도 없을 때
    """
    api_key = get_dart_api_key_from_environment()
    
    # API Key가 있으면 DART API 호출 시도
    if api_key:
        corporation_code = fetch_corporation_code_from_dart(stock_code, api_key)
        
        if corporation_code:
            try:
                raw_statements = fetch_annual_financial_statements_from_dart_api(
                    stock_code=stock_code,
                    corporation_code=corporation_code,
                    api_key=api_key,
                    fiscal_year=fiscal_year,
                    number_of_years=number_of_years
                )
                
                if raw_statements:
                    print(f"Success: DART API로부터 {len(raw_statements)}개 연도 재무제표 수집 완료")
                    # TODO: 원본 DART 응답을 NormalizedFinancialStatement로 변환하는 normalizer 연동
                    # 현재는 fixture를 사용하여 검증
            except Exception as error:
                print(f"Warning: DART API 호출 중 오류 발생: {error}")
    
    # API Key 없거나 실패 시 fixture fallback
    if use_fixture_fallback:
        print(f"Info: Fixture JSON에서 재무제표 로드 시도 (종목코드: {stock_code})")
        fixture_statements = load_financial_statements_from_fixture(stock_code)
        
        if fixture_statements:
            normalized_statements = [
                NormalizedFinancialStatement.from_dictionary(stmt)
                for stmt in fixture_statements
            ]
            print(f"Success: Fixture에서 {len(normalized_statements)}개 연도 재무제표 로드 완료")
            return normalized_statements
    
    raise ValueError(
        f"재무제표 수집 실패: DART_API_KEY 환경변수가 설정되지 않았고, "
        f"종목코드 {stock_code}에 대한 fixture도 존재하지 않습니다."
    )


def save_financial_statements_to_json_file(
    statements: List[NormalizedFinancialStatement],
    output_file_path: str
) -> None:
    """
    재무제표 모델 리스트를 JSON 파일로 저장합니다.
    
    Args:
        statements: NormalizedFinancialStatement 리스트
        output_file_path: 저장할 JSON 파일 경로
    """
    output_data = {
        "collected_at": datetime.now().isoformat(),
        "statements": [stmt.to_dictionary() for stmt in statements]
    }
    
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(output_data, file, ensure_ascii=False, indent=2)
    
    print(f"Success: 재무제표 데이터를 {output_file_path}에 저장 완료")


def main():
    """
    단독 CLI 실행 진입점 (규칙 3: 모듈 독립성)
    
    Example:
        python -m src.collectors.dart_financial_statement_collector --ticker 005930 --output data/raw/005930.json
    """
    parser = argparse.ArgumentParser(
        description="DART Open API 재무제표 수집기 (독립 실행 모드)"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        required=True,
        help="6자리 종목코드 (예: 005930)"
    )
    parser.add_argument(
        "--fiscal-year",
        type=int,
        default=2023,
        help="최신 사업연도 (기본값: 2023)"
    )
    parser.add_argument(
        "--years",
        type=int,
        default=5,
        help="수집할 연도 수 (기본값: 5)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/raw/collected_financials.json",
        help="출력 JSON 파일 경로"
    )
    parser.add_argument(
        "--no-fixture",
        action="store_true",
        help="Fixture fallback 사용 안 함 (API 전용 모드)"
    )
    
    args = parser.parse_args()
    
    try:
        statements = collect_normalized_financial_statements(
            stock_code=args.ticker,
            fiscal_year=args.fiscal_year,
            number_of_years=args.years,
            use_fixture_fallback=not args.no_fixture
        )
        
        save_financial_statements_to_json_file(statements, args.output)
        
        print("\n=== 수집 요약 ===")
        print(f"종목코드: {args.ticker}")
        print(f"수집 연도 수: {len(statements)}")
        print(f"연도 범위: {statements[-1].fiscal_year} ~ {statements[0].fiscal_year}")
        print(f"출력 파일: {args.output}")
        
    except Exception as error:
        print(f"\nError: 재무제표 수집 실패 - {error}")
        exit(1)


if __name__ == "__main__":
    main()
