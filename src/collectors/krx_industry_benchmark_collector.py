"""
KRX 업종 벤치마크 수집기 (KRX Industry Benchmark Collector)

pykrx 라이브러리를 통해 KRX 업종 평균 지표를 수집합니다.
- 동일 업종(sector) 동료 종목의 PER/PBR만 집계 (KOSPI 임의 샘플링 금지)
- 규칙 3(모듈 독립성) 준수: 단독 CLI 실행 가능
- 규칙 6(명확한 명명) 준수: 축약어 없는 완전한 함수명
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

try:
    from pykrx import stock as pykrx_stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    print("Warning: pykrx 라이브러리가 설치되어 있지 않습니다. fixture 모드만 사용 가능합니다.")

from src.models.financial_statement_models import IndustryBenchmarkData


# fixture·데모용 검증된 업종 매핑 (종목코드 → 업종코드, 업종명)
KNOWN_INDUSTRY_CLASSIFICATIONS = {
    "005930": ("264", "반도체와반도체장비"),
    "005380": ("301", "자동차"),
    "055550": ("401", "은행/금융지주"),
}

FINANCIAL_INDUSTRY_NAME_KEYWORDS = (
    "은행",
    "증권",
    "보험",
    "금융지주",
    "금융",
    "카드",
)


def is_financial_industry_classification_name(industry_name: str) -> bool:
    """업종명으로 금융업(은행/증권/보험 등) 여부를 판정합니다."""
    if not industry_name:
        return False
    return any(keyword in industry_name for keyword in FINANCIAL_INDUSTRY_NAME_KEYWORDS)


def get_industry_classification_for_stock(stock_code: str) -> Optional[Tuple[str, str]]:
    """
    종목코드로부터 업종 분류를 조회합니다.

    Args:
        stock_code: 6자리 종목코드

    Returns:
        (업종코드, 업종명) 튜플 또는 None
    """
    # 1) pykrx 업종분류 현황에서 조회 (가능하면 하드코딩보다 우선)
    live_classification = fetch_industry_classification_from_sector_table(stock_code)
    if live_classification:
        return live_classification

    # 2) 검증된 fixture 종목 폴백
    return KNOWN_INDUSTRY_CLASSIFICATIONS.get(stock_code)


def fetch_industry_classification_from_sector_table(
    stock_code: str,
    base_date: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """pykrx 업종분류 표에서 종목의 업종명/코드를 조회합니다."""
    if not PYKRX_AVAILABLE:
        return None

    normalized_base_date = base_date or get_latest_trading_date_string_from_stock_collector()

    for market_name in ("KOSPI", "KOSDAQ"):
        try:
            sector_dataframe = pykrx_stock.get_market_sector_classifications(
                normalized_base_date, market_name
            )
        except Exception as error:
            print(f"Warning: 업종분류 조회 실패 ({market_name}): {error}")
            continue

        if sector_dataframe is None or getattr(sector_dataframe, "empty", True):
            continue

        peer_rows = extract_peer_rows_matching_stock(
            sector_dataframe, stock_code
        )
        if peer_rows is None:
            # 종목 자체 행만 찾기
            own_row = find_stock_row_in_sector_dataframe(sector_dataframe, stock_code)
            if own_row is None:
                continue
            industry_name = extract_industry_name_from_sector_row(own_row)
            if not industry_name:
                continue
            return (industry_name, industry_name)

        industry_name = peer_rows[0][1]
        return (industry_name, industry_name)

    return None


def find_stock_row_in_sector_dataframe(sector_dataframe, stock_code: str):
    """업종분류 DataFrame에서 종목 행을 찾습니다."""
    try:
        if stock_code in sector_dataframe.index:
            return sector_dataframe.loc[stock_code]
    except Exception:
        pass

    for column_name in ("티커", "종목코드", "단축코드", "종목"):
        if column_name not in getattr(sector_dataframe, "columns", []):
            continue
        matched = sector_dataframe[sector_dataframe[column_name].astype(str) == stock_code]
        if not matched.empty:
            return matched.iloc[0]
    return None


def extract_industry_name_from_sector_row(sector_row) -> Optional[str]:
    """업종분류 행에서 업종명 컬럼을 추출합니다."""
    for column_name in ("업종명", "지수업종대분류", "업종", "sector", "산업"):
        try:
            value = sector_row[column_name] if column_name in sector_row.index else None
        except Exception:
            value = None
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def extract_peer_rows_matching_stock(
    sector_dataframe,
    stock_code: str,
) -> Optional[List[Tuple[str, str]]]:
    """
    동일 업종 동료 (ticker, industry_name) 목록을 반환합니다.

    Returns:
        동료 목록 또는 종목/업종을 찾지 못하면 None
    """
    own_row = find_stock_row_in_sector_dataframe(sector_dataframe, stock_code)
    if own_row is None:
        return None

    industry_name = extract_industry_name_from_sector_row(own_row)
    if not industry_name:
        return None

    peers: List[Tuple[str, str]] = []
    industry_column = None
    for column_name in ("업종명", "지수업종대분류", "업종", "sector", "산업"):
        if column_name in getattr(sector_dataframe, "columns", []):
            industry_column = column_name
            break

    if industry_column is None:
        return [(stock_code, industry_name)]

    matched = sector_dataframe[
        sector_dataframe[industry_column].astype(str).str.strip() == industry_name
    ]
    for ticker_value, row in matched.iterrows():
        ticker = str(ticker_value)
        if "티커" in matched.columns:
            ticker = str(row["티커"])
        elif len(ticker) != 6:
            continue
        peers.append((ticker.zfill(6), industry_name))

    return peers or [(stock_code, industry_name)]


def resolve_industry_peer_tickers(
    stock_code: str,
    industry_name: str,
    base_date: Optional[str] = None,
    maximum_peer_count: int = 50,
) -> List[str]:
    """
    동일 업종 동료 종목코드 목록을 반환합니다.

    KOSPI 전 종목 임의 샘플링은 하지 않습니다. 업종 동료를 확정할 수 없으면 빈 목록.
    """
    if not PYKRX_AVAILABLE:
        return []

    normalized_base_date = base_date or get_latest_trading_date_string_from_stock_collector()
    peer_tickers: List[str] = []

    for market_name in ("KOSPI", "KOSDAQ"):
        try:
            sector_dataframe = pykrx_stock.get_market_sector_classifications(
                normalized_base_date, market_name
            )
        except Exception:
            continue

        if sector_dataframe is None or getattr(sector_dataframe, "empty", True):
            continue

        peers = extract_peer_rows_matching_stock(sector_dataframe, stock_code)
        if not peers:
            # 업종명으로 직접 필터 (종목 행을 못 찾은 경우)
            for column_name in ("업종명", "지수업종대분류", "업종"):
                if column_name not in getattr(sector_dataframe, "columns", []):
                    continue
                matched = sector_dataframe[
                    sector_dataframe[column_name].astype(str).str.strip() == industry_name
                ]
                for ticker_value in matched.index:
                    ticker = str(ticker_value)
                    if len(ticker) == 6:
                        peer_tickers.append(ticker)
                break
            continue

        peer_tickers.extend(ticker for ticker, _ in peers)

    # 중복 제거, 대상 종목 포함 유지, 상한
    unique_peers: List[str] = []
    seen = set()
    for ticker in peer_tickers:
        if ticker not in seen:
            seen.add(ticker)
            unique_peers.append(ticker)
        if len(unique_peers) >= maximum_peer_count:
            break

    return unique_peers


def aggregate_industry_benchmark_from_company_ratios(
    industry_code: str,
    industry_name: str,
    company_valuation_ratios: list,
    base_date: Optional[str] = None,
) -> Optional[IndustryBenchmarkData]:
    """개별 종목의 PER/PBR 목록으로부터 업종 평균 벤치마크를 집계합니다 (G4).

    Args:
        industry_code: 업종 코드
        industry_name: 업종명
        company_valuation_ratios: (per, pbr) 튜플 목록 (None 허용)
        base_date: 기준일

    Returns:
        IndustryBenchmarkData 모델 또는 None (집계할 값이 없을 때)
    """
    collected_per_values = [
        per_value
        for per_value, _ in company_valuation_ratios
        if per_value is not None and per_value > 0
    ]
    collected_pbr_values = [
        pbr_value
        for _, pbr_value in company_valuation_ratios
        if pbr_value is not None and pbr_value > 0
    ]

    if not collected_per_values and not collected_pbr_values:
        return None

    def calculate_rounded_average(values: list) -> Optional[float]:
        if not values:
            return None
        return round(sum(values) / len(values), 1)

    return IndustryBenchmarkData(
        industry_classification_code=industry_code,
        industry_classification_name=industry_name,
        average_operating_profit_margin_percentage=None,
        average_return_on_equity_percentage=None,
        average_debt_to_equity_ratio_percentage=None,
        average_price_to_earnings_ratio=calculate_rounded_average(
            collected_per_values
        ),
        average_price_to_book_ratio=calculate_rounded_average(
            collected_pbr_values
        ),
        base_date=base_date or "",
        data_source_name="KRX 정보데이터시스템(pykrx 동업종 집계)",
    )


def get_latest_trading_date_string_from_stock_collector() -> str:
    """주가 수집기와 동일한 규칙으로 최근 거래일 문자열을 반환합니다."""
    base_date = datetime.now() - timedelta(days=10)
    return base_date.strftime("%Y%m%d")


def fetch_industry_benchmark_from_krx(
    industry_code: str,
    industry_name: str,
    base_date: Optional[str] = None,
    stock_code: Optional[str] = None,
) -> Optional[IndustryBenchmarkData]:
    """
    pykrx를 통해 동일 업종 동료의 PER/PBR 평균을 수집합니다.

    Args:
        industry_code: 업종 코드
        industry_name: 업종명
        base_date: 기준일 (YYYYMMDD 형식)
        stock_code: 대상 종목 (동료 필터링에 사용)

    Returns:
        IndustryBenchmarkData 모델 또는 None

    Note:
        업종 동료를 확정할 수 없으면 None을 반환해 fixture 폴백을 유지합니다.
        KOSPI 전 종목의 앞에서 N개를 샘플링하지 않습니다.
    """
    if not PYKRX_AVAILABLE:
        return None

    if not stock_code:
        print("Info: 종목코드 없이 업종 동료를 확정할 수 없어 fixture 폴백을 사용합니다.")
        return None

    normalized_base_date = (
        base_date
        if base_date
        else get_latest_trading_date_string_from_stock_collector()
    )

    peer_tickers = resolve_industry_peer_tickers(
        stock_code=stock_code,
        industry_name=industry_name,
        base_date=normalized_base_date,
    )
    if not peer_tickers:
        print(
            f"Info: '{industry_name}' 동업종 동료를 확정할 수 없어 fixture 폴백을 사용합니다."
        )
        return None

    collected_ratios = []
    for ticker in peer_tickers:
        try:
            fundamental = pykrx_stock.get_market_fundamental_by_date(
                normalized_base_date, normalized_base_date, ticker
            )
            if fundamental is None or fundamental.empty:
                continue
            latest_row = fundamental.iloc[-1]
            per_raw = latest_row.get("PER", 0)
            pbr_raw = latest_row.get("PBR", 0)
            collected_ratios.append((
                float(per_raw) if per_raw else None,
                float(pbr_raw) if pbr_raw else None,
            ))
        except Exception:
            continue

    aggregated = aggregate_industry_benchmark_from_company_ratios(
        industry_code, industry_name, collected_ratios, normalized_base_date
    )
    if aggregated is None:
        print("Info: 업종 벤치마크 집계값이 없어 fixture 폴백을 사용합니다.")
    return aggregated


def load_industry_benchmark_from_fixture(stock_code: str) -> Optional[IndustryBenchmarkData]:
    """
    로컬 fixture JSON에서 업종 벤치마크 데이터를 로드합니다.
    
    Args:
        stock_code: 6자리 종목코드
    
    Returns:
        IndustryBenchmarkData 모델 또는 None
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
            benchmark_data = data.get("industry_benchmark")
            
            if benchmark_data:
                return IndustryBenchmarkData.from_dictionary(benchmark_data)
    except Exception as error:
        print(f"Warning: Fixture 로드 실패 ({fixture_path}): {error}")
    
    return None


