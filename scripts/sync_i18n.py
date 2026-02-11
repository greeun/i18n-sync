#!/usr/bin/env python3
"""
i18n translation file sync, check, and validation script.
Reads detection config from detect_i18n.py and performs key comparison,
sync with placeholders, and validation.
"""

import argparse
import json
import os
import re
import sys
from collections import OrderedDict
from pathlib import Path

DEFAULT_PLACEHOLDER = '[TODO: translate]'
TODO_PATTERN = re.compile(r'\[TODO[:\s].*?\]', re.IGNORECASE)


# --- Helpers ---

def extract_leaf_keys(obj: dict, prefix: str = '') -> OrderedDict:
    """Recursively extract all leaf key paths and values, preserving order."""
    keys = OrderedDict()
    if not isinstance(obj, dict):
        return keys
    for key, value in obj.items():
        full_key = f'{prefix}.{key}' if prefix else key
        if isinstance(value, dict):
            keys.update(extract_leaf_keys(value, full_key))
        else:
            keys[full_key] = value
    return keys


def set_nested_key(obj: dict, dotted_key: str, value) -> None:
    """Set a value in a nested dict using dot-notation key."""
    parts = dotted_key.split('.')
    current = obj
    for part in parts[:-1]:
        if part not in current or not isinstance(current[part], dict):
            current[part] = OrderedDict()
        current = current[part]
    current[parts[-1]] = value


def get_nested_value(obj: dict, dotted_key: str):
    """Get a value from a nested dict using dot-notation key."""
    parts = dotted_key.split('.')
    current = obj
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def load_json_ordered(filepath: str) -> OrderedDict | None:
    """Load JSON preserving key order."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f, object_pairs_hook=OrderedDict)
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return None


def load_yaml_file(filepath: str) -> dict | None:
    """Load YAML file."""
    try:
        import yaml
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except ImportError:
        return None
    except Exception:
        return None


def load_file(filepath: str, file_format: str) -> OrderedDict | None:
    """Load a translation file based on format."""
    if file_format == 'json':
        return load_json_ordered(filepath)
    elif file_format == 'yaml':
        data = load_yaml_file(filepath)
        if isinstance(data, dict):
            return OrderedDict(data)
    return None


def save_json(filepath: str, data: dict) -> None:
    """Save JSON with 2-space indent and trailing newline."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write('\n')


