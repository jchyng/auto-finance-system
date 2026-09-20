# 프로젝트 핵심 규칙 및 미니멀 스펙 정의서
> **Project Rules & Lean Tech Spec**
> 원칙: "과도한 것은 배제한다. 지금 딱 필요한 최소한으로 시작하고, 필요가 생길 때 점진적으로 확장한다."

---

## 1. 프로젝트 필수 유지 규칙 (Non-Negotiable Rules)

### [규칙 1] 투자 표현의 객관성 유지 (No Investment Advice)
* "매수 추천", "매도 추천", "저평가 확정", "좋은 기업", "나쁜 기업" 등 **주관적/단정적 표현은 코드, 주석, 출력 화면, AI 프롬프트 전반에서 일절 금지**한다.
* 시스템은 오직 **"계산된 숫자"**, **"과거 5년 평균과의 차이"**, **"업종 평균과의 차이"** 등 객관적 팩트만 문장으로 서술한다.
* 데이터가 없거나 적자로 왜곡된 경우 억지로 값을 추정하지 않고 명시적으로 `데이터 부족` 또는 `판단불가`로 표기한다.

### [규칙 2] 엔지니어링과 AI의 엄격한 경계 (Strict Separation)
* **모든 지표 계산, 평균 집계, 상태 판정은 100% Python 일반 코드**로 수행한다.
* AI(LLM)는 오직 계산 완료된 수치 요약과 쉬운 금융 용어 설명에만 관여한다.
* AI 호출이 실패하거나 오프라인 상태여도 시스템은 **기본 템플릿으로 100% 정상 작동**해야 한다 (Graceful Fallback).

### [규칙 3] 모듈 독립성 (Unix Philosophy: Standalone & Composable)
* 각 기능(수집, 정제, 계산, 평가, 설명)은 **다른 모듈 없이도 단독 실행(CLI)과 독립 테스트(Unit Test)가 가능**해야 한다.
* 모듈 간 입출력은 표준 Python 딕셔너리 또는 표준 JSON 규격으로만 통신한다.

### [규칙 4] 미니멀리즘과 YAGNI (You Aren't Gonna Need It)
* 지금 당장 필요 없는 무거운 프레임워크, 분산 큐, 복잡한 ORM, 대형 프론트엔드는 선제 도입하지 않는다.
* 외부 라이브러리는 **"반드시 필요한가? 표준 라이브러리로 대체할 수 없는가?"**를 검토한 후 최소한만 추가한다.

### [규칙 5] 점진적 구현 및 검증 (One Step at a Time)
* 한 번에 여러 기능을 몰아서 구현하지 않는다.
* 반드시 **[기능 하나 구현] -> [단독 테스트 및 검증] -> [사용자 확인] -> [다음 단계]** 순서로 진행한다.

### [규칙 6] 명확하고 설명적인 명명 규칙 (No Cryptic Names - Self-Documenting)
* **축약어 및 모호한 단어 사용 금지**: `fin`, `calc`, `eval`, `norm`, `df`, `val`, `res`, `tmp`, `data`, `info`, `obj` 등 유추해야 하는 축약어는 파일명, 클래스명, 함수명, 변수명에서 일절 사용하지 않는다.
* **이름만 보고도 역할과 단위를 즉시 파악 가능하도록 명명**:
  * 파일명 예시: `financial_statement_models.py`, `dart_financial_statement_collector.py`, `financial_indicator_calculator.py`
  * 변수명 예시: `revenue_growth_rate_percentage`, `operating_profit_margin_percentage`, `debt_to_equity_ratio_percentage`, `free_cash_flow_amount_krw`
  * 함수명 예시: `calculate_revenue_growth_rate()`, `evaluate_debt_to_equity_ratio()`, `fetch_annual_financial_statements_from_dart()`

