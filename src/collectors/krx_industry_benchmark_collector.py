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
            "055550": ("401", "은행"),
        }
        
        return hardcoded_mapping.get(stock_code)
    
    except Exception as error:
        print(f"Warning: 업종 분류 조회 실패 ({stock_code}): {error}")
        return None


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
        KRX 공식 업종 지수 데이터를 활용해야 합니다.
        간소화를 위해 현재는 fixture 기반으로 구현합니다.
    """
    if not PYKRX_AVAILABLE:
        return None
    
    # TODO: 실제 KRX 업종 평균 계산 로직 구현
    # 현재는 fixture로 대체
    print("Info: 업종 벤치마크는 현재 fixture 기반으로만 제공됩니다.")
    return None


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
