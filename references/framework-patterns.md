# Framework i18n Patterns Reference

## next-intl (Next.js)

**Default dirs:** `messages/`, `src/messages/`
**Structure:** `flat_locale` or `locale_first`
```
messages/en.json          # flat_locale
messages/en/common.json   # locale_first
```
**Config:** `next.config.js` with `createNextIntlPlugin`, or `i18n.ts`
**Detection:** `next-intl` in package.json dependencies

## react-i18next / i18next

**Default dirs:** `public/locales/`, `locales/`
**Structure:** `locale_first`
```
public/locales/en/common.json
public/locales/en/auth.json
```
**Config:** `i18next.init()` in `i18n.js` or `i18n.ts`
**Detection:** `react-i18next` or `i18next` in package.json

## vue-i18n

**Default dirs:** `src/locales/`, `locales/`
**Structure:** `locale_first` or `flat_locale`
```
src/locales/en.json       # flat_locale
src/locales/en/index.json # locale_first
```
**Config:** `createI18n()` in main.ts/js
**Detection:** `vue-i18n` in package.json

## Angular (@angular/localize)

**Default dirs:** `src/locale/`, `src/locales/`
**Structure:** `flat_locale` (XLIFF or JSON)
```
src/locale/messages.en.xlf
src/locale/messages.ja.xlf
```
**Config:** `angular.json` i18n section
**Detection:** `@angular/localize` in package.json, `.xlf` files

## Rails (ruby-i18n)

**Default dirs:** `config/locales/`
**Structure:** `flat_locale` (YAML)
**Format:** YAML with locale as root key
```yaml
# config/locales/en.yml
en:
  activerecord:
    models:
      user: User
  views:
    home:
      title: Home
```
**Detection:** `Gemfile` with `rails-i18n` or `i18n` gem

## Laravel (PHP)

**Default dirs:** `resources/lang/`, `lang/`
**Structure:** `locale_first`
```
lang/en/messages.php
lang/en/validation.php
```
**Detection:** `composer.json` with `laravel/framework`

## Django / Flask

**Default dirs:** `locale/`, `translations/`
**Format:** `.po` / `.mo` (gettext)
```
locale/en/LC_MESSAGES/django.po
```
**Detection:** `requirements.txt` with `django` or `flask-babel`

## Flutter

**Default dirs:** `lib/l10n/`, `l10n/`
**Format:** ARB (Application Resource Bundle)
```
lib/l10n/app_en.arb
lib/l10n/app_ko.arb
```
**Detection:** `pubspec.yaml` with `flutter_localizations`

## react-intl / FormatJS

**Default dirs:** `src/translations/`, `lang/`, `locales/`
**Structure:** `flat_locale`
```
src/translations/en.json
```
**Detection:** `react-intl` or `@formatjs/intl` in package.json
**Note:** Uses ICU MessageFormat: `{count, plural, one {# item} other {# items}}`

## Generic JSON i18n

**Common dirs:** `locales/`, `i18n/`, `lang/`, `translations/`
**Structure:** Any of the 4 patterns
**Key styles:**
- Nested: `{"button": {"save": "Save"}}`
- Flat: `{"button.save": "Save"}`
