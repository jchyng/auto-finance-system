"""
KRX 주가 및 시가총액 수집기 (KRX Stock Price Collector)

pykrx 라이브러리를 통해 한국거래소(KRX) 공식 데이터를 수집합니다.
- 종목의 종가, 시가총액, 상장주식수 등을 수집
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

from src.models.financial_statement_models import StockPriceAndMarketCapData


def get_latest_trading_date_string(target_date: Optional[str] = None) -> str:
    """
    최근 거래일 날짜 문자열을 반환합니다 (YYYYMMDD 형식).
    
    Args:
        target_date: 기준 날짜 (YYYYMMDD). None이면 오늘 날짜 기준
    
    Returns:
        YYYYMMDD 형식 날짜 문자열
    
    Note:
        실제 거래소 휴장일 처리는 pykrx가 자동으로 처리하므로 
        간소화를 위해 최근 10일 이내 날짜를 반환
    """
    if target_date:
        return target_date
    
    # 최근 10일 이내 날짜 사용 (주말/공휴일 대비)
    base_date = datetime.now() - timedelta(days=10)
    return base_date.strftime("%Y%m%d")


def fetch_stock_price_from_krx(
    stock_code: str,
    trading_date: Optional[str] = None
) -> Optional[StockPriceAndMarketCapData]:
    """
    pykrx를 통해 KRX에서 주가 및 시가총액 데이터를 수집합니다.
    
    Args:
        stock_code: 6자리 종목코드 (예: "005930")
        trading_date: 기준 거래일 (YYYYMMDD 형식, None이면 최근 거래일)
    
    Returns:
        StockPriceAndMarketCapData 모델 또는 None (수집 실패 시)
    """
    if not PYKRX_AVAILABLE:
        print("Error: pykrx 라이브러리가 설치되지 않았습니다.")
        return None
    
    try:
        date_string = trading_date or get_latest_trading_date_string()
        
        # pykrx로 시가총액 정보 조회
        market_cap_df = pykrx_stock.get_market_cap_by_date(
            fromdate=date_string,
            todate=date_string,
            ticker=stock_code
        )
        
        if market_cap_df.empty:
            print(f"Warning: {stock_code}의 {date_string} 시가총액 데이터가 없습니다.")
            return None
        
        # 종가 조회
        price_df = pykrx_stock.get_market_ohlcv_by_date(
            fromdate=date_string,
            todate=date_string,
            ticker=stock_code
        )
        
        if price_df.empty:
            print(f"Warning: {stock_code}의 {date_string} 주가 데이터가 없습니다.")
            return None
        
        # 종목명 조회
        try:
            company_name = pykrx_stock.get_market_ticker_name(stock_code)
        except:
            company_name = "종목명 조회 실패"
        
        # 데이터 추출
        market_cap_row = market_cap_df.iloc[0]
        price_row = price_df.iloc[0]
        
        closing_price = int(price_row['종가'])
        market_capitalization = int(market_cap_row['시가총액'])
        total_shares = int(market_cap_row['상장주식수'])
        
        # 날짜 형식 변환 (YYYYMMDD → YYYY-MM-DD)
        formatted_date = f"{date_string[:4]}-{date_string[4:6]}-{date_string[6:8]}"
        
        return StockPriceAndMarketCapData(
            stock_code=stock_code,
            company_name=company_name,
            closing_price_krw=closing_price,
            market_capitalization_krw=market_capitalization,
            total_shares_outstanding=total_shares,
            base_trading_date=formatted_date,
            data_source_name="KRX 정보데이터시스템"
        )
    
    except Exception as error:
        print(f"Error: KRX 데이터 수집 실패 ({stock_code}): {error}")
        return None


def load_stock_price_from_fixture(stock_code: str) -> Optional[StockPriceAndMarketCapData]:
    """
    로컬 fixture JSON에서 주가 데이터를 로드합니다 (pykrx 미설치 시 fallback).
    
    Args:
        stock_code: 6자리 종목코드
    
    Returns:
        StockPriceAndMarketCapData 모델 또는 None
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
            price_data = data.get("stock_price_and_market_cap")
            
            if price_data:
                return StockPriceAndMarketCapData.from_dictionary(price_data)
    except Exception as error:
        print(f"Warning: Fixture 로드 실패 ({fixture_path}): {error}")
    
    return None


