# Spine Pair Review — Zero100_Builderthon

## Overall verdict

**thin.** 핵심 사용자 흐름, 18개 제품 컴포넌트의 양 문서 대응, 토큰 참조, 정해진 문서 구조는 downstream consumer가 안정적으로 추출할 수 있다. 다만 입력 경계의 명시적 대비 위반, 소스에 정의된 상태 열거형의 화면 계약 누락, 질문·핸드오프 권한 주체 충돌은 구현 전에 확정하지 않으면 접근성과 권한·상태 로직이 서로 다르게 만들어질 위험이 있다.

## 1. Flow coverage — adequate

PRD의 세 핵심 유저 플로우 `UF-1 기준 합의와 검토 시작`, `UF-2 근거 기반 지원서 검토`, `UF-3 현업 핸드오프와 인터뷰 검증`은 이름을 그대로 유지한다. 각 흐름에는 이름이 있는 주인공, 번호가 매겨진 단계, 명시적 Climax, 적용 가능한 실패 경로가 있고, `Requirement Coverage`가 FR-001~FR-022를 F1~F3 흐름·표면에 연결한다.

### Findings

- **medium** PDF 업로드와 처리 실행은 FR-012/FR-012b 및 IA의 `지원서 처리 목록`에 포함되지만, 이를 실제로 수행하는 이름 있는 주인공의 Key Flow가 없다. UF-2는 이미 `완료 상태의 대표 지원서`를 선택하는 단계에서 시작하므로 업로드 → 수신 → 파싱 → 매핑 → 완료/실패라는 사용자 경험을 검증하지 않는다 (`EXPERIENCE.md` §Information Architecture, lines 24–32; §Key Flows/UF-2, lines 162–172; §Requirement Coverage, lines 186–192; `prd.md` §FR-012~FR-012b). *Fix:* 민지가 PDF를 업로드하고 처리 상태를 추적하는 짧은 Key Flow를 추가하거나 UF-1의 후속 단계로 확장해 성공·실패·부분 산출물 보존을 명시한다.

## 2. Token completeness — thin

DESIGN.md YAML의 색상·타이포그래피·라운딩·간격·18개 컴포넌트 토큰을 추출했다. 25개의 `{path.to.token}` 참조는 모두 정의된 경로로 해석되고, 모든 색상 토큰은 hex 값을 가진다. 라이트 모드만 제공한다는 가정이 명시되어 있어 light/dark pair 누락은 오류가 아니다.

### Findings

- **high** `field-control`의 기본 경계는 `{colors.border-strong}` (`#BEC3CF`)을 `{colors.surface-raised}` (`#FFFFFF`) 위에 쓰도록 고정되어 있으며 계산 대비는 약 **1.77:1**이다. 이는 EXPERIENCE.md가 약속한 비텍스트 UI 3:1 바닥과 충돌하고, 입력 경계는 downstream 구현이 그대로 복제하는 load-bearing 토큰이다 (`DESIGN.md` YAML `colors.border-strong`, lines 21–22; `components.field-control`, lines 161–165; `EXPERIENCE.md` §Accessibility Floor, lines 119–127). *Fix:* 흰 표면에서 3:1 이상이 되는 입력 전용 border 토큰을 추가하거나, 기본 상태에서도 경계를 대체하는 3:1 이상의 명시적 형태·톤 신호를 계약한다.
- **medium** 상태 배지의 YAML은 radius와 font만 정의하고 성공·주의·실패의 정확한 전경/배경 토큰 쌍을 연결하지 않는다. Colors 본문도 상태별 색을 사용하라고만 하며, 문서에 수치로 기록된 대비는 primary/white 한 쌍뿐이다 (`DESIGN.md` YAML `components.status-badge`; §Colors, lines 174–181; §Components `status-badge`). *Fix:* `status-badge`에 `success-foreground/background`, `warning-foreground/background`, `danger-foreground/background` 참조를 명시하고 각 load-bearing 조합의 검증 대비를 DESIGN.md에 기록한다.

## 3. Component coverage — adequate

제품 고유 컴포넌트 18개는 DESIGN.md YAML `components`, DESIGN.md §Components, EXPERIENCE.md §Component Patterns에서 이름이 정확히 일치하며 각 행에 시각 규칙과 행동 규칙이 있다. 양 문서 사이의 제품 컴포넌트 누락은 없다.

