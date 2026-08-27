---
name: "Evidence Handoff"
description: "Code.Presso의 신뢰감 있는 블루 언어를 근거 중심 채용 검토에 맞게 확장한 디자인 시스템."
status: draft
created: 2026-08-27
updated: 2026-08-27
sources:
  - "../../prds/prd-Zero100_Builderthon-2026-08-25/prd.md"
  - "../../prds/prd-Zero100_Builderthon-2026-08-25/addendum.md"
  - "../../architecture/architecture-Zero100_Builderthon-2026-08-26/ARCHITECTURE-SPINE.md"
  - "../../architecture/architecture-Zero100_Builderthon-2026-08-26/PRESENTATION-SYSTEM-DESIGN.md"
  - "https://codepresso.io/"
colors:
  surface-base: '#F7F9FC'
  surface-raised: '#FFFFFF'
  surface-subtle: '#F6FAFF'
  surface-selected: '#E7EFFE'
  ink-primary: '#1B1D26'
  ink-secondary: '#4E5566'
  ink-muted: '#838B9D'
  border-default: '#E8EBEE'
  border-strong: '#BEC3CF'
  primary: '#1A61EA'
  primary-hover: '#195CDE'
  primary-pressed: '#173999'
  primary-foreground: '#FFFFFF'
  navy: '#07153D'
  success: '#0F7D68'
  success-subtle: '#E7F6F2'
  warning: '#8A5A00'
  warning-subtle: '#FFF4D6'
  danger: '#B83333'
  danger-subtle: '#FDEBEC'
  focus-ring: '#356DDE'
typography:
  display:
    fontFamily: 'Pretendard, Pretendard JP, sans-serif'
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.25'
    letterSpacing: -0.02em
  heading:
    fontFamily: 'Pretendard, Pretendard JP, sans-serif'
    fontSize: 24px
    fontWeight: '700'
    lineHeight: '1.35'
    letterSpacing: -0.01em
  section:
    fontFamily: 'Pretendard, Pretendard JP, sans-serif'
    fontSize: 18px
    fontWeight: '700'
    lineHeight: '1.4'
  body-lg:
    fontFamily: 'Pretendard, Pretendard JP, sans-serif'
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body:
    fontFamily: 'Pretendard, Pretendard JP, sans-serif'
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.55'
  label:
    fontFamily: 'Pretendard, Pretendard JP, sans-serif'
    fontSize: 13px
    fontWeight: '600'
    lineHeight: '1.4'
  meta:
    fontFamily: 'Pretendard, Pretendard JP, sans-serif'
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.4'
  mono:
    fontFamily: 'JetBrains Mono, monospace'
    fontSize: 12px
    fontWeight: '500'
    lineHeight: '1.5'
rounded:
  sm: 4px
  md: 6px
  lg: 8px
  xl: 12px
  full: 9999px
spacing:
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 20px
  '6': 24px
  '8': 32px
  '10': 40px
  shell-gutter: 24px
  panel-padding: 16px
components:
  workflow-nav:
    background: '{colors.navy}'
    active: '{colors.primary}'
    foreground: '{colors.primary-foreground}'
  context-bar:
    background: '{colors.surface-raised}'
    border: '{colors.border-default}'
    radius: '{rounded.lg}'
  status-badge:
    radius: '{rounded.full}'
    font: '{typography.meta}'
  gate-banner:
    background: '{colors.warning-subtle}'
    foreground: '{colors.warning}'
    radius: '{rounded.lg}'
  calibration-matrix:
    background: '{colors.surface-raised}'
    border: '{colors.border-default}'
    radius: '{rounded.xl}'
  application-row:
    background: '{colors.surface-raised}'
    selected: '{colors.surface-selected}'
    radius: '{rounded.lg}'
  processing-stepper:
    active: '{colors.primary}'
    failed: '{colors.danger}'
  evidence-split-view:
    background: '{colors.surface-raised}'
    divider: '{colors.border-strong}'
    radius: '{rounded.xl}'
  document-viewer:
    background: '{colors.surface-subtle}'
    highlight: '{colors.warning-subtle}'
  evidence-card:
    background: '{colors.surface-raised}'
    selected: '{colors.surface-selected}'
    border: '{colors.border-default}'
    radius: '{rounded.lg}'
  review-control:
    background: '{colors.surface-raised}'
    focus: '{colors.focus-ring}'
    radius: '{rounded.md}'
  reviewer-comparison:
    background: '{colors.surface-subtle}'
    border: '{colors.border-default}'
    radius: '{rounded.lg}'
  handoff-card:
    background: '{colors.surface-raised}'
    border: '{colors.border-default}'
    radius: '{rounded.xl}'
  question-candidate:
    background: '{colors.surface-raised}'
    selected: '{colors.surface-selected}'
    radius: '{rounded.lg}'
  verification-comparison:
    background: '{colors.surface-subtle}'
    border: '{colors.border-default}'
    radius: '{rounded.lg}'
  audit-timeline:
    line: '{colors.border-strong}'
    marker: '{colors.primary}'
  button-primary:
    background: '{colors.primary}'
    foreground: '{colors.primary-foreground}'
    radius: '{rounded.md}'
  field-control:
    background: '{colors.surface-raised}'
    border: '{colors.border-strong}'
    focus: '{colors.focus-ring}'
    radius: '{rounded.md}'