### [규칙 7] 커밋 메시지 컨벤션 (Conventional Commits)
* 커밋 메시지는 **Conventional Commits 규약**을 따른다.
* 형식: `<type>(<scope>): <간결한 요약>

<본문 설명>`
* **type** (필수, 소문자): `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `style`, `build`, `ci`, `revert`
* **scope**: 작업 범위를 명시했을 때에만 선택적으로 사용 (예: `feat(calculator): ...`)
* **요약**: 필수, 명령문 형태로 간결하게 서술 (예: `지표 계산 기능 추가`)
* **본문(Body)**: 변경 이유와 주요 변경 사항을 bullet로 명확하게 설명 (생략 가능하나 `fix`/`refactor` 등 동기 설명이 필요한 변경에는 포함)
* 예시:
  ```
  docs: 시스템 명세 및 프로젝트 문서 초기 커밋

  시스템 사양, 프로젝트 규칙, 모듈 구현 계획 문서와
  .gitignore 설정을 포함한 첫 커밋.
  ```

---

## 2. 미니멀 기술 스펙 및 공식 데이터 소스 (Official & Free Lean Stack)

"공식적인 자료나 API, 정확하고 간편하며 무료(또는 저비용)"라는 원칙에 맞추어 국가 공인 데이터 소스를 확정합니다.

| 분류 | 선정 기술/소스 | 공식 여부 및 비용 | 선정 이유 |
| :--- | :--- | :--- | :--- |
| **재무제표** | **금융감독원 DART Open API** | **100% 공식 / 무료** (1일 10,000회) | 법정 공시 사업보고서 원본. 대한민국에서 가장 정확한 재무 데이터 |
| **주가/시가총액** | **한국거래소(KRX) 공식 데이터 (`pykrx` / Open API)** | **100% 공식 / 무료** | 거래소 공식 주가, 시가총액, 상장주식수를 가장 간편하게 수집 |
| **업종 벤치마크** | **KRX 업종 지수 / WICS 분류** | **공식 및 표준 벤치마크 / 무료** | 업종 평균 PER, PBR 및 업종 소속 분류 데이터 제공 |
| **언어/런타임** | **Python 3.13** (기설치 완료) | 무료 / 오픈소스 | 데이터 분석 생태계 표준 |
| **데이터 모델** | **Python 표준 `dataclasses`** | 내장 표준 (외부 패키지 X) | 의존성 없이 가장 가볍고 엄격한 타입 모델링 |
| **로컬 저장소** | **로컬 JSON / `sqlite3` (내장)** | 내장 표준 (서버 설치 X) | API 호출 절약 및 오프라인 단독 테스트 지원 |
| **실행 인터페이스**| **Python 표준 `argparse` (CLI)** | 내장 표준 (서버 띄울 필요 X) | 각 모듈을 터미널에서 즉시 독립 실행 가능 |

> [!TIP]
> **API 키 관리 및 개발 편의성 원칙**:
> 1. DART API Key는 환경변수 또는 `.env`에 안전하게 보관합니다 (DART 인증키는 누구나 1분 만에 무료 발급 가능).
> 2. **DART 키가 없는 상태에서도 즉시 개발과 테스트가 가능하도록**, 삼성전자/현대차/신한지주의 **실제 DART 공식 공시 원본 샘플 JSON을 기본 내장(Fixture)**합니다. 키 발급 전에도 100% 독립 실행 및 계산 검증이 가능합니다.

---

## 3. 명확한 명칭의 프로젝트 디렉토리 구조 (Explicit Lean Structure)

```text
C:\Users\jcy03\dev\
├── docs/                                          # 프로젝트 설계 및 규칙 문서
│   ├── PROJECT_RULES.md                           # 프로젝트 핵심 규칙 및 스펙
│   ├── SYSTEM_SPECIFICATION.md                    # 시스템 상세 정의서 (15개 지표/기준)
│   └── MODULAR_IMPLEMENTATION_PLAN.md             # 단계별 구현 계획
├── src/                                           # 소스 코드
│   ├── __init__.py
│   ├── models/                                    # 명확한 데이터 모델
│   │   ├── __init__.py
│   │   ├── financial_statement_models.py          # 원본/정제 재무제표 규격
│   │   ├── investment_indicator_models.py         # 15개 투자지표 규격
│   │   └── indicator_evaluation_models.py         # 상태 판정 결과 규격
│   ├── collectors/                                # 독립 데이터 수집기
│   │   ├── __init__.py
│   │   ├── dart_financial_statement_collector.py  # DART 공시 재무제표 수집기
│   │   ├── krx_stock_price_collector.py           # KRX 주가 및 시가총액 수집기
│   │   └── krx_industry_benchmark_collector.py    # KRX 업종 벤치마크 수집기
│   ├── normalizers/                               # 데이터 정제기
│   │   ├── __init__.py
│   │   └── financial_statement_normalizer.py      # 재무제표 계정과목 표준화 정제기
│   ├── engines/                                   # 결정론적 계산 및 평가 엔진
│   │   ├── __init__.py
│   │   ├── financial_indicator_calculator.py      # 15개 지표 수학 계산기
│   │   └── investment_indicator_evaluator.py      # 상태 판정(양호/보통/주의) 평가기
│   ├── explainers/                                # 해설 및 리포트 포맷터
│   │   ├── __init__.py
│   │   ├── financial_term_dictionary.py           # 금융 초보자용 용어 사전
│   │   └── financial_report_explainer.py          # 사실 요약 및 리포트 생성기
│   ├── investment_analysis_pipeline.py            # 전 과정 오케스트레이션 파이프라인
│   └── investment_analysis_cli.py                 # 통합 커맨드라인 인터페이스
├── tests/                                         # 독립 단위 테스트
│   ├── test_financial_statement_models.py
│   ├── test_financial_indicator_calculator.py
│   └── test_investment_indicator_evaluator.py
├── data/
│   └── fixtures/                                  # 오프라인 검증용 실제 DART 공시 샘플
│       ├── 005930_samsung_electronics_dart_financials.json
│       ├── 005380_hyundai_motor_dart_financials.json
│       └── 055550_shinhan_financial_dart_financials.json
└── requirements.txt                               # 최소 필수 패키지 목록
```
