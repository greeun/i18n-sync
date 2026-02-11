---
name: i18n-sync
description: |
  Framework-agnostic i18n translation file sync and validation.
  Auto-detects project i18n structure (Next.js, React, Vue, Angular, Rails, etc.).
  "i18n sync", "translation sync", "missing translations", "check translations",
  "sync locales", "add missing translations", "validate translations",
  "번역 동기화", "i18n 검사", "누락 번역", "번역 키 추가", "다국어 동기화",
  "번역 검증", "번역 파일 확인".
---

# i18n-sync

Auto-detects any project's i18n structure and performs translation file synchronization, missing key detection, and validation.

## Supported Patterns

Automatically detects these structures:

| Type | Example | Frameworks |
|------|---------|------------|
| `locale_first` | `locales/{locale}/{namespace}.json` | react-i18next, vue-i18n |
| `domain_first` | `messages/{domain}/{locale}.json` | Custom setups |
| `flat_locale` | `locales/{locale}.json` | next-intl, simple projects |

Supported formats: JSON, YAML. Detects framework from `package.json`, `Gemfile`, `pubspec.yaml`.

## Workflow

### Step 1: Detect Project Structure

```bash
python3 ~/.claude/skills/i18n-sync/scripts/detect_i18n.py . --pretty
```

Parse the JSON output and present a summary to the user:
- Framework detected (if any)
- i18n directory path
- Structure type
- Locales found with key counts
- Reference locale (auto-detected: most keys)
- Whether sync is needed

If `detected: false`, inform the user and suggest using `--path` to specify the i18n directory manually.

Save detection output for the next step:
```bash
python3 ~/.claude/skills/i18n-sync/scripts/detect_i18n.py . > /tmp/i18n_config.json
```

### Step 2: Check or Sync

**Check only (no modifications):**
```bash
python3 ~/.claude/skills/i18n-sync/scripts/sync_i18n.py --config /tmp/i18n_config.json --check --pretty
```

**Sync (add placeholders for missing keys):**
```bash
python3 ~/.claude/skills/i18n-sync/scripts/sync_i18n.py --config /tmp/i18n_config.json --sync --pretty
```

**Dry run (preview changes without writing):**
```bash
python3 ~/.claude/skills/i18n-sync/scripts/sync_i18n.py --config /tmp/i18n_config.json --sync --dry-run --pretty
```

### Step 3: Validate (optional)

```bash
python3 ~/.claude/skills/i18n-sync/scripts/sync_i18n.py --config /tmp/i18n_config.json --validate --pretty
```

Checks: JSON syntax, key consistency, empty values, TODO placeholders, structure consistency.

## Script Reference

### detect_i18n.py

```
python3 detect_i18n.py [project_dir]
  --path PATH      Override i18n directory (skip auto-detection)
  --ref LOCALE     Force reference locale (e.g., en, ko)
  --format FORMAT  Force file format: json, yaml
  --pretty         Pretty-print output
```

**Output fields:**
- `detected` (bool): Whether i18n structure was found
- `framework` (string|null): Detected framework name
- `i18n_root` (string): Relative path to i18n directory
- `structure_type` (string): `locale_first`, `domain_first`, `flat_locale`
- `file_format` (string): `json` or `yaml`
- `reference_locale` (string): Auto-detected reference language code
- `target_locales` (array): All non-reference locale codes
- `locales` (array): Per-locale details with key counts
- `namespaces` (array|null): Namespace/domain names
- `summary.needs_sync` (bool): Whether any locale has missing keys

### sync_i18n.py

```
python3 sync_i18n.py --config <path> --check|--sync|--validate
  --locale CODE        Process specific locale only
  --namespace NAME     Process specific namespace/domain only
  --placeholder TEXT   Custom placeholder (default: "[TODO: translate]")
  --dry-run            Preview changes without writing (sync mode)
  --pretty             Pretty-print output
```

**Check output fields:**
- `results[].missing_keys` (array): Keys in reference but not in target
- `results[].extra_keys` (array): Keys in target but not in reference
- `results[].empty_keys` (array): Keys with empty string values
- `results[].todo_keys` (array): Keys with TODO placeholder values
- `summary.total_missing_keys` (int): Total missing keys across all files

**Sync output fields:**
- `results[].keys_added` (array): Keys that were added
- `results[].already_synced` (bool): Whether file was already in sync
- `summary.total_keys_added` (int): Total keys added
- `summary.files_modified` (int): Files that were changed

**Validate output fields:**
- `results[].errors` (array): Critical issues (missing keys, parse errors, structure mismatches)
- `results[].warnings` (array): Non-critical issues (extra keys, empty values, TODO residue)
- `results[].valid` (bool): Whether file passed validation
- `summary.all_valid` (bool): Whether all files passed

## Decision Tree

| User Request | Action |
|-------------|--------|
| "번역 동기화" / "i18n sync" / "sync translations" | Detect -> Check -> report results, ask to sync |
| "번역 검사" / "check translations" / "missing translations" | Detect -> Check only |
| "번역 동기화해줘" / "sync now" | Detect -> Sync (add placeholders) |
| "번역 검증" / "validate translations" | Detect -> Validate |
| "[locale] 번역 확인" / "check [locale]" | Detect -> Check with --locale |
| "[namespace] 동기화" / "sync [namespace]" | Detect -> Sync with --namespace |
| "번역 추가해줘" / "translate missing keys" | Detect -> Check -> use Claude to translate and Edit files |

When the user asks Claude to actually translate (not just add placeholders), use the check output to identify missing keys, then use Claude's Read/Edit tools to add proper translations.

## Output Format

Present results to the user in this format:

```
=== i18n Sync Report ===

Project: [framework or "Generic"]
Structure: [structure_type]
Reference: [reference_locale] ([total_keys] keys)
Targets: [target_locales]

[namespace or filename]
  [locale]: [status] ([details])

Summary: [totals]
```

Status icons:
- In sync, no issues
- Has missing keys
- Has TODO placeholders remaining
- Parse error or structural issue

## Manual Override

When auto-detection fails, specify the path explicitly:

```bash
# Custom i18n directory
python3 ~/.claude/skills/i18n-sync/scripts/detect_i18n.py . --path src/custom/i18n --pretty

# Force reference locale
python3 ~/.claude/skills/i18n-sync/scripts/detect_i18n.py . --ref en --pretty

# Force YAML format
python3 ~/.claude/skills/i18n-sync/scripts/detect_i18n.py . --format yaml --pretty
```

## Sync Logic

```
reference_locale file (auto-detected, most keys)
    |
    +-- Key A --> target has A? --> Yes: keep existing value
    |                           --> No:  add "[TODO: translate] {ref_value}"
    |
    +-- Key B --> target has B? --> Yes: keep existing value
    |                           --> No:  add "[TODO: translate] {ref_value}"
    ...
```

Existing translations are never overwritten. Only missing keys are added.