---

## Brand & Style

Evidence Handoff는 후보자를 점수화하는 대시보드가 아니라, 사람이 승인된 기준과 원문을 함께 보며 판단 근거를 남기는 **evidence console**이다. Code.Presso의 선명한 블루, 깨끗한 흰 표면, 짙은 네이비, 데이터 카드의 정돈감을 이어받되 마케팅 페이지의 대형 그래픽과 장식적 그라데이션은 가져오지 않는다.

시각적 위계는 `원문 → 기준 → 사람의 판단` 순서를 지원한다. 블루는 현재 맥락과 행동에만 사용하고, 충족 여부나 합격 가능성처럼 오해될 수 있는 의미에는 사용하지 않는다. 자동 합격·탈락, 종합 점수, 순위가 있는 듯한 차트 표현은 금지한다.

## Colors

- **Code Blue** `{colors.primary}`는 주요 행동, 현재 단계, 선택된 근거의 연결선에만 쓴다. 흰색과 대비는 5.33:1이다.
- **Deep Navy** `{colors.navy}`는 전역 진행 구조와 발표에서 흐름의 중심축을 고정한다. 넓은 본문 배경으로 남용하지 않는다.
- **Paper White / Cool Canvas** `{colors.surface-raised}`와 `{colors.surface-base}`는 고밀도 정보를 카드와 캔버스로 분리한다.
- **Ink** `{colors.ink-primary}`와 `{colors.ink-secondary}`가 본문·보조 본문을 담당한다. `{colors.ink-muted}`는 큰 텍스트나 비필수 메타에만 사용한다.
- **Success / Warning / Danger**는 승인·주의·실패 상태에만 사용한다. 반드시 아이콘과 텍스트 레이블을 함께 둔다. 검토 상태 `충족/부분 충족/미충족/확인 불가`는 색만으로 구분하지 않는다.
- 선택 배경 `{colors.surface-selected}` 위 본문은 `{colors.ink-primary}`를 유지한다. 컬러 배경 위 긴 본문은 두지 않는다.

## Typography

Code.Presso와 언어적 연속성을 유지하기 위해 Pretendard를 기본으로 사용한다. 제목은 700, 기능 이름과 상태 레이블은 600, 장문 근거는 400으로 제한한다. 후보자 이름·검토 사유·인용구는 모두 본문 크기 이상이며 압축된 `meta` 크기로 내리지 않는다.

기준 버전 ID, 처리 실행 ID, 페이지·문단 위치처럼 감사에 필요한 값만 `{typography.mono}`를 사용한다. 영문 대문자 장식 레이블과 과도한 자간은 쓰지 않는다. 한국어는 `word-break: keep-all`, 긴 ID와 원문 URL만 안전하게 줄바꿈한다.

## Layout & Spacing

4px 기반 간격을 사용한다. 데스크톱 작업 캔버스는 최대 1440px이며, 전역 여백은 `{spacing.shell-gutter}`다. 정보가 서로 의존하는 카드 내부는 `{spacing.panel-padding}`, 독립 섹션 사이는 `{spacing.8}` 이상으로 구분한다.

근거 검토의 기준 레이아웃은 55:45 스플릿이다. 왼쪽 `document-viewer`는 원문 읽기 폭을, 오른쪽 `evidence-card` 열은 판단과 기록 폭을 확보한다. 두 검토자의 의견은 좌우 대칭 열로 보여주며 한 열로 합치지 않는다. 표는 고정 헤더와 행 레이블을 유지한다.

## Elevation & Depth

