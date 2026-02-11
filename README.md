# i18n-sync

Framework-agnostic i18n translation file synchronization and validation for [Claude Code](https://claude.ai/code).

Any project, any framework. Auto-detects your i18n structure and keeps translation files in sync.

## Features

- **Auto-detection** - Scans your project to find i18n files and identify the framework
- **Structure-aware** - Supports `locale_first`, `domain_first`, `flat_locale` patterns
- **Reference language auto-detection** - Most complete locale becomes the reference
- **Missing key detection** - Finds keys present in reference but missing in targets
- **Placeholder sync** - Adds `[TODO: translate]` markers for missing translations
- **Validation** - Checks JSON syntax, key consistency, empty values, TODO residue
- **No external dependencies** - Python standard library only (`pyyaml` optional for YAML)

## Supported Frameworks

| Framework | Detection | Default Directory |
|-----------|-----------|-------------------|
| next-intl | `package.json` | `messages/` |
| react-i18next | `package.json` | `public/locales/` |
| vue-i18n | `package.json` | `src/locales/` |
| Angular | `package.json` | `src/locale/` |
| Rails | `Gemfile` | `config/locales/` |
| Flutter | `pubspec.yaml` | `lib/l10n/` |
| react-intl / FormatJS | `package.json` | `src/translations/` |
| Generic | Directory scan | `locales/`, `i18n/`, `lang/` |

## Supported Structures

### `flat_locale` - One file per locale

```
locales/
  en.json
  ko.json
  ja.json
```

Used by: next-intl, simple projects

### `locale_first` - Locale directories with namespace files

```
locales/
  en/
    common.json
    auth.json
  ko/
    common.json
    auth.json
```

Used by: react-i18next, vue-i18n

### `domain_first` - Domain directories with locale files

```
messages/
  common/
    en.json
    ko.json
  auth/
    en.json
    ko.json
```

Used by: Custom setups, SvelteKit

## Installation

### Requirements

- Python 3.10+
- [Claude Code CLI](https://claude.ai/code)

### Install as Claude Code Skill

```bash
# Clone the repository
git clone <repository-url> /tmp/i18n-sync

# Create symlink
ln -s /tmp/i18n-sync ~/.claude/skills/i18n-sync
```

Or if you already have the skill in a local directory:

```bash
ln -s "$(pwd)/i18n-sync" ~/.claude/skills/i18n-sync
```

## Usage

### With Claude Code (Natural Language)

Simply ask Claude in natural language:

```
"Check my translation files"
"Sync missing translations"
"Validate i18n files"
"Check Japanese translations"
"Sync the auth namespace"
"i18n sync"
"Show missing translation keys"
```

Claude will automatically invoke the skill and present results.

### Standalone CLI Usage

The scripts can also be used independently outside of Claude Code.

#### Step 1: Detect Project Structure

```bash
python3 ~/.claude/skills/i18n-sync/scripts/detect_i18n.py . --pretty
```

Output:

```json
{
  "detected": true,
  "framework": "next-intl",
  "i18n_root": "messages",
  "structure_type": "flat_locale",
  "file_format": "json",
  "reference_locale": "ko",
  "target_locales": ["en", "ja"],
  "locales": [
    { "code": "ko", "total_keys": 245, "is_reference": true },
    { "code": "en", "total_keys": 230, "is_reference": false },
    { "code": "ja", "total_keys": 210, "is_reference": false }
  ],
  "summary": {
    "total_locales": 3,
    "total_reference_keys": 245,
    "max_missing_keys": 35,
    "needs_sync": true
  }
}
```

Save the output for subsequent commands:

```bash
python3 ~/.claude/skills/i18n-sync/scripts/detect_i18n.py . > /tmp/i18n_config.json
```

#### Step 2: Check Missing Keys

```bash
python3 ~/.claude/skills/i18n-sync/scripts/sync_i18n.py \
  --config /tmp/i18n_config.json \
  --check --pretty
```

Output:

```json
{
  "mode": "check",
  "reference_locale": "ko",
  "results": [
    {
      "namespace": "common",
      "locale": "en",
      "file": "locales/en/common.json",
      "missing_keys": ["button.delete", "errors.network"],
      "missing_count": 2,
      "extra_keys": [],
      "empty_keys": [],
      "todo_keys": []
    }
  ],
  "summary": {
    "total_files_checked": 4,
    "files_in_sync": 2,
    "files_needing_sync": 2,
    "total_missing_keys": 5
  }
}
```

#### Step 3: Sync (Add Placeholders)

Preview changes without writing:

```bash
python3 ~/.claude/skills/i18n-sync/scripts/sync_i18n.py \
  --config /tmp/i18n_config.json \
  --sync --dry-run --pretty
```

Apply changes:

```bash
python3 ~/.claude/skills/i18n-sync/scripts/sync_i18n.py \
  --config /tmp/i18n_config.json \
  --sync --pretty
```

Before sync:

```json
{
  "button": {
    "save": "Save",
    "cancel": "Cancel"
  }
}
```

After sync:

```json
{
  "button": {
    "save": "Save",
    "cancel": "Cancel",
    "delete": "[TODO: translate] uc0ad\uc81c"
  }
}
```

Existing translations are never overwritten. Only missing keys are added.

#### Step 4: Validate

```bash
python3 ~/.claude/skills/i18n-sync/scripts/sync_i18n.py \
  --config /tmp/i18n_config.json \
  --validate --pretty
```

Validates:
- JSON/YAML syntax
- Key consistency (all keys from reference exist)
- Empty string values
- TODO placeholder residue
- Structural consistency (nested object types match)

## CLI Reference

### detect_i18n.py

```
python3 detect_i18n.py [project_dir] [options]
```

| Option | Description |
|--------|-------------|
| `project_dir` | Project root directory (default: `.`) |
| `--path PATH` | Override i18n directory path (skip auto-detection) |
| `--ref LOCALE` | Force reference locale (e.g., `en`, `ko`) |
| `--format FORMAT` | Force file format: `json` or `yaml` |
| `--pretty` | Pretty-print JSON output |

**Exit codes:** `0` = detected, `1` = not detected

### sync_i18n.py

```
python3 sync_i18n.py --config <path> --check|--sync|--validate [options]
```

| Option | Description |
|--------|-------------|
| `--config PATH` | Detection config JSON file (required), use `-` for stdin |
| `--check` | Report missing keys only (read-only) |
| `--sync` | Add missing keys with placeholder values |
| `--validate` | Run full validation suite |
| `--locale CODE` | Process only this target locale |
| `--namespace NAME` | Process only this namespace/domain |
| `--placeholder TEXT` | Custom placeholder (default: `[TODO: translate]`) |
| `--dry-run` | Preview changes without writing (sync mode only) |
| `--pretty` | Pretty-print JSON output |

**Exit codes:**
- `--check`: `0` = all in sync, `1` = missing keys found
- `--sync`: `0` = always
- `--validate`: `0` = all valid, `1` = errors found

## Piping & Composition

Detect and check in one command:

```bash
python3 detect_i18n.py . | python3 sync_i18n.py --config - --check --pretty
```

Filter specific locale:

```bash
python3 sync_i18n.py --config /tmp/i18n_config.json --check --locale ja --pretty
```

Filter specific namespace:

```bash
python3 sync_i18n.py --config /tmp/i18n_config.json --sync --namespace auth --pretty
```

Custom placeholder text:

```bash
python3 sync_i18n.py --config /tmp/i18n_config.json --sync \
  --placeholder "[NEEDS TRANSLATION]" --pretty
```

## Manual Override

When auto-detection doesn't find your files, specify the path manually:

```bash
# Custom i18n directory
python3 detect_i18n.py . --path src/custom/translations --pretty

# Force reference locale to English
python3 detect_i18n.py . --ref en --pretty

# Force YAML format
python3 detect_i18n.py . --format yaml --pretty

# Combine options
python3 detect_i18n.py . --path config/locales --ref en --format yaml --pretty
```

## Auto-Detection Priority

The detection script searches these directories in order:

| Priority | Directory |
|----------|-----------|
| 1 | `src/lib/i18n/messages` |
| 2 | `public/locales` |
| 3 | `src/locales` |
| 4 | `src/locale` |
| 5 | `messages` |
| 6 | `locales` |
| 7 | `locale` |
| 8 | `i18n` |
| 9 | `lang` |
| 10 | `translations` |
| 11 | `config/locales` |
| 12 | `src/i18n` |
| 13+ | `src/messages`, `app/i18n`, `resources/lang`, ... |

The first directory that contains valid locale-coded files is selected.

## Reference Language Detection

The reference locale is automatically determined by key count:

1. Count leaf keys across all files for each locale
2. The locale with the most keys becomes the reference
3. If tied, prefer: `en` > `ko` > `ja` > `zh` > `fr` > `de` > `es` > `pt` > `it` > `ru`

Override with `--ref`:

```bash
python3 detect_i18n.py . --ref en
```

## Sync Logic

```
Reference locale (auto-detected)
    |
    +-- Key A --> target has A? --> Yes: keep existing translation
    |                           --> No:  add "[TODO: translate] {reference_value}"
    |
    +-- Key B --> target has B? --> Yes: keep existing translation
    |                           --> No:  add "[TODO: translate] {reference_value}"
    ...

  - Existing translations are never overwritten
  - New keys are inserted at the same position as in the reference file
  - Extra keys in target (not in reference) are preserved at the end
```

## Project Structure

```
i18n-sync/
  SKILL.md                        # Claude Code skill definition
  scripts/
    detect_i18n.py                # Project structure auto-detection
    sync_i18n.py                  # Sync, check, and validation
  references/
    framework-patterns.md         # Framework-specific pattern reference
```

## License

MIT