### Findings

- **medium** 공통 상호작용 프리미티브인 skeleton, 상단 탭, 팝오버/편집 모드, 확인 UI, 오류 요약, live region이 EXPERIENCE.md와 DESIGN.md prose에서 실제 구성요소처럼 사용되지만 양 문서의 컴포넌트 계약에는 없다. Foundation은 Tailwind 위의 프로젝트 전용 계층만 말하고 shadcn/MUI 같은 상속 UI 시스템을 지정하지 않아, downstream consumer가 이 프리미티브의 시각·행동 기준을 어디서 상속해야 하는지 알 수 없다 (`DESIGN.md` §Elevation & Depth, line 197; `EXPERIENCE.md` §State Patterns, line 90; §Interaction Primitives, lines 108–115; §Accessibility Floor, line 126; §Responsive & Platform, line 136). *Fix:* 상속할 접근 가능한 UI primitive 시스템을 Foundation에 명시하거나, 최소한 `loading-skeleton`, `tab-switcher`, `dialog/popover`, `error-summary`의 양쪽 spine 행을 추가한다.

## 4. State coverage — thin

IA의 일곱 표면을 순회했다. 전역 초기 로딩·오프라인·권한 없음·저장 실패, 교정 DRAFT/APPROVED와 충돌, 처리 진행/실패, 근거·좌표 없음, 두 번째 검토 없음, 핸드오프 차단, 질문 생성 실패, 면접 전 상태는 명시되어 있다.

### Findings

- **high** Architecture Spine의 명시적 상태 열거형 중 기준 `ARCHIVED`, 처리 `COMPLETED`, 충돌 `RESOLVED`, 질문 `CANDIDATE/SELECTED/DELETED`의 표면별 처리가 State Patterns에 없다. 일부는 컴포넌트 prose에 간접 언급되지만, 진입 가능 여부·레이블·허용 행동·전이 결과를 소비자가 추출할 수 있는 상태 계약은 아니다 (`ARCHITECTURE-SPINE.md` §핵심 상태, lines 100–108; `EXPERIENCE.md` §Component Patterns, lines 72–80; §State Patterns, lines 86–106). *Fix:* 각 열거형을 상태 표의 별도 행으로 만들고 해당 표면, 표시 문구, 가능한 행동, 읽기 전용 여부, 다음 전이를 명시한다.
- **medium** 핸드오프, 면접 검증·최종 결정, 감사 기록 표면은 실패/사전 상태 일부만 있고 정상 생성 중·생성 완료, 최종 결정 저장 완료/이미 확정됨, 감사 기록 empty/filter-empty/load-error 같은 핵심 상태가 없다 (`EXPERIENCE.md` §Information Architecture, lines 30–32; §State Patterns, lines 101–106). 전역 `초기 로딩`과 `저장 실패`만으로는 각 표면에서 불변 기록과 재시도/읽기 전용 행동을 결정하기 어렵다. *Fix:* 세 표면 각각의 cold-load, empty, submitting, success/immutable, stale/conflict, recoverable error 상태를 표로 추가한다.

## 5. Visual reference coverage — adequate

`imports/`, `mockups/`, `wireframes/` 아래 파일은 0개여서 orphan 또는 불명확한 inline 링크는 없다. Code.Presso 방향은 frontmatter source, 두 spine의 본문, `reconcile-codepresso-reference.md`에서 채택·변형·제외 항목으로 구체화되어 있다.

### Findings

- **low** “spines win on conflict” 규칙은 `reconcile-codepresso-reference.md`에만 있고 DESIGN.md 또는 EXPERIENCE.md에는 없다. 현재 시각 파일이 없어 즉시 충돌할 대상은 없지만, 이후 mockup/import가 생기면 소비자가 우선순위를 spine에서 직접 찾을 수 없다 (`reconcile-codepresso-reference.md` 마지막 문단; `DESIGN.md`/`EXPERIENCE.md` 전체). *Fix:* 시각 참조를 처음 연결하는 spine 위치에 “DESIGN.md와 EXPERIENCE.md가 mockup·wireframe·import보다 우선한다”는 문장을 한 번만 명시한다.

## 6. Bloat & overspecification — strong