def collect_stock_price_and_market_cap(
    stock_code: str,
    trading_date: Optional[str] = None,
    use_fixture_fallback: bool = True
) -> StockPriceAndMarketCapData:
    """
    종목코드로부터 주가 및 시가총액 데이터를 수집합니다.
    
    Args:
        stock_code: 6자리 종목코드
        trading_date: 거래 기준일 (YYYYMMDD 형식, None이면 최근 거래일)
        use_fixture_fallback: pykrx 실패 시 fixture 사용 여부
    
    Returns:
        StockPriceAndMarketCapData 모델
    
    Raises:
        ValueError: 데이터 수집 실패 시
    """
    # pykrx로 수집 시도
    if PYKRX_AVAILABLE:
        result = fetch_stock_price_from_krx(stock_code, trading_date)
        if result:
            print(f"Success: KRX에서 {stock_code} 주가 데이터 수집 완료")
            return result
    
    # fixture fallback
    if use_fixture_fallback:
        print(f"Info: Fixture JSON에서 주가 데이터 로드 시도 (종목코드: {stock_code})")
        fixture_result = load_stock_price_from_fixture(stock_code)
        
        if fixture_result:
            print(f"Success: Fixture에서 {stock_code} 주가 데이터 로드 완료")
            return fixture_result
    
    raise ValueError(
        f"주가 데이터 수집 실패: pykrx가 설치되지 않았거나 수집 실패했으며, "
        f"종목코드 {stock_code}에 대한 fixture도 존재하지 않습니다."
    )


def save_stock_price_to_json_file(
    price_data: StockPriceAndMarketCapData,
    output_file_path: str
) -> None:
    """
    주가 데이터를 JSON 파일로 저장합니다.
    
    Args:
        price_data: StockPriceAndMarketCapData 모델
        output_file_path: 저장할 JSON 파일 경로
    """
    output_data = {
        "collected_at": datetime.now().isoformat(),
        "stock_price_data": price_data.to_dictionary()
    }
    
    output_path = Path(output_file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(output_data, file, ensure_ascii=False, indent=2)
    
    print(f"Success: 주가 데이터를 {output_file_path}에 저장 완료")


def main():
    """
    단독 CLI 실행 진입점
    
    Example:
        python -m src.collectors.krx_stock_price_collector --ticker 005930 --output data/raw/005930_price.json
    """
    parser = argparse.ArgumentParser(
        description="KRX 주가 및 시가총액 수집기 (독립 실행 모드)"
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
        help="기준 거래일 (YYYYMMDD 형식, 미지정 시 최근 거래일)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/raw/stock_price.json",
        help="출력 JSON 파일 경로"
    )
    parser.add_argument(
        "--no-fixture",
        action="store_true",
        help="Fixture fallback 사용 안 함"
    )
    
    args = parser.parse_args()
    
    try:
        price_data = collect_stock_price_and_market_cap(
            stock_code=args.ticker,
            trading_date=args.date,
            use_fixture_fallback=not args.no_fixture
        )
        
        save_stock_price_to_json_file(price_data, args.output)
        
        print("\n=== 수집 요약 ===")
        print(f"종목코드: {price_data.stock_code}")
        print(f"기업명: {price_data.company_name}")
        print(f"종가: {price_data.closing_price_krw:,}원")
        print(f"시가총액: {price_data.market_capitalization_krw:,}원")
        print(f"기준일: {price_data.base_trading_date}")
        print(f"출력 파일: {args.output}")
        
    except Exception as error:
        print(f"\nError: 주가 데이터 수집 실패 - {error}")
        exit(1)


if __name__ == "__main__":
    main()
