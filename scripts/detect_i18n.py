#!/usr/bin/env python3
"""
i18n project structure auto-detection script.
Scans a project directory to detect i18n framework, directory layout,
file format, locales, and reference language.
Outputs a JSON manifest for use by sync_i18n.py.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# --- Constants ---

LOCALE_PATTERN = re.compile(r'^[a-z]{2,3}(?:[-_][A-Za-z]{2,4})?$')

KNOWN_LOCALE_CODES = {
    'af', 'am', 'ar', 'az', 'be', 'bg', 'bn', 'bs', 'ca', 'cs', 'cy', 'da',
    'de', 'el', 'en', 'es', 'et', 'eu', 'fa', 'fi', 'fil', 'fr', 'ga', 'gl',
    'gu', 'he', 'hi', 'hr', 'hu', 'hy', 'id', 'is', 'it', 'ja', 'jv', 'ka',
    'kk', 'km', 'kn', 'ko', 'ky', 'lo', 'lt', 'lv', 'mk', 'ml', 'mn', 'mr',
    'ms', 'my', 'nb', 'ne', 'nl', 'nn', 'no', 'pa', 'pl', 'pt', 'ro', 'ru',
    'si', 'sk', 'sl', 'sq', 'sr', 'sv', 'sw', 'ta', 'te', 'th', 'tr', 'uk',
    'ur', 'uz', 'vi', 'zh', 'zu',
}

CANDIDATE_DIRS = [
    'src/lib/i18n/messages',
    'public/locales',
    'src/locales',
    'src/locale',
    'messages',
    'locales',
    'locale',
    'i18n',
    'lang',
    'translations',
    'config/locales',
    'src/i18n',
    'src/messages',
    'app/i18n',
    'resources/lang',
    'src/translations',
    'assets/i18n',
    'assets/locales',
]

I18N_FILE_EXTENSIONS = {'.json', '.yml', '.yaml'}

FRAMEWORK_INDICATORS = {
    'next-intl': 'next-intl',
    'next-i18next': 'next-i18next',
    'react-i18next': 'react-i18next',
    'i18next': 'i18next',
    'vue-i18n': 'vue-i18n',
    '@angular/localize': 'angular',
    'react-intl': 'react-intl',
    '@formatjs/intl': 'formatjs',
    'typesafe-i18n': 'typesafe-i18n',
    '@lingui/core': 'lingui',
    'svelte-i18n': 'svelte-i18n',
}

REFERENCE_LOCALE_PRIORITY = ['en', 'ko', 'ja', 'zh', 'fr', 'de', 'es', 'pt', 'it', 'ru']


# --- Helpers ---

def is_locale_code(name: str) -> bool:
    """Check if a name looks like a locale code."""
    base = name.split('.')[0]  # strip extension
    if not LOCALE_PATTERN.match(base):
        return False
    # Normalize: en-US -> en, zh_CN -> zh
    lang = base.split('-')[0].split('_')[0].lower()
    return lang in KNOWN_LOCALE_CODES


def count_leaf_keys(obj, prefix='') -> dict:
    """Recursively extract all leaf key paths and their values from a nested dict."""
    keys = {}
    if not isinstance(obj, dict):
        return keys
    for key, value in obj.items():
        full_key = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict):
            keys.update(count_leaf_keys(value, full_key))
        else:
            keys[full_key] = value
    return keys


def load_json(filepath: str) -> dict | None:
    """Load a JSON file, return None on failure."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        pass
    return None


