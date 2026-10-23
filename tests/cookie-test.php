<?php
/**
 * Loads the drop-in without WordPress and checks the cookie reader.
 */

function add_action($hook, $callback, $priority = 10) {
}

function apply_filters($name, $value) {
    return $value;
}

function is_admin() {
    return false;
}

function wp_unslash($value) {
    return is_string($value) ? stripslashes($value) : $value;
}

function esc_html($value) {
    return htmlspecialchars((string) $value, ENT_QUOTES, 'UTF-8');
}

define('ABSPATH', __DIR__);
require dirname(__DIR__) . '/zaraz-consent.php';

function expect($label, $got, $want) {
    if ($got !== $want) {
        fwrite(STDERR, $label . ' got ' . var_export($got, true) . "\n");
        exit(1);
    }
}

expect('missing', zaraz_consent_choice('analytics'), null);

$_COOKIE['cf_consent'] = '{"analytics":true}';
expect('granted', zaraz_consent_choice('analytics'), true);

$_COOKIE['cf_consent'] = '{"analytics":false}';
expect('refused', zaraz_consent_choice('analytics'), false);

$_COOKIE['cf_consent'] = '{"analytics":"yes"}';
expect('not a boolean', zaraz_consent_choice('analytics'), null);

$_COOKIE['cf_consent'] = '{"analytics":true}';
expect('other purpose', zaraz_consent_choice('marketing'), null);

$_COOKIE['cf_consent'] = '{\"analytics\":true}';
expect('slashed', zaraz_consent_choice('analytics'), true);

$script = zaraz_consent_script();
if (strpos($script, 'zarazConsentAPIReady') === false) {
    fwrite(STDERR, "script does not wait for the consent API\n");
    exit(1);
}
if (strpos($script, 'http') !== false) {
    fwrite(STDERR, "script must not fetch\n");
    exit(1);
}

// Issue #2. Without `once`, a second `zarazConsentAPIReady` binds a second
// click listener and one click toggles the modal twice.
if (strpos($script, 'once: true') === false) {
    fwrite(STDERR, "the readiness listener is not one-shot\n");
    exit(1);
}

// ISSUE #2, THE TAG. Both branches are driven, because the fallback is the
// one that runs here by default and a test that only sees the fallback
// proves nothing about the path real WordPress takes.
$fallback = zaraz_consent_script_tag();
expect('fallback opens a script tag', strpos($fallback, '<script>') === 0, true);
expect('fallback closes it', substr($fallback, -9), '</script>');
expect('fallback carries the script', strpos($fallback, 'zarazConsentAPIReady') !== false, true);

// DEFINED INSIDE A CONDITIONAL ON PURPOSE. PHP hoists an unconditional
// top-level function, so a plain declaration here would already exist while
// the fallback check above ran, and that check would silently exercise the
// WordPress branch instead. It did exactly that on the first attempt. A
// conditional block defers the declaration to this point in execution.
if (true) {
    function wp_get_inline_script_tag($javascript, $attributes = array()) {
        return "<script nonce=\"TESTNONCE\">" . $javascript . "</script>";
    }
}

$viaWordPress = zaraz_consent_script_tag();
expect('the helper is used when present', strpos($viaWordPress, 'nonce="TESTNONCE"') !== false, true);
expect('and it still carries the script', strpos($viaWordPress, 'zarazConsentAPIReady') !== false, true);

echo "cookie_ok\n";