def collect_industry_benchmark_data(
    stock_code: str,
    base_date: Optional[str] = None,
    use_fixture_fallback: bool = True
) -> IndustryBenchmarkData:
    """
    종목코드로부터 해당 업종의 벤치마크 데이터를 수집합니다.
    
    Args:
        stock_code: 6자리 종목코드
        base_date: 기준일 (YYYYMMDD 형식)
        use_fixture_fallback: pykrx 실패 시 fixture 사용 여부
    
    Returns:
        IndustryBenchmarkData 모델
    
    Raises:
        ValueError: 데이터 수집 실패 시
    """
    if PYKRX_AVAILABLE:
        industry_info = get_industry_classification_for_stock(stock_code)
        
        if industry_info:
            industry_code, industry_name = industry_info
            result = fetch_industry_benchmark_from_krx(
                industry_code,
                industry_name,
                base_date,
                stock_code=stock_code,
            )
            
            if result:
                print(f"Success: KRX에서 {industry_name} 업종 벤치마크 수집 완료")
                return result
    
    if use_fixture_fallback:
        print(f"Info: Fixture JSON에서 업종 벤치마크 로드 시도 (종목코드: {stock_code})")
        fixture_result = load_industry_benchmark_from_fixture(stock_code)
        
        if fixture_result:
            print(f"Success: Fixture에서 {fixture_result.industry_classification_name} 업종 벤치마크 로드 완료")
            return fixture_result
    
    raise ValueError(
        f"업종 벤치마크 데이터 수집 실패: pykrx가 설치되지 않았거나 수집 실패했으며, "
        f"종목코드 {stock_code}에 대한 fixture도 존재하지 않습니다."
    )


