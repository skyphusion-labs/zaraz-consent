#!/bin/bash
# The drop-in stays one file and does not grow a front-end request.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
fail() { echo "FAIL: $*" >&2; exit 1; }

php -l "$root/zaraz-consent.php" >/dev/null
php "$root/tests/cookie-test.php" | grep -q 'cookie_ok' || fail "cookie reader"
python3 "$root/tests/test_sync.py" >/dev/null

grep -q "add_action('wp_footer'" "$root/zaraz-consent.php" || fail "footer hook"
grep -q 'cf_consent' "$root/zaraz-consent.php" || fail "cookie name"
grep -q 'zaraz.consent.modal = true' "$root/zaraz-consent.php" || fail "reopen modal"
if grep -q 'wp_enqueue' "$root/zaraz-consent.php"; then
  fail "a stylesheet or script request"
fi
if grep -q 'https\?://' "$root/zaraz-consent.php"; then
  fail "the drop-in must not reference a remote URL"
fi
# SIMPLIFIED TECHNICAL ENGLISH, measured rather than remembered. This repo is
# public, and every public project in this estate holds its docs to STE: one
# idea per sentence, twenty words or fewer. The self-test runs FIRST, because a
# linter nobody has watched fail reports a clean file for the same reason a
# broken one does.
python3 "$root/tests/ste_lint.py" --self-test >/dev/null || fail "ste_lint self-test"
python3 "$root/tests/ste_lint.py" "$root/README.md" || fail "README prose over 20 words per sentence"

grep -q 'mu-plugins/zaraz-consent.php' "$root/README.md" || fail "install path"
grep -q 'does not list a purpose' "$root/README.md" || fail "empty purpose note"
grep -q 'does not create tools' "$root/iac/sync_consent.py" || fail "sync creates nothing"
python3 -c 'import json; c=json.load(open("'"$root"'/iac/consent.json")); assert c["companyStreetAddress"]==""; assert c["cookieName"]=="cf_consent"'
python3 -c 'import json; assert json.load(open("'"$root"'/iac/tool-purposes.json"))=={}'
echo "contract_ok"
