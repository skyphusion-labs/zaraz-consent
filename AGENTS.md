# Zaraz Consent

This file is the guide for any coding agent and any contributor. Follow it.

## What this project is

Zaraz Consent is one WordPress must-use file. Copy `zaraz-consent.php` to `wp-content/mu-plugins/zaraz-consent.php`. Zaraz draws the consent modal. This file reopens that modal. PHP reads the `cf_consent` cookie when other code asks. Read [README.md](README.md).

The license is GPL-2.0-or-later, the same grant as WordPress.

## Limits

This file does not gate scripts. Cloudflare Zaraz gates Zaraz tools. WordPress, the theme, and other plugins can still load their own scripts. Read the README section on what Zaraz cannot gate.

Do not add an admin screen. Do not add an options row. Do not add banner assets. Do not enqueue a stylesheet or a script from this file.

`iac/sync_consent.py` writes zone consent config. It replaces the `consent` object on the live config. It sets `defaultPurpose` for ids listed in `iac/tool-purposes.json`. It must leave tools alone. The example map in that JSON file stays `{}`.

Leave `companyStreetAddress` empty until there is a real street address. Do not print `CLOUDFLARE_API_TOKEN`. Do not print the Zaraz debug key.

## Checks

CI is [`.github/workflows/ci.yml`](.github/workflows/ci.yml). The `ci` job lints the PHP files and compiles the Python files. The `coverage` job runs the contract:

```bash
bash tests/contract.sh
```

That script runs the cookie test, the sync test, and `tests/ste_lint.py` on `README.md`. Keep each README sentence at twenty words or fewer.

## Docs

Write Simplified Technical English. Use short sentences. Use one idea per sentence. Use the active present tense. Use plain words. Use the same word every time.

Do not use an em dash (U+2014). Do not use an en dash (U+2013). Use a comma, a semicolon, parentheses, or two hyphens (`--`).

State the limit next to the capability. Do not turn a measured result into a promise.

## Safety

Do not put a secret in a tracked file, a log, or an issue.
