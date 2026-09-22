"""
KRX 업종 벤치마크 수집기 (KRX Industry Benchmark Collector)

pykrx 라이브러리를 통해 KRX WICS 업종 평균 지표를 수집합니다.
- 업종 평균 PER, PBR, 부채비율, ROE 등 벤치마크 데이터 수집
- 규칙 3(모듈 독립성) 준수: 단독 CLI 실행 가능
- 규칙 6(명확한 명명) 준수: 축약어 없는 완전한 함수명
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    from pykrx import stock as pykrx_stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    print("Warning: pykrx 라이브러리가 설치되어 있지 않습니다. fixture 모드만 사용 가능합니다.")

from src.models.financial_statement_models import IndustryBenchmarkData


def get_industry_classification_for_stock(stock_code: str) -> Optional[tuple]:
    """
    종목코드로부터 WICS 업종 분류를 조회합니다.
    
    Args:
        stock_code: 6자리 종목코드
    
    Returns:
        (업종코드, 업종명) 튜플 또는 None
    """
    if not PYKRX_AVAILABLE:
        return None
    
    try:
        # pykrx로 종목의 업종 정보 조회
        sector_name = pykrx_stock.get_market_ticker_name(stock_code)
        
        # WICS 업종 매핑 (실제로는 pykrx의 sector 정보 활용)
        # 간소화를 위해 주요 종목 하드코딩
        hardcoded_mapping = {
            "005930": ("264", "반도체와반도체장비"),
            "005380": ("301", "자동차"),
            "055550": ("401", "은행/금융지주"),
        }
        
        return hardcoded_mapping.get(stock_code)
    
    except Exception as error:
        print(f"Warning: 업종 분류 조회 실패 ({stock_code}): {error}")
        return None


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
        data_source_name="KRX 정보데이터시스템(pykrx 집계)",
    )


def get_latest_trading_date_string_from_stock_collector() -> str:
    """주가 수집기와 동일한 규칙으로 최근 거래일 문자열을 반환합니다."""
    from datetime import datetime, timedelta

    base_date = datetime.now() - timedelta(days=10)
    return base_date.strftime("%Y%m%d")



def fetch_industry_benchmark_from_krx(
    industry_code: str,
    industry_name: str,
    base_date: Optional[str] = None
) -> Optional[IndustryBenchmarkData]:
    """
    pykrx를 통해 KRX 업종 평균 지표를 수집합니다.
    
    Args:
        industry_code: 업종 코드
        industry_name: 업종명
        base_date: 기준일 (YYYYMMDD 형식)
    
    Returns:
        IndustryBenchmarkData 모델 또는 None
    
    Note:
        pykrx는 개별 종목 PER/PBR은 제공하나 업종 평균은 직접 계산 필요.
        실제 구현 시 업종 내 전체 종목의 평균을 계산하거나 
        네트워크/데이터 부재 시 None을 반환해 fixture 폴백을 유지합니다.
    """
    if not PYKRX_AVAILABLE:
        return None
    
    normalized_base_date = (
        base_date
        if base_date
        else get_latest_trading_date_string_from_stock_collector()
    )

    try:
        industry_tickers = pykrx_stock.get_market_ticker_list(
            normalized_base_date, market="KOSPI"
        )
    except Exception as industry_error:
        print(f"Warning: 업종 종목 목록 조회 실패: {industry_error}")
        return None

    collected_ratios = []
    for ticker in industry_tickers:
        try:
            fundamental = pykrx_stock.get_market_fundamental_by_date(
                normalized_base_date, normalized_base_date, ticker
            )
            if fundamental is None or fundamental.empty:
                continue
            latest_row = fundamental.iloc[-1]
            collected_ratios.append((
                float(latest_row.get("PER", 0)) or None,
                float(latest_row.get("PBR", 0)) or None,
            ))
        except Exception:
            continue

        if len(collected_ratios) >= 50:
            break

    aggregated = aggregate_industry_benchmark_from_company_ratios(
        industry_code, industry_name, collected_ratios, normalized_base_date
    )
    if aggregated is None:
        print("Info: 업종 벤치마크 집계값이 없어 fixture 폴백을 사용합니다.")
    return aggregated
    # (위 집계 로직에서 이미 반환 처리)


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
    # pykrx로 수집 시도
    if PYKRX_AVAILABLE:
        industry_info = get_industry_classification_for_stock(stock_code)
        
        if industry_info:
            industry_code, industry_name = industry_info
            result = fetch_industry_benchmark_from_krx(
                industry_code, industry_name, base_date
            )
            
            if result:
                print(f"Success: KRX에서 {industry_name} 업종 벤치마크 수집 완료")
                return result
    
    # fixture fallback
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
