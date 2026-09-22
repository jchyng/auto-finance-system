# TODO — 남은 단계 (Step 8 별도 단계: G2(a) 실데이터 수집 + G4 온라인 종단 검증)

> 기준: `docs/STEP8_REAL_COMPANY_VERIFICATION.md` §6~§7 (Step 8 = "통과, 범위: 공시 기반 샘플/근사 fixture 기준")
> 최신 커밋: `daf3f7e feat(normalizers): DART 실데이터 계정명 매칭 로직 보강`
> 검증일: 2026-09-23 — DART API 키로 3사 실수집·정제 검증 완료 (fixture 재생성 전)

---

## TODO-1. G2(a): DART 실데이터로 fixture 재생성 → Step 8 재검증 [선행조건: DART_API_KEY — 달성]

- [x] 1-1. `DART_API_KEY` 발급 후 환경변수(또는 `.env`)에 설정
- [x] 1-2. 3사 실데이터 수집 검증 (`--no-fixture`)
  - 005930 삼성전자: 5개년(2019~2023) 수집·정제 성공
  - 005380 현대자동차: 5개년(2019~2023) 수집·정제 성공
  - 055550 신한지주: 2023년 1개년 수집·정제 성공 (2019~2022는 DART API `status=013` 미제공 — API 한계로 확인)
- [x] 1-3. 정제(normalizer) 연동 — DART 원본 → `NormalizedFinancialStatement` 변환 완료 (`convert_dart_raw_statements_to_normalized_statements`)
  - 보강 완료: 괄호 설명 계정명 매칭(`법인세비용(수익)` 등), CIS 섹션 우선 선택, 금융업 대용 수익(이자수익+수수료수익), DART 기업코드 하드코딩 오류 2건 수정(현대차·신한지주)
  - 참고: 삼성전자 2023 연결(CFS)에는 감가상각비·이자비용 세부 계정이 없어 별도 소스 보강 필요 (EV/EBITDA·이자보상배율 영향)
- [ ] 1-4. `data/fixtures/` 재생성 — **보류**: (a) 신한지주 5개년 실데이터 미확보, (b) 감가상각비 등 일부 계정 미제공으로 fixture 대체 시 지표 품질 저하 우려. 보강 소스 확보 후 진행
- [ ] 1-5. Step 8 기준값(baseline) 갱신: `tests/test_step8_real_company_verification.py` `REAL_COMPANY_VERIFICATION_TARGETS` 교체 (fixture 재생성 완료 시)
- [ ] 1-6. 재검증 실행 (fixture 재생성 완료 시)
  - `python -m src.investment_analysis_cli --ticker {005930,005380,055550} --save-intermediate`
  - `python -m pytest tests/test_step8_real_company_verification.py -v`
- [ ] 1-7. `docs/STEP8_REAL_COMPANY_VERIFICATION.md` §3.3·§6·§7 갱신
- [ ] 완료 기준: Step 8 테스트 15 passed + 전체 회귀 통과 + 검증문서 "실측 공시 기준 통과" 명시

---

## TODO-2. G4 잔여: 온라인 종단 검증 (실 API 키 설정 환경)

- [x] 2-1. DART `corpCode.xml` 실다운로드 검증 — 3사 기업코드 실조회 성공, 하드코딩 오류 2건 발견·수정 (현대차 00164742, 신한지주 00382199)
- [x] 2-2. KRX 업종 평균 집계: 집계 함수 단위 테스트 통과 / **실동작은 KRX_ID·KRX_PW 로그인 필요 확인** (`data.krx.co.kr`가 비로그인 요청 차단 → 403/LOGOUT). `.env`에 `KRX_ID`·`KRX_PW` 자리 마련, 입력 시 실동작 검증 예정
  - 집계 상한(현재 50종목 샘플) 적절성 검토: 전수 집계 vs 샘플링 기준 문서화
- [ ] 2-3. `--no-fixture` 종단 실행 (3사) — **보류**: KRX 주가·업종 벤치마크가 로그인 없이는 수집 불가하여 KRX 계정 확보 후 진행 (fixture 폴백은 정상 동작 확인)
- [ ] 2-4. `docs/STEP8_REAL_COMPANY_VERIFICATION.md` §G4·§6·§7 갱신 (KRX 실동작 포함)
- [ ] 완료 기준: 3사 `--no-fixture` 실행 정상 종료 + 리포트 생성 + 검증문서 반영

---

## TODO-3. 회귀 및 커밋 (분할 실행 — 전체 일괄 실행 타임아웃 회피)

- [x] 3-1. 분할 회귀: 16+45+16+17 = **94 passed** (2026-09-23), fixture 경로 회귀 없음 확인
- [x] 3-2. Conventional Commits 커밋: `daf3f7e feat(normalizers): DART 실데이터 계정명 매칭 로직 보강`

