# i18n-sync

[![Claude Code Skill](https://img.shields.io/badge/Claude%20Code-Skill-blueviolet)](https://claude.ai/code)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> 다국어 번역 파일 동기화, 누락 키 감지, 번역 파일 검증을 자동화하는 Claude Code 스킬

## 개요

i18n-sync는 다국어 프로젝트에서 번역 파일 관리를 자동화합니다. 기준 언어(ko.json)를 기반으로 다른 언어 파일의 누락된 키를 감지하고, 동기화하며, 검증합니다.

### 주요 기능

- **누락 키 감지** - 기준 언어 대비 누락된 번역 키 자동 탐지
- **자동 동기화** - 누락된 키에 `[TODO: 번역필요]` 플레이스홀더 자동 추가
- **파일 검증** - JSON 구문, 키 일관성, 빈 값 검사
- **도메인별 처리** - 특정 도메인/언어만 선택적 처리 가능

## 설치

### 요구사항

- [Claude Code CLI](https://claude.ai/code) 설치 필요
- `jq` 명령어 (JSON 처리용)

### 스킬 설치

```bash
# 스킬 디렉토리 생성
mkdir -p ~/.claude/skills/i18n-sync

# SKILL.md 파일 복사
cp SKILL.md ~/.claude/skills/i18n-sync/
```

또는 직접 클론:

```bash
git clone https://github.com/your-username/i18n-sync.git ~/.claude/skills/i18n-sync
```

## 지원 구조

다음과 같은 도메인 기반 i18n 구조를 지원합니다:

```
src/lib/i18n/messages/
├── analytics/
│   ├── ko.json  ← 기준 언어
│   ├── en.json
│   └── ja.json
├── common/
│   ├── ko.json
│   ├── en.json
│   └── ja.json
└── [domain]/
    ├── ko.json
    ├── en.json
    └── ja.json
```

## 사용법

Claude Code에서 자연어로 명령하면 자동으로 스킬이 활성화됩니다.

### 트리거 키워드

| 한국어 | English |
|--------|---------|
| 번역 동기화 | i18n sync |
| i18n 검사 | translation sync |
| 누락 번역 | missing translations |
| 번역 키 추가 | sync translations |
| 다국어 동기화 | check i18n |

### 명령 예시

```
# 전체 검사
"번역 동기화해줘"
"i18n 검사해줘"

# 특정 도메인만
"analytics 도메인 번역 동기화"
"common 폴더 번역 검사"

# 특정 언어만
"일본어 번역 누락 확인"
"영어 번역 동기화"

# 검증
"번역 파일 유효성 검사"
```

## 동작 원리

### 동기화 로직

```
ko.json (기준)
    │
    ├── 키 A ──→ en.json에 A 없음 → "[TODO: 번역필요] {ko값}" 추가
    │
    ├── 키 B ──→ en.json에 B 있음 → 기존 값 유지
    │
    └── 키 C ──→ en.json에 C 있음 → 기존 값 유지
```

### 동기화 전후 예시

**ko.json** (새 키 추가됨)
```json
{
  "button": {
    "save": "저장",
    "cancel": "취소",
    "delete": "삭제"
  }
}
```

**en.json** (동기화 전)
```json
{
  "button": {
    "save": "Save",
    "cancel": "Cancel"
  }
}
```

**en.json** (동기화 후)
```json
{
  "button": {
    "save": "Save",
    "cancel": "Cancel",
    "delete": "[TODO: 번역필요] 삭제"
  }
}
```

## 실행 모드

| 모드 | 설명 | 예시 |
|------|------|------|
| `--check` | 누락 키만 검사 (수정 없음) | "번역 검사만 해줘" |
| `--sync` | 누락 키에 플레이스홀더 추가 | "번역 동기화해줘" |
| `--domain [name]` | 특정 도메인만 처리 | "analytics 동기화" |
| `--lang [code]` | 특정 언어만 처리 | "일본어만 동기화" |

## 출력 형식

```
=== 번역 동기화 결과 ===

📁 analytics
  ├─ en.json: ✅ 동기화됨 (3개 키 추가)
  └─ ja.json: ⚠️ 5개 누락

📁 common
  ├─ en.json: ✅ 완료
  └─ ja.json: ✅ 완료

📁 settings
  ├─ en.json: ✅ 완료
  └─ ja.json: ⚠️ 2개 누락

────────────────────────────
총계: 16개 도메인
  ✅ 동기화: 3개 키 추가
  ⚠️ TODO 남음: 7개
```

## 검증 항목

스킬이 검사하는 항목:

| 항목 | 설명 |
|------|------|
| JSON 구문 유효성 | 파싱 가능한 올바른 JSON인지 |
| 키 일관성 | 기준 언어(ko) 대비 모든 키 존재 여부 |
| 빈 값 감지 | 빈 문자열("") 값 탐지 |
| TODO 플레이스홀더 | `[TODO: 번역필요]` 잔존 확인 |
| 중첩 구조 일치 | 객체 중첩 구조가 동일한지 |

## 설정 커스터마이징

### 기준 언어 변경

SKILL.md에서 기준 언어를 변경할 수 있습니다:

```markdown
# 기준 언어: en.json으로 변경
ko_keys=$(jq -r 'paths(scalars) | join(".")' "$domain/en.json" ...)
```

### 지원 언어 추가

```markdown
# 중국어(zh) 추가
for lang in en ja zh; do
  ...
done
```

### 플레이스홀더 형식 변경

```markdown
# 기본: [TODO: 번역필요]
# 변경: [TRANSLATE]
"[TRANSLATE] {ko값}"
```

## 트러블슈팅

### jq 설치 필요

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# Windows (chocolatey)
choco install jq
```

### 권한 오류

```bash
chmod -R 755 ~/.claude/skills/i18n-sync
```

### 스킬이 트리거되지 않음

Claude Code를 재시작하거나, 더 명확한 키워드 사용:
```
"i18n-sync 스킬로 번역 동기화해줘"
```

## 관련 스킬

- [skill-wizard](https://github.com/your-username/skill-wizard) - Claude Code 스킬 생성 가이드
- [skill-creator](https://github.com/your-username/skill-creator) - 스킬 템플릿 생성기

## 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능합니다.

## 작성자

Claude Code Skill by [@your-username](https://github.com/your-username)

---

**Made with Claude Code**
