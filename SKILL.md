---
name: i18n-sync
description: i18n 번역 파일 동기화 및 검증. "번역 동기화", "i18n 검사", "누락 번역", "번역 키 추가", "다국어 동기화", "i18n sync", "translation sync", "missing translations" 요청에 사용.
---

# i18n-sync

다국어 번역 파일 동기화, 누락 키 감지, 번역 파일 검증을 수행합니다.

## 지원 구조

```
src/lib/i18n/messages/
├── [domain]/
│   ├── ko.json  (기준 언어)
│   ├── en.json
│   └── ja.json
```

## 핵심 명령

### 1. 누락 키 검사

모든 도메인의 누락 번역 키를 검사합니다.

```bash
# 전체 검사
find src/lib/i18n/messages -type d -mindepth 1 -maxdepth 1 | while read domain; do
  echo "=== $(basename $domain) ==="
  ko_keys=$(jq -r 'paths(scalars) | join(".")' "$domain/ko.json" 2>/dev/null | sort)
  for lang in en ja; do
    if [ -f "$domain/$lang.json" ]; then
      lang_keys=$(jq -r 'paths(scalars) | join(".")' "$domain/$lang.json" 2>/dev/null | sort)
      missing=$(comm -23 <(echo "$ko_keys") <(echo "$lang_keys"))
      if [ -n "$missing" ]; then
        echo "[$lang] 누락: $(echo "$missing" | wc -l | tr -d ' ')개"
        echo "$missing" | head -5
      fi
    fi
  done
done
```

### 2. 특정 도메인 동기화

기준 언어(ko)의 키를 다른 언어 파일에 동기화합니다.

**워크플로우:**
1. ko.json의 모든 키 추출
2. 대상 언어 파일에서 누락된 키 확인
3. 누락 키에 `[TODO: 번역필요]` 플레이스홀더 추가
4. 기존 번역은 유지

**예시:**
```javascript
// ko.json에 새 키 추가됨
{ "button": { "save": "저장", "cancel": "취소" } }

// en.json 동기화 후
{ "button": { "save": "[TODO: 번역필요] 저장", "cancel": "Cancel" } }
```

### 3. 번역 파일 검증

```
✅ 검증 항목:
- JSON 구문 유효성
- 키 일관성 (기준 언어 대비)
- 빈 값 감지
- TODO 플레이스홀더 잔존 확인
- 중첩 구조 일치
```

### 4. 일괄 동기화

모든 도메인을 한번에 동기화합니다.

## 실행 모드

| 모드 | 설명 |
|------|------|
| `--check` | 누락 키만 검사 (수정 없음) |
| `--sync` | 누락 키에 플레이스홀더 추가 |
| `--domain [name]` | 특정 도메인만 처리 |
| `--lang [code]` | 특정 언어만 처리 |

## 사용 예시

**"번역 동기화해줘"** → 전체 검사 후 누락 키 보고
**"analytics 도메인 번역 동기화"** → analytics 폴더 동기화
**"일본어 번역 누락 확인"** → ja.json 파일들만 검사

## 동기화 로직

```
ko.json (기준)
    │
    ├── 키 A ──→ en.json에 A 없음 → "[TODO: 번역필요] {ko값}" 추가
    │
    ├── 키 B ──→ en.json에 B 있음 → 기존 값 유지
    │
    └── 키 C ──→ en.json에 C 있음 → 기존 값 유지
```

## 출력 형식

```
=== 번역 동기화 결과 ===

📁 analytics
  ├─ en.json: ✅ 동기화됨 (3개 키 추가)
  └─ ja.json: ⚠️ 5개 누락

📁 common
  ├─ en.json: ✅ 완료
  └─ ja.json: ✅ 완료

총계: 16개 도메인, 3개 키 추가, 5개 TODO 남음
```