def save_industry_benchmark_to_json_file(
    benchmark_data: IndustryBenchmarkData,
    output_file_path: str
) -> None:
    """
    업종 벤치마크 데이터를 JSON 파일로 저장합니다.
    
    Args:
        benchmark_data: IndustryBenchmarkData 모델
        output_file_path: 저장할 JSON 파일 경로
    """
    output_data = {
        "collected_at": datetime.now().isoformat(),
        "industry_benchmark": benchmark_data.to_dictionary()
    }
    
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(output_data, file, ensure_ascii=False, indent=2)
    
    print(f"Success: 업종 벤치마크 데이터를 {output_file_path}에 저장 완료")


def main():
    """
    단독 CLI 실행 진입점
    
    Example:
        python -m src.collectors.krx_industry_benchmark_collector --ticker 005930 --output data/raw/005930_industry.json
    """
    parser = argparse.ArgumentParser(
        description="KRX 업종 벤치마크 수집기 (독립 실행 모드)"
    )
    parser.add_argument(
        "--ticker",
        type=str,
        required=True,
        help="6자리 종목코드 (예: 005930)"
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="기준일 (YYYYMMDD 형식)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/raw/industry_benchmark.json",
        help="출력 JSON 파일 경로"
    )
    parser.add_argument(
        "--no-fixture",
        action="store_true",
        help="Fixture fallback 사용 안 함"
    )
    
    args = parser.parse_args()
    
    try:
        benchmark_data = collect_industry_benchmark_data(
            stock_code=args.ticker,
            base_date=args.date,
            use_fixture_fallback=not args.no_fixture
        )
        
        save_industry_benchmark_to_json_file(benchmark_data, args.output)
        
        print("\n=== 수집 요약 ===")
        print(f"업종 코드: {benchmark_data.industry_classification_code}")
        print(f"업종명: {benchmark_data.industry_classification_name}")
        print(f"평균 영업이익률: {benchmark_data.average_operating_profit_margin_percentage}%")
        print(f"평균 ROE: {benchmark_data.average_return_on_equity_percentage}%")
        print(f"평균 PER: {benchmark_data.average_price_to_earnings_ratio}배")
        print(f"평균 PBR: {benchmark_data.average_price_to_book_ratio}배")
        print(f"기준일: {benchmark_data.base_date}")
        print(f"출력 파일: {args.output}")
        
    except Exception as error:
        print(f"\nError: 업종 벤치마크 수집 실패 - {error}")
        exit(1)


if __name__ == "__main__":
    main()