두 spine은 표와 짧은 규칙 중심이며 PRD의 persona·시장 설명이나 전체 기능 명세를 복사하지 않는다. `Requirement Coverage`는 세 행의 추적표로 압축되어 있고, Evidence & Decision Safety·Responsive·Open Decisions는 공정성, 고밀도 반응형 작업, 구현 전 계약 공백이라는 downstream 결정을 각각 소유한다. 픽셀 값은 토큰·접근성 최소값·검토 레이아웃·breakpoint처럼 실제 구현을 고정해야 하는 곳에 한정되어 있다.

### Findings

없음.

## 7. Inheritance discipline — thin

네 개의 로컬 `sources` 경로는 모두 현재 workspace 기준으로 해석된다. 세 UF 이름은 PRD와 동일하고, 제품 컴포넌트 이름은 양 spine에서 일치하며, EXPERIENCE.md의 DESIGN.md 토큰 참조는 모두 해석된다. 외부 Code.Presso source는 이번 검증에서 재탐색하지 않았고, 로컬 memlog와 reconciliation 기록을 근거로 확인했다.

### Findings

- **high** 질문 수정·삭제·선택과 핸드오프 생성의 행위자가 source 내부 및 EXPERIENCE.md 사이에서 하나로 확정되지 않았다. Architecture AD-5는 “검토자가 수정·삭제, 현업 리더가 선택”이라고 하고, AD-9는 LEAD가 핸드오프·질문 선택을 담당한다고 하며, Structural Seed는 TECH가 핸드오프 생성을 촉발한 뒤 LEAD가 수정·삭제·선택하는 것으로 그린다. EXPERIENCE.md는 LEAD가 세 질문 행동과 핸드오프 생성을 수행한다고 가정하면서 Open Decisions로 남긴다 (`ARCHITECTURE-SPINE.md` §AD-5, lines 66–72; §AD-9, lines 93–97; §Structural Seed, lines 192–196; `EXPERIENCE.md` §Component Patterns `question-candidate`, line 80; §UF-3, lines 176–179; §Open Decisions, lines 194–204). 이 상태로 story/API 권한을 만들면 서로 다른 역할 계약이 구현될 수 있다. *Fix:* `생성`, `수정`, `삭제`, `선택`별 RACI/권한 행렬을 하나로 확정하고 Architecture와 EXPERIENCE를 동시에 갱신한다.

## 8. Shape fit — strong

DESIGN.md의 본문 섹션은 Brand & Style → Colors → Typography → Layout & Spacing → Elevation & Depth → Shapes → Components → Do's and Don'ts의 canonical order를 정확히 따른다. EXPERIENCE.md는 Foundation, Information Architecture, Voice and Tone, Component Patterns, State Patterns, Interaction Primitives, Accessibility Floor, Key Flows를 모두 포함하며, 반응형 웹과 참조 제품이 있으므로 필요한 Responsive & Platform 및 Inspiration & Anti-patterns도 있다. Evidence & Decision Safety, Requirement Coverage, Open Decisions는 제품의 채용 공정성·추적성·미결정 계약을 위해 역할이 분명하다.

### Findings

없음.

## Mechanical notes

- DESIGN.md YAML frontmatter는 파싱되며 필수 `name`, `description`, `colors`, `typography`, `rounded`, `spacing`, `components`가 존재한다. 색상 21개는 모두 hex, typography 값은 허용 필드, rounded/spacing 값은 CSS dimension 형태다.
- `{path.to.token}` 고유 참조 25개는 모두 DESIGN.md YAML 경로로 해석된다. 미해결 참조는 0개다.
- 제품 컴포넌트는 YAML 18개, DESIGN.md §Components 18개, EXPERIENCE.md §Component Patterns 18개이며 차집합은 양방향 0개다.
- 네 개의 로컬 source 경로는 모두 존재한다. `https://codepresso.io/`는 사용자 지시에 따라 네트워크 재검증하지 않았고 `.memlog.md`와 `reconcile-codepresso-reference.md`의 로컬 조사 기록으로 대체했다.
- DESIGN.md canonical section order와 EXPERIENCE.md 필수/조건부 section 존재를 확인했다. 두 spine 자체에는 Mermaid block이 없으므로 Mermaid syntax 검사항목은 해당 없음이다.
- 시각 자산 디렉터리의 파일 수: `imports/` 0, `mockups/` 0, `wireframes/` 0. orphan은 0개다.

