# Zaraz Consent

A WordPress must-use file for [Cloudflare Zaraz](https://developers.cloudflare.com/zaraz/consent-management/) cookie consent.

Cloudflare injects Zaraz on the proxied zone. This file does not ship a banner, a stylesheet, or a script request. The only front-end work is a footer button that stays hidden until `zarazConsentAPIReady`, then sets `zaraz.consent.modal = true`. The consent cookie is read in PHP when something asks.

Copy one file:

```
cp zaraz-consent.php wp-content/mu-plugins/zaraz-consent.php
```

There is no activation step and no settings row. WordPress loads `mu-plugins` on its own.

GPL-2.0-or-later.

## What the button does

Zaraz shows its own modal on a first visit when consent is enabled and a tool is assigned to a purpose. Later visits do not show it again. The button reopens it.

The cart cookie and Cloudflare's security cookies are not Zaraz tools. This file does not gate them.

If the zone uses a cookie name other than `cf_consent`, define `ZARAZ_CONSENT_COOKIE` in `wp-config.php` to the same string as `consent.cookieName`.

`zaraz_consent_choice('analytics')` returns true, false, or null. Null means the visitor has not chosen. The purpose id is the key in the Zaraz config, not the display name.

## Zone config

`iac/sync_consent.py` reads the live Zaraz config, replaces `consent`, and sets `defaultPurpose` on tools listed in `iac/tool-purposes.json`. It does not create tools. An empty map is the default, so a sync does not attach Google, Meta, or anything else.

Zaraz does not list a purpose that has no tool assigned. Leave the map empty until the tool already exists in the zone, then set its id to a purpose id from `iac/consent.json`.

`companyStreetAddress` in the example is empty. Put an address there only when you have one. The intro HTML is a description of the choice, not a privacy policy. Replace it with the wording you actually use, and point it at your privacy page.

Set `CLOUDFLARE_API_TOKEN` and `ZONE_ID` in the environment, then run:

```
python3 iac/sync_consent.py iac/consent.json iac/tool-purposes.json
```

The token is read from the environment and is not printed. `ZONE_ID` is the 32 character zone id.

A purpose with no tool still will not appear in the modal. The script says so when the map is empty.