계층은 그림자보다 표면 톤과 테두리로 만든다. 기본 카드는 1px `{colors.border-default}`를 사용한다. 드롭다운·팝오버처럼 실제로 겹치는 요소만 `0 8px 24px rgba(7, 21, 61, 0.10)`을 허용한다. 선택 상태를 그림자만으로 표현하지 않는다.

## Shapes

입력과 버튼은 `{rounded.md}`, 데이터 행과 작은 카드는 `{rounded.lg}`, 주요 작업 패널은 `{rounded.xl}`을 쓴다. `{rounded.full}`은 짧은 상태 배지에만 허용한다. 후보자 카드나 전체 패널을 과도한 pill 형태로 만들지 않는다.

## Components

| 컴포넌트 | 시각 규칙 |
|---|---|
| `workflow-nav` | 네이비 바 위 단계 레이블. 현재 단계만 블루 강조와 `현재` 텍스트를 함께 표시한다. |
| `context-bar` | 포지션, 기준 버전, 승인 상태, 현재 역할을 한 줄에 묶는 흰 표면. 버전 ID는 mono. |
| `status-badge` | 텍스트+아이콘 조합. 상태별 전경/옅은 배경을 사용하고 단독 색 점은 금지한다. |
| `gate-banner` | 승인 전 공식 출력 차단 사유와 다음 행동을 경고색 표면에 표시한다. |
| `calibration-matrix` | 기준 행, HR 열, TECH 열, 충돌 열의 정렬된 매트릭스. 충돌 행만 약한 경고 표면. |
| `application-row` | 이름, 처리 단계, 근거 커버리지 상태, 오류 여부를 한 행에 표시한다. 종합 점수 칸은 두지 않는다. |
| `processing-stepper` | 수신·파싱·매핑·완료 단계를 텍스트와 아이콘으로 표시한다. 실패는 마지막 성공 단계와 함께 보존한다. |
| `evidence-split-view` | 55:45 패널, 명확한 구분선, 각 패널 독립 스크롤. 선택 근거는 양쪽에서 같은 블루 연결 상태를 쓴다. |
| `document-viewer` | PDF/Markdown 원문 표면. 좌표가 있으면 얇은 앰버 하이라이트, 없으면 문맥 박스로 대체한다. |
| `evidence-card` | 기준, 원문 인용구, 위치, 근거 상태를 한 카드에 묶는다. 선택 카드는 블루 테두리+옅은 배경. |
| `review-control` | 4가지 검토 상태와 판단 사유 입력을 묶는다. 포커스 링은 2px `{colors.focus-ring}`. |
| `reviewer-comparison` | HR·TECH를 같은 폭으로 분리하고 이름·역할·근거를 반복 노출한다. 합의된 단일 점수는 표시하지 않는다. |
| `handoff-card` | 적용 기준, 근거, 이견, 미검증 항목, 질문 후보의 구획이 한 화면에서 읽히는 큰 카드. |
| `question-candidate` | 질문, 이유, 연결 기준, 참조 근거, 편집·선택 상태를 수직 구조로 표시한다. 선택은 체크와 레이블을 함께 사용한다. |
| `verification-comparison` | 서류 단계 가설과 면접 검증 결과를 병렬 열로 보여준다. 최종 결정 입력은 별도 구획이다. |
| `audit-timeline` | 버전·행위자·시각·변경을 시간순으로 표시한다. 삭제된 기록도 상태로 보존한다. |
| `button-primary` | 블루 채움, 흰 텍스트. 화면당 하나의 우선 행동에만 사용한다. 위험 행동에는 쓰지 않는다. |
| `field-control` | 1px 테두리와 명시적 레이블. 오류 시 위험색 테두리+오류 문장을 함께 표시한다. |

## Do's and Don'ts

| Do | Don't |
|---|---|
| 블루를 현재 맥락·주요 행동·근거 연결에 사용 | 블루를 `충족`이나 합격 가능성의 암시로 사용 |
| 모든 상태에 텍스트와 아이콘을 병기 | 초록·노랑·빨강 점만으로 상태 구분 |
| 원문과 판단을 시각적으로 분리하되 연결 유지 | AI 요약을 원문보다 더 강하게 표시 |
| HR·TECH 의견을 같은 위계로 병렬 표시 | 두 의견을 평균·점수·단일 결론으로 합치기 |
| 차단 사유와 해제 조건을 같은 화면에 표시 | 비활성 버튼만 두고 이유를 숨기기 |
| Code.Presso의 블루·산세리프·정돈감을 계승 | 홈페이지 일러스트, 광택 그라데이션, 대형 마케팅 타이포 복제 |