def save_yaml(filepath: str, data: dict) -> None:
    """Save YAML file."""
    try:
        import yaml
        with open(filepath, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    except ImportError:
        print(f'Warning: pyyaml not installed, cannot write YAML file: {filepath}', file=sys.stderr)


def save_file(filepath: str, data: dict, file_format: str) -> None:
    """Save a translation file based on format."""
    if file_format == 'json':
        save_json(filepath, data)
    elif file_format == 'yaml':
        save_yaml(filepath, data)


def merge_missing_keys(target: dict, reference: dict, missing_keys: list,
                       ref_leaf_keys: dict, placeholder: str) -> dict:
    """Insert missing keys into target dict, preserving existing keys.
    Attempts to insert new keys in the same position as the reference."""
    result = OrderedDict()

    def _merge_level(ref_obj, tgt_obj, prefix=''):
        merged = OrderedDict()
        if not isinstance(ref_obj, dict):
            return tgt_obj if tgt_obj is not None else ref_obj

        for key in ref_obj:
            full_key = f'{prefix}.{key}' if prefix else key
            ref_value = ref_obj[key]

            if isinstance(ref_value, dict):
                tgt_sub = tgt_obj.get(key, OrderedDict()) if isinstance(tgt_obj, dict) else OrderedDict()
                if not isinstance(tgt_sub, dict):
                    tgt_sub = OrderedDict()
                merged[key] = _merge_level(ref_value, tgt_sub, full_key)
            else:
                if isinstance(tgt_obj, dict) and key in tgt_obj:
                    merged[key] = tgt_obj[key]
                elif full_key in missing_keys:
                    ref_val = ref_leaf_keys.get(full_key, '')
                    merged[key] = f'{placeholder} {ref_val}' if ref_val else placeholder
                else:
                    if isinstance(tgt_obj, dict) and key in tgt_obj:
                        merged[key] = tgt_obj[key]

        # Keep any extra keys from target that aren't in reference
        if isinstance(tgt_obj, dict):
            for key in tgt_obj:
                if key not in merged:
                    merged[key] = tgt_obj[key]

        return merged

    target = target if target else OrderedDict()
    return _merge_level(reference, target)


# --- File Resolution ---

def resolve_file_pairs(config: dict) -> list:
    """Resolve reference/target file pairs from config.
    Returns list of dicts: {namespace, ref_file, target_locale, target_file}
    """
    pairs = []
    project_dir = config['project_dir']
    structure = config['structure_type']
    file_format = config['file_format']
    ref_locale = config['reference_locale']
    target_locales = config['target_locales']
    i18n_root = os.path.join(project_dir, config['i18n_root'])

    ext = '.json' if file_format == 'json' else '.yml'

    if structure == 'flat_locale':
        ref_file = os.path.join(i18n_root, f'{ref_locale}{ext}')
        for tgt in target_locales:
            tgt_file = os.path.join(i18n_root, f'{tgt}{ext}')
            pairs.append({
                'namespace': None,
                'ref_file': ref_file,
                'target_locale': tgt,
                'target_file': tgt_file,
            })

    elif structure == 'locale_first':
        namespaces = config.get('namespaces') or []
        if not namespaces:
            # Discover namespaces from reference locale dir
            ref_dir = os.path.join(i18n_root, ref_locale)
            if os.path.isdir(ref_dir):
                namespaces = [Path(f).stem for f in sorted(os.listdir(ref_dir))
                              if Path(f).suffix.lower() in {'.json', '.yml', '.yaml'}]

        for ns in namespaces:
            ref_file = os.path.join(i18n_root, ref_locale, f'{ns}{ext}')
            for tgt in target_locales:
                tgt_file = os.path.join(i18n_root, tgt, f'{ns}{ext}')
                pairs.append({
                    'namespace': ns,
                    'ref_file': ref_file,
                    'target_locale': tgt,
                    'target_file': tgt_file,
                })

    elif structure == 'domain_first':
        namespaces = config.get('namespaces') or []
        if not namespaces:
            # Discover domains
            namespaces = [d for d in sorted(os.listdir(i18n_root))
                          if os.path.isdir(os.path.join(i18n_root, d))]

        for ns in namespaces:
            ref_file = os.path.join(i18n_root, ns, f'{ref_locale}{ext}')
            for tgt in target_locales:
                tgt_file = os.path.join(i18n_root, ns, f'{tgt}{ext}')
                pairs.append({
                    'namespace': ns,
                    'ref_file': ref_file,
                    'target_locale': tgt,
                    'target_file': tgt_file,
                })

    else:  # single_namespace or fallback
        ref_file = os.path.join(i18n_root, f'{ref_locale}{ext}')
        for tgt in target_locales:
            tgt_file = os.path.join(i18n_root, f'{tgt}{ext}')
            pairs.append({
                'namespace': None,
                'ref_file': ref_file,
                'target_locale': tgt,
                'target_file': tgt_file,
            })

    return pairs


# --- Check Mode ---

def run_check(config: dict, locale_filter: str | None = None,
              namespace_filter: str | None = None) -> dict:
    """Check mode: report missing/extra/empty/todo keys without modification."""
    pairs = resolve_file_pairs(config)
    results = []
    file_format = config['file_format']

    for pair in pairs:
        if locale_filter and pair['target_locale'] != locale_filter:
            continue
        if namespace_filter and pair['namespace'] != namespace_filter:
            continue

        ref_data = load_file(pair['ref_file'], file_format)
        if not ref_data:
            continue

        ref_keys = extract_leaf_keys(ref_data)
        ref_key_set = set(ref_keys.keys())

        tgt_data = load_file(pair['target_file'], file_format)
        tgt_keys = extract_leaf_keys(tgt_data) if tgt_data else OrderedDict()
        tgt_key_set = set(tgt_keys.keys())

        missing = sorted(ref_key_set - tgt_key_set)
        extra = sorted(tgt_key_set - ref_key_set)
        empty = sorted(k for k, v in tgt_keys.items() if v == '' or v is None)
        todo = sorted(k for k, v in tgt_keys.items()
                      if isinstance(v, str) and TODO_PATTERN.search(v))

        rel_file = os.path.relpath(pair['target_file'], config['project_dir'])
        results.append({
            'namespace': pair['namespace'],
            'locale': pair['target_locale'],
            'file': rel_file,
            'file_exists': tgt_data is not None,
            'total_reference_keys': len(ref_keys),
            'total_target_keys': len(tgt_keys),
            'missing_keys': missing,
            'missing_count': len(missing),
            'extra_keys': extra,
            'extra_count': len(extra),
            'empty_keys': empty,
            'empty_count': len(empty),
            'todo_keys': todo,
            'todo_count': len(todo),
        })

    total_missing = sum(r['missing_count'] for r in results)
    total_extra = sum(r['extra_count'] for r in results)
    total_empty = sum(r['empty_count'] for r in results)
    total_todo = sum(r['todo_count'] for r in results)
    files_in_sync = sum(1 for r in results if r['missing_count'] == 0)

    return {
        'mode': 'check',
        'reference_locale': config['reference_locale'],
        'results': results,
        'summary': {
            'total_files_checked': len(results),
            'files_in_sync': files_in_sync,
            'files_needing_sync': len(results) - files_in_sync,
            'total_missing_keys': total_missing,
            'total_extra_keys': total_extra,
            'total_empty_keys': total_empty,
            'total_todo_keys': total_todo,
        },
    }


# --- Sync Mode ---

def run_sync(config: dict, placeholder: str = DEFAULT_PLACEHOLDER,
             locale_filter: str | None = None, namespace_filter: str | None = None,
             dry_run: bool = False) -> dict:
    """Sync mode: add missing keys with placeholder values."""
    pairs = resolve_file_pairs(config)
    results = []
    file_format = config['file_format']

    for pair in pairs:
        if locale_filter and pair['target_locale'] != locale_filter:
            continue
        if namespace_filter and pair['namespace'] != namespace_filter:
            continue

        ref_data = load_file(pair['ref_file'], file_format)
        if not ref_data:
            continue

        ref_keys = extract_leaf_keys(ref_data)
        ref_key_set = set(ref_keys.keys())

        tgt_data = load_file(pair['target_file'], file_format)
        tgt_keys = extract_leaf_keys(tgt_data) if tgt_data else OrderedDict()
        tgt_key_set = set(tgt_keys.keys())

        missing = sorted(ref_key_set - tgt_key_set)

        rel_file = os.path.relpath(pair['target_file'], config['project_dir'])

        if not missing:
            results.append({
                'namespace': pair['namespace'],
                'locale': pair['target_locale'],
                'file': rel_file,
                'keys_added': [],
                'keys_added_count': 0,
                'already_synced': True,
            })
            continue

        # Merge missing keys
        if tgt_data is None:
            tgt_data = OrderedDict()
            # Ensure target directory exists
            tgt_dir = os.path.dirname(pair['target_file'])
            if not dry_run:
                os.makedirs(tgt_dir, exist_ok=True)

        merged = merge_missing_keys(tgt_data, ref_data, missing, ref_keys, placeholder)

        if not dry_run:
            save_file(pair['target_file'], merged, file_format)

        results.append({
            'namespace': pair['namespace'],
            'locale': pair['target_locale'],
            'file': rel_file,
            'keys_added': missing,
            'keys_added_count': len(missing),
            'already_synced': False,
        })

    total_added = sum(r['keys_added_count'] for r in results)
    files_modified = sum(1 for r in results if not r['already_synced'])

    return {
        'mode': 'sync' if not dry_run else 'dry_run',
        'reference_locale': config['reference_locale'],
        'placeholder': placeholder,
        'results': results,
        'summary': {
            'total_keys_added': total_added,
            'files_modified': files_modified,
            'files_already_synced': len(results) - files_modified,
        },
    }


# --- Validate Mode ---

def run_validate(config: dict, locale_filter: str | None = None,
                 namespace_filter: str | None = None) -> dict:
    """Validate mode: comprehensive validation of translation files."""
    pairs = resolve_file_pairs(config)
    results = []
    file_format = config['file_format']
    project_dir = config['project_dir']

    # Also validate reference files for JSON syntax
    ref_files_checked = set()

    for pair in pairs:
        if locale_filter and pair['target_locale'] != locale_filter:
            continue
        if namespace_filter and pair['namespace'] != namespace_filter:
            continue

        errors = []
        warnings = []

        # Validate reference file (once per unique ref file)
        if pair['ref_file'] not in ref_files_checked:
            ref_files_checked.add(pair['ref_file'])
            ref_data = load_file(pair['ref_file'], file_format)
            if ref_data is None:
                rel_ref = os.path.relpath(pair['ref_file'], project_dir)
                errors.append({
                    'type': 'parse_error',
                    'file': rel_ref,
                    'message': f'Cannot parse reference file: {rel_ref}',
                })

        ref_data = load_file(pair['ref_file'], file_format)
        if not ref_data:
            continue

        ref_keys = extract_leaf_keys(ref_data)
        ref_key_set = set(ref_keys.keys())

        # Validate target file
        rel_file = os.path.relpath(pair['target_file'], project_dir)

        if not os.path.isfile(pair['target_file']):
            errors.append({
                'type': 'missing_file',
                'file': rel_file,
                'message': f'Translation file does not exist: {rel_file}',
            })
            results.append({
                'namespace': pair['namespace'],
                'locale': pair['target_locale'],
                'file': rel_file,
                'errors': errors,
                'warnings': warnings,
                'valid': False,
            })
            continue

        tgt_data = load_file(pair['target_file'], file_format)
        if tgt_data is None:
            errors.append({
                'type': 'parse_error',
                'file': rel_file,
                'message': f'Cannot parse translation file: {rel_file}',
            })
            results.append({
                'namespace': pair['namespace'],
                'locale': pair['target_locale'],
                'file': rel_file,
                'errors': errors,
                'warnings': warnings,
                'valid': False,
            })
            continue

        tgt_keys = extract_leaf_keys(tgt_data)
        tgt_key_set = set(tgt_keys.keys())

        # Check missing keys
        missing = ref_key_set - tgt_key_set
        if missing:
            errors.append({
                'type': 'missing_keys',
                'file': rel_file,
                'count': len(missing),
                'keys': sorted(missing)[:10],  # Show first 10
                'message': f'{len(missing)} keys missing from reference',
            })

        # Check extra keys
        extra = tgt_key_set - ref_key_set
        if extra:
            warnings.append({
                'type': 'extra_keys',
                'file': rel_file,
                'count': len(extra),
                'keys': sorted(extra)[:10],
                'message': f'{len(extra)} keys not in reference (may be intentional)',
            })

        # Check empty values
        empty = [k for k, v in tgt_keys.items() if v == '' or v is None]
        if empty:
            warnings.append({
                'type': 'empty_values',
                'file': rel_file,
                'count': len(empty),
                'keys': sorted(empty)[:10],
                'message': f'{len(empty)} keys have empty values',
            })

        # Check TODO placeholders
        todo = [k for k, v in tgt_keys.items()
                if isinstance(v, str) and TODO_PATTERN.search(v)]
        if todo:
            warnings.append({
                'type': 'todo_placeholders',
                'file': rel_file,
                'count': len(todo),
                'keys': sorted(todo)[:10],
                'message': f'{len(todo)} keys still have TODO placeholders',
            })

        # Check structural consistency
        def check_structure(ref_obj, tgt_obj, path=''):
            issues = []
            if not isinstance(ref_obj, dict) or not isinstance(tgt_obj, dict):
                return issues
            for key in ref_obj:
                if key not in tgt_obj:
                    continue
                full_path = f'{path}.{key}' if path else key
                ref_is_dict = isinstance(ref_obj[key], dict)
                tgt_is_dict = isinstance(tgt_obj[key], dict)
                if ref_is_dict != tgt_is_dict:
                    issues.append({
                        'type': 'structure_mismatch',
                        'file': rel_file,
                        'key': full_path,
                        'message': f'Type mismatch at "{full_path}": '
                                   f'reference has {"object" if ref_is_dict else "value"}, '
                                   f'target has {"object" if tgt_is_dict else "value"}',
                    })
                elif ref_is_dict:
                    issues.extend(check_structure(ref_obj[key], tgt_obj[key], full_path))
            return issues

        struct_issues = check_structure(ref_data, tgt_data)
        errors.extend(struct_issues)

        results.append({
            'namespace': pair['namespace'],
            'locale': pair['target_locale'],
            'file': rel_file,
            'errors': errors,
            'warnings': warnings,
            'valid': len(errors) == 0,
        })

    total_errors = sum(len(r['errors']) for r in results)
    total_warnings = sum(len(r['warnings']) for r in results)
    all_valid = all(r['valid'] for r in results) if results else True

    return {
        'mode': 'validate',
        'reference_locale': config['reference_locale'],
        'results': results,
        'summary': {
            'total_files_validated': len(results),
            'files_valid': sum(1 for r in results if r['valid']),
            'files_with_errors': sum(1 for r in results if not r['valid']),
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'all_valid': all_valid,
        },
    }


# --- Main ---

def load_config(config_arg: str) -> dict:
    """Load config from file path or stdin."""
    if config_arg == '-':
        return json.load(sys.stdin)
    with open(config_arg, 'r', encoding='utf-8') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description='i18n translation file sync and validation')
    parser.add_argument('--config', required=True,
                        help='Detection config JSON file path, or "-" for stdin')

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--check', action='store_true',
                            help='Report missing keys only (read-only)')
    mode_group.add_argument('--sync', action='store_true',
                            help='Add missing keys with placeholders')
    mode_group.add_argument('--validate', action='store_true',
                            help='Run full validation suite')

    parser.add_argument('--locale', default=None,
                        help='Process only this target locale')
    parser.add_argument('--namespace', default=None,
                        help='Process only this namespace/domain')
    parser.add_argument('--placeholder', default=DEFAULT_PLACEHOLDER,
                        help=f'Custom placeholder text (default: "{DEFAULT_PLACEHOLDER}")')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would change without writing (sync mode)')
    parser.add_argument('--pretty', action='store_true',
                        help='Pretty-print JSON output')

    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps({'error': f'Cannot load config: {e}'}), file=sys.stderr)
        sys.exit(1)

    if not config.get('detected'):
        print(json.dumps({'error': 'Config indicates detection failed', 'config': config}),
              file=sys.stderr)
        sys.exit(1)

    if args.check:
        result = run_check(config, args.locale, args.namespace)
    elif args.sync:
        result = run_sync(config, args.placeholder, args.locale, args.namespace, args.dry_run)
    elif args.validate:
        result = run_validate(config, args.locale, args.namespace)
    else:
        print(json.dumps({'error': 'No mode specified'}), file=sys.stderr)
        sys.exit(1)

    indent = 2 if args.pretty else None
    json.dump(result, sys.stdout, indent=indent, ensure_ascii=False)
    if args.pretty:
        print()

    # Exit code: 0 if clean, 1 if issues found
    if args.check:
        sys.exit(0 if result['summary']['total_missing_keys'] == 0 else 1)
    elif args.sync:
        sys.exit(0)
    elif args.validate:
        sys.exit(0 if result['summary']['all_valid'] else 1)


if __name__ == '__main__':
    main()