def load_yaml(filepath: str) -> dict | None:
    """Load a YAML file, return None on failure or if pyyaml not installed."""
    try:
        import yaml
        with open(filepath, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        if isinstance(data, dict):
            return data
    except ImportError:
        # Fallback: simple key-value YAML parser
        return _parse_simple_yaml(filepath)
    except Exception:
        pass
    return None


def _parse_simple_yaml(filepath: str) -> dict | None:
    """Very basic YAML parser for flat key-value structures."""
    try:
        result = {}
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if ':' in line:
                    key, _, value = line.partition(':')
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and value:
                        result[key] = value
        return result if result else None
    except Exception:
        return None


def load_translation_file(filepath: str) -> dict | None:
    """Load a translation file based on extension."""
    ext = Path(filepath).suffix.lower()
    if ext == '.json':
        return load_json(filepath)
    elif ext in ('.yml', '.yaml'):
        return load_yaml(filepath)
    return None


def looks_like_translation_file(filepath: str) -> bool:
    """Check if a file looks like a translation file (has string leaf values)."""
    data = load_translation_file(filepath)
    if not data:
        return False
    keys = count_leaf_keys(data)
    if not keys:
        return False
    # At least 50% of leaf values should be strings
    string_count = sum(1 for v in keys.values() if isinstance(v, str))
    return string_count / len(keys) >= 0.5


# --- Framework Detection ---

def detect_framework(project_dir: str) -> str | None:
    """Detect i18n framework from project dependency files."""
    pkg_path = os.path.join(project_dir, 'package.json')
    if os.path.isfile(pkg_path):
        pkg = load_json(pkg_path)
        if pkg:
            all_deps = {}
            for dep_key in ('dependencies', 'devDependencies', 'peerDependencies'):
                all_deps.update(pkg.get(dep_key, {}))
            for pkg_name, framework_name in FRAMEWORK_INDICATORS.items():
                if pkg_name in all_deps:
                    return framework_name

    # Check Gemfile for Rails
    gemfile_path = os.path.join(project_dir, 'Gemfile')
    if os.path.isfile(gemfile_path):
        try:
            with open(gemfile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'rails-i18n' in content or ("gem 'i18n'" in content or 'gem "i18n"' in content):
                return 'rails'
        except OSError:
            pass

    # Check pubspec.yaml for Flutter
    pubspec_path = os.path.join(project_dir, 'pubspec.yaml')
    if os.path.isfile(pubspec_path):
        try:
            with open(pubspec_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'flutter_localizations' in content:
                return 'flutter'
        except OSError:
            pass

    return None


# --- Directory Detection ---

def find_i18n_directory(project_dir: str, override_path: str | None = None) -> str | None:
    """Find the i18n directory in the project."""
    if override_path:
        full_path = os.path.join(project_dir, override_path) if not os.path.isabs(override_path) else override_path
        if os.path.isdir(full_path):
            return full_path
        return None

    for candidate in CANDIDATE_DIRS:
        full_path = os.path.join(project_dir, candidate)
        if os.path.isdir(full_path):
            # Verify it contains translation-related files
            entries = os.listdir(full_path)
            has_translation_content = False
            for entry in entries:
                entry_path = os.path.join(full_path, entry)
                if os.path.isfile(entry_path):
                    ext = Path(entry).suffix.lower()
                    if ext in I18N_FILE_EXTENSIONS and is_locale_code(Path(entry).stem):
                        has_translation_content = True
                        break
                elif os.path.isdir(entry_path):
                    # Check if subdir name is a locale or contains locale files
                    if is_locale_code(entry):
                        has_translation_content = True
                        break
                    # Check if subdir contains locale-named files
                    sub_entries = os.listdir(entry_path)
                    for sub in sub_entries:
                        if Path(sub).suffix.lower() in I18N_FILE_EXTENSIONS and is_locale_code(Path(sub).stem):
                            has_translation_content = True
                            break
                if has_translation_content:
                    break
            if has_translation_content:
                return full_path
    return None


# --- Structure Classification ---

def classify_structure(i18n_dir: str, force_format: str | None = None) -> dict:
    """Classify the i18n directory structure and inventory all locales."""
    entries = sorted(os.listdir(i18n_dir))
    dirs = [e for e in entries if os.path.isdir(os.path.join(i18n_dir, e))]
    files = [e for e in entries if os.path.isfile(os.path.join(i18n_dir, e))
             and Path(e).suffix.lower() in I18N_FILE_EXTENSIONS]

    # Determine file format
    if force_format:
        file_format = force_format
    else:
        formats = set()
        for f in files:
            ext = Path(f).suffix.lower()
            if ext == '.json':
                formats.add('json')
            elif ext in ('.yml', '.yaml'):
                formats.add('yaml')
        if not formats and dirs:
            # Check files inside first subdir
            for d in dirs:
                sub_path = os.path.join(i18n_dir, d)
                for sf in os.listdir(sub_path):
                    ext = Path(sf).suffix.lower()
                    if ext == '.json':
                        formats.add('json')
                    elif ext in ('.yml', '.yaml'):
                        formats.add('yaml')
                if formats:
                    break
        file_format = 'json' if 'json' in formats else ('yaml' if 'yaml' in formats else 'json')

    valid_ext = {'.json'} if file_format == 'json' else {'.yml', '.yaml'}

    # Case 1: Flat files at root level (flat_locale or single_namespace)
    locale_files = [f for f in files if Path(f).suffix.lower() in valid_ext and is_locale_code(Path(f).stem)]
    if locale_files and not dirs:
        return _build_flat_locale(i18n_dir, locale_files, file_format)

    # Case 2: Subdirectories named as locale codes (locale_first)
    locale_dirs = [d for d in dirs if is_locale_code(d)]
    if locale_dirs and len(locale_dirs) >= 2:
        return _build_locale_first(i18n_dir, locale_dirs, file_format, valid_ext)

    # Case 3: Subdirectories NOT named as locale codes (domain_first)
    non_locale_dirs = [d for d in dirs if not is_locale_code(d)]
    if non_locale_dirs:
        return _build_domain_first(i18n_dir, non_locale_dirs, file_format, valid_ext)

    # Case 4: Mixed - locale files at root + subdirs, treat as flat_locale
    if locale_files:
        return _build_flat_locale(i18n_dir, locale_files, file_format)

    return {
        'structure_type': 'unknown',
        'file_format': file_format,
        'locales': [],
        'namespaces': None,
    }


def _build_flat_locale(i18n_dir: str, locale_files: list, file_format: str) -> dict:
    """Build inventory for flat_locale structure: {locale}.json at root."""
    locales = []
    for f in sorted(locale_files):
        code = Path(f).stem
        filepath = os.path.join(i18n_dir, f)
        data = load_translation_file(filepath)
        key_count = len(count_leaf_keys(data)) if data else 0
        # Check if it has nested namespaces (top-level keys are dicts)
        has_namespaces = data and any(isinstance(v, dict) for v in data.values())
        namespaces = sorted(k for k, v in data.items() if isinstance(v, dict)) if has_namespaces else None
        locales.append({
            'code': code,
            'files': [os.path.relpath(filepath, os.path.dirname(i18n_dir))],
            'total_keys': key_count,
        })

    # Detect namespaces from first locale file
    first_file = os.path.join(i18n_dir, locale_files[0])
    data = load_translation_file(first_file)
    namespaces = None
    if data:
        ns = sorted(k for k, v in data.items() if isinstance(v, dict))
        if ns:
            namespaces = ns

    return {
        'structure_type': 'flat_locale',
        'file_format': file_format,
        'locales': locales,
        'namespaces': namespaces,
    }


def _build_locale_first(i18n_dir: str, locale_dirs: list, file_format: str, valid_ext: set) -> dict:
    """Build inventory for locale_first structure: {locale}/{namespace}.json."""
    locales = []
    all_namespaces = set()

    for locale_dir_name in sorted(locale_dirs):
        locale_path = os.path.join(i18n_dir, locale_dir_name)
        ns_files = [f for f in sorted(os.listdir(locale_path))
                     if os.path.isfile(os.path.join(locale_path, f))
                     and Path(f).suffix.lower() in valid_ext]

        total_keys = 0
        file_paths = []
        for f in ns_files:
            filepath = os.path.join(locale_path, f)
            data = load_translation_file(filepath)
            if data:
                total_keys += len(count_leaf_keys(data))
                all_namespaces.add(Path(f).stem)
            file_paths.append(os.path.relpath(filepath, os.path.dirname(i18n_dir)))

        locales.append({
            'code': locale_dir_name,
            'files': file_paths,
            'total_keys': total_keys,
        })

    return {
        'structure_type': 'locale_first',
        'file_format': file_format,
        'locales': locales,
        'namespaces': sorted(all_namespaces) if all_namespaces else None,
    }


def _build_domain_first(i18n_dir: str, domain_dirs: list, file_format: str, valid_ext: set) -> dict:
    """Build inventory for domain_first structure: {domain}/{locale}.json."""
    locale_map = {}  # code -> {files: [], total_keys: 0}
    namespaces = []

    for domain_name in sorted(domain_dirs):
        domain_path = os.path.join(i18n_dir, domain_name)
        locale_files = [f for f in sorted(os.listdir(domain_path))
                        if os.path.isfile(os.path.join(domain_path, f))
                        and Path(f).suffix.lower() in valid_ext
                        and is_locale_code(Path(f).stem)]

        if not locale_files:
            continue
        namespaces.append(domain_name)

        for f in locale_files:
            code = Path(f).stem
            filepath = os.path.join(domain_path, f)
            data = load_translation_file(filepath)
            key_count = len(count_leaf_keys(data)) if data else 0

            if code not in locale_map:
                locale_map[code] = {'files': [], 'total_keys': 0}
            locale_map[code]['files'].append(os.path.relpath(filepath, os.path.dirname(i18n_dir)))
            locale_map[code]['total_keys'] += key_count

    locales = [
        {'code': code, 'files': info['files'], 'total_keys': info['total_keys']}
        for code, info in sorted(locale_map.items())
    ]

    return {
        'structure_type': 'domain_first',
        'file_format': file_format,
        'locales': locales,
        'namespaces': namespaces if namespaces else None,
    }


# --- Reference Locale Detection ---

def detect_reference_locale(locales: list, forced_ref: str | None = None) -> str | None:
    """Determine the reference locale (most keys, with priority tiebreaker)."""
    if forced_ref:
        return forced_ref

    if not locales:
        return None

    max_keys = max(l['total_keys'] for l in locales)
    candidates = [l['code'] for l in locales if l['total_keys'] == max_keys]

    if len(candidates) == 1:
        return candidates[0]

    # Tiebreaker: use priority list
    for pref in REFERENCE_LOCALE_PRIORITY:
        if pref in candidates:
            return pref

    return candidates[0]


# --- Main ---

def detect(project_dir: str, override_path: str | None = None,
           force_ref: str | None = None, force_format: str | None = None) -> dict:
    """Run full detection and return result dict."""
    project_dir = os.path.abspath(project_dir)

    # Step 1: Framework detection
    framework = detect_framework(project_dir)

    # Step 2: Find i18n directory
    i18n_dir = find_i18n_directory(project_dir, override_path)
    if not i18n_dir:
        return {
            'detected': False,
            'project_dir': project_dir,
            'framework': framework,
            'error': 'No i18n directory found',
            'candidates_checked': [os.path.join(project_dir, c) for c in CANDIDATE_DIRS],
            'suggestions': [
                'Create a locales/ directory with {locale}.json files',
                'Use --path to specify the i18n directory path manually',
            ],
        }

    i18n_root = os.path.relpath(i18n_dir, project_dir)

    # Step 3: Classify structure
    result = classify_structure(i18n_dir, force_format)
    if result['structure_type'] == 'unknown' or not result['locales']:
        return {
            'detected': False,
            'project_dir': project_dir,
            'framework': framework,
            'i18n_root': i18n_root,
            'error': 'Could not classify i18n structure',
            'suggestions': [
                'Ensure translation files use locale codes as filenames (e.g., en.json, ko.json)',
                'Use --path to specify the correct i18n directory',
            ],
        }

    # Step 4: Detect reference locale
    ref_locale = detect_reference_locale(result['locales'], force_ref)
    target_locales = [l['code'] for l in result['locales'] if l['code'] != ref_locale]

    # Mark reference in locales
    for l in result['locales']:
        l['is_reference'] = l['code'] == ref_locale

    # Step 5: Build summary
    ref_keys = next((l['total_keys'] for l in result['locales'] if l['code'] == ref_locale), 0)
    max_missing = max(
        (ref_keys - l['total_keys'] for l in result['locales'] if l['code'] != ref_locale),
        default=0
    )

    return {
        'detected': True,
        'project_dir': project_dir,
        'framework': framework,
        'i18n_root': i18n_root,
        'i18n_root_absolute': os.path.abspath(i18n_dir),
        'structure_type': result['structure_type'],
        'file_format': result['file_format'],
        'locales': result['locales'],
        'reference_locale': ref_locale,
        'target_locales': target_locales,
        'namespaces': result['namespaces'],
        'summary': {
            'total_locales': len(result['locales']),
            'total_namespaces': len(result['namespaces']) if result['namespaces'] else 0,
            'total_reference_keys': ref_keys,
            'max_missing_keys': max(max_missing, 0),
            'needs_sync': max_missing > 0,
        },
    }


def main():
    parser = argparse.ArgumentParser(description='Detect i18n project structure')
    parser.add_argument('project_dir', nargs='?', default='.',
                        help='Project root directory (default: current directory)')
    parser.add_argument('--path', dest='override_path', default=None,
                        help='Override i18n directory path (skip auto-detection)')
    parser.add_argument('--ref', dest='force_ref', default=None,
                        help='Force reference locale (e.g., en, ko)')
    parser.add_argument('--format', dest='force_format', default=None,
                        choices=['json', 'yaml'],
                        help='Force file format')
    parser.add_argument('--pretty', action='store_true',
                        help='Pretty-print JSON output')

    args = parser.parse_args()
    result = detect(args.project_dir, args.override_path, args.force_ref, args.force_format)

    indent = 2 if args.pretty else None
    json.dump(result, sys.stdout, indent=indent, ensure_ascii=False)
    if args.pretty:
        print()
    sys.exit(0 if result.get('detected') else 1)


if __name__ == '__main__':
    main()
