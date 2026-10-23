<?php
/**
 * Plugin Name: Zaraz Consent
 * Description: Reopens the Cloudflare Zaraz consent modal and reads the consent cookie. No banner library.
 * Version: 0.1.0
 * Author: Skyphusion
 * License: GPL-2.0-or-later
 *
 * Copy this file to wp-content/mu-plugins/zaraz-consent.php.
 * WordPress loads that directory itself. There is no activation step and no
 * settings query. The button stays hidden until Zaraz says its consent API
 * is ready, so a site without Zaraz does not show a control.
 */

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Cookie name Zaraz writes. Override it only when the zone config sets
 * consent.cookieName to something else.
 */
function zaraz_consent_cookie_name() {
    if (defined('ZARAZ_CONSENT_COOKIE') && is_string(ZARAZ_CONSENT_COOKIE) && ZARAZ_CONSENT_COOKIE !== '') {
        return ZARAZ_CONSENT_COOKIE;
    }
    return 'cf_consent';
}

/**
 * Read one purpose from the Zaraz consent cookie.
 *
 * @param string $purpose_id Purpose id from the Zaraz config.
 * @return bool|null True when granted, false when refused, null when unset.
 */
function zaraz_consent_choice($purpose_id) {
    $purpose_id = (string) $purpose_id;
    if ($purpose_id === '') {
        return null;
    }
    $name = zaraz_consent_cookie_name();
    if (!isset($_COOKIE[$name]) || !is_string($_COOKIE[$name])) {
        return null;
    }
    $data = json_decode(wp_unslash($_COOKIE[$name]), true);
    if (!is_array($data) || !array_key_exists($purpose_id, $data) || !is_bool($data[$purpose_id])) {
        return null;
    }
    return $data[$purpose_id];
}

/**
 * Static script. It does not fetch anything. Zaraz is already on the page
 * when Cloudflare injects it.
 */
function zaraz_consent_script() {
    return <<<'JS'
(function () {
  var button = document.getElementById("zaraz-consent-choices");
  if (!button) return;
  function arm() {
    if (button.parentNode) button.parentNode.hidden = false;
    button.addEventListener("click", function () {
      if (window.zaraz && zaraz.consent) zaraz.consent.modal = true;
    });
  }
  if (window.zaraz && zaraz.consent && zaraz.consent.APIReady) arm();
  else document.addEventListener("zarazConsentAPIReady", arm);
})();
JS;
}

function zaraz_consent_footer() {
    if (is_admin()) {
        return;
    }
    $label = apply_filters('zaraz_consent_button_label', 'Cookie choices');
    if (!is_string($label) || $label === '') {
        $label = 'Cookie choices';
    }
    echo '<p class="zaraz-consent-choices" hidden>';
    echo '<button type="button" id="zaraz-consent-choices">';
    echo esc_html($label);
    echo '</button></p><script>';
    echo zaraz_consent_script();
    echo '</script>';
}

add_action('wp_footer', 'zaraz_consent_footer', 20);
