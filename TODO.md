# TODO — 남은 단계 (Step 8 별도 단계: G2(a) 실데이터 수집 + G4 온라인 종단 검증)

> 기준: `docs/STEP8_REAL_COMPANY_VERIFICATION.md` §6~§7 (Step 8 = "통과, 범위: 공시 기반 샘플/근사 fixture 기준")
> 선행 완료: G1/G3/G5 완료, G2(b) 재라벨링 완료, G4 뼈대 구현 + 오프라인 폴백 유지
> 최신 커밋: `daa410d feat(collectors): DART corpCode 파싱과 KRX 업종평균 집계 뼈대 구현`

---

## TODO-1. G2(a): DART 실데이터로 fixture 재생성 → Step 8 재검증 [선행조건: DART_API_KEY]

- [ ] 1-1. `DART_API_KEY` 발급 후 환경변수(또는 `.env`)에 설정
  - 확인: `python -c "import os; print(bool(os.environ.get('DART_API_KEY')))"` → `True`
- [ ] 1-2. 3사 5개년 실데이터 수집 (사업보고서 `11011` + 연결 `CFS` 기준)
  - `python -m src.collectors.dart_financial_statement_collector --ticker 005930 --fiscal-year 2023 --years 5 --output data/raw/005930_dart_raw_financials.json --no-fixture`
  - `python -m src.collectors.dart_financial_statement_collector --ticker 005380 --fiscal-year 2023 --years 5 --output data/raw/005380_dart_raw_financials.json --no-fixture`
  - `python -m src.collectors.dart_financial_statement_collector --ticker 055550 --fiscal-year 2023 --years 5 --output data/raw/055550_dart_raw_financials.json --no-fixture`
- [ ] 1-3. 정제(normalizer) 연동 확인 — 수집 원본이 `NormalizedFinancialStatement`로 변환되는지 확인
  - 현 상태 메모: `collect_normalized_financial_statements()`의 실 API 경로에 normalizer 연동 TODO 잔존 → 필요 시 `src/normalizers/financial_statement_normalizer.py` 연동 후 진행
- [ ] 1-4. `data/fixtures/005{930,380}_*_dart_financials.json`, `data/fixtures/055550_*_dart_financials.json` 재생성 (헤드라인 실측 + 세부 계정 실측 교체)
- [ ] 1-5. Step 8 기준값(baseline) 갱신: `tests/test_step8_real_company_verification.py`의 `REAL_COMPANY_VERIFICATION_TARGETS`를 실측 기반 값으로 교체
  - 주의: 신한지주 ROIC·이자보상배율은 금융업 예외로 `None` 유지
- [ ] 1-6. 재검증 실행
  - `python -m src.investment_analysis_cli --ticker 005930 --save-intermediate`
  - `python -m src.investment_analysis_cli --ticker 005380 --save-intermediate`
  - `python -m src.investment_analysis_cli --ticker 055550 --save-intermediate`
  - `python -m pytest tests/test_step8_real_company_verification.py -v`
- [ ] 1-7. `docs/STEP8_REAL_COMPANY_VERIFICATION.md` §3.3·§6·§7 갱신 ("실측 공시 기준 통과"로 승격, G2(a) 체크)
- [ ] 완료 기준: Step 8 테스트 15 passed + 전체 회귀 통과 + 검증문서 "실측 공시 기준 통과" 명시

---

## TODO-2. G4 잔여: 온라인 종단 검증 (실 API 키 설정 환경)

- [ ] 2-1. DART `corpCode.xml` 실다운로드 검증
  - `fetch_corporation_code_from_dart("005930", <실키>)` → `"00126380"` 반환 확인 (하드코딩 폴백 미사용 경로)
- [ ] 2-2. KRX 업종 평균 집계 실동작 검증
  - `fetch_industry_benchmark_from_krx("264", "반도체와반도체장비", "20240329")` → `IndustryBenchmarkData` 반환(또는 정당한 `None`+fixture 폴백) 확인
  - 집계 상한(현재 50종목 샘플) 적절성 검토: 전수 집계 vs 샘플링 기준 문서화
- [ ] 2-3. `--no-fixture` 종단 실행 (3사)
  - `python -m src.investment_analysis_cli --ticker 005930 --no-fixture`
  - `python -m src.investment_analysis_cli --ticker 005380 --no-fixture`
  - `python -m src.investment_analysis_cli --ticker 055550 --no-fixture`
- [ ] 2-4. `docs/STEP8_REAL_COMPANY_VERIFICATION.md` §G4·§6·§7 갱신 ("온라인 종단 검증 완료" 명시, G4 체크)
- [ ] 완료 기준: 3사 `--no-fixture` 실행 정상 종료 + 리포트 생성 + 검증문서 반영

---

## TODO-3. 회귀 및 커밋 (TODO-1/2 완료 후)

- [ ] 3-1. 분할 회귀 (전체 일괄 실행 타임아웃 회피)
  - `python -m pytest tests/test_dart_financial_statement_collector.py tests/test_krx_collectors.py tests/test_financial_indicator_calculator.py -q`
  - `python -m pytest tests/test_investment_indicator_evaluator.py tests/test_financial_statement_models.py tests/test_financial_statement_normalizer.py tests/test_financial_report_explainer.py -q`
  - `python -m pytest tests/test_step8_real_company_verification.py -q`
  - `python -m pytest tests/test_dart_financial_statement_collector.py tests/test_krx_collectors.py tests/test_investment_analysis_pipeline.py -q`
- [ ] 3-2. Conventional Commits 커밋 (예: `feat(data): ...`, `test: ...`, `docs: ...` 분리)
- [ ] 완료 기준: 4개 분할 모두 passed + 워킹트리 깨끗 (`git status --short --branch` 출력 없음)
