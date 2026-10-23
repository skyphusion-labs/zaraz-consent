# Zaraz Consent

A WordPress must-use file for [Cloudflare Zaraz](https://developers.cloudflare.com/zaraz/consent-management/) cookie consent.

Cloudflare injects Zaraz on the proxied zone. This plugin ships no banner, no stylesheet and no script request. It adds one footer button. The button stays hidden until `zarazConsentAPIReady`. The button then sets `zaraz.consent.modal = true`. PHP reads the consent cookie when something asks for it.

## Read this before you install it

**This plugin does not gate anything. It does not give your site consent.**

The plugin does two jobs. It reopens a modal that Zaraz draws. It also reads the visitor choice back in PHP. Cloudflare does all the gating, in the Zaraz configuration. The plugin does none of it.

**Zaraz can gate only Zaraz tools.** WordPress, your theme and other plugins also load scripts. Those are not Zaraz tools. No purpose reaches them. Correct Cloudflare configuration does not stop them. Read [What Zaraz cannot gate](#what-zaraz-cannot-gate) first. That section decides whether this repo solves your problem.

Do the configuration below before you copy the file. The order matters. Out of order, you get a button that does nothing, and no way to tell why.

## Prerequisite order

Each step depends on the step above it.

1. Zaraz is enabled on the zone.
2. Purposes are defined.
3. Tools are assigned to purposes.
4. Consent is enabled.
5. The plugin is installed.

Start at step 5 and you see a hidden button and no modal. WordPress does not explain why. Stop after step 4 and you get a modal that records a choice. That modal enforces nothing.

### 1. Zaraz must be enabled on the zone

Check this from the edge. You need no credential:

```
curl -o /dev/null -w "%{http_code}\n" https://<your-zone>/cdn-cgi/zaraz/i.js
curl -o /dev/null -w "%{http_code}\n" https://<your-zone>/cdn-cgi/trace
```

`i.js` returns 200 when Zaraz is on. It returns 404 when Zaraz is off. The second request is the control. `/cdn-cgi/trace` returns 200 on any Cloudflare proxied zone. So 200 on `trace` with 404 on `i.js` means Zaraz itself is off. It does not mean the `cdn-cgi` path is unreachable or the host is wrong.

Measured 2026-10-23 on `ggc.sh`, `skyphusion.org` and `vivijure.com`. All three returned 404 for `i.js` and 200 for `trace`. Zaraz serves on none of them.

A zone can hold a Zaraz configuration and still not serve the script. Those three zones hold a configuration. It reports `autoInjectScript: true` and contains zero tools. So reading the configuration does not replace the check above.

### 2. Purposes

A purpose is what the visitor agrees to. A purpose is not a tool. A purpose is not a vendor. It is a category, such as analytics or marketing. Each purpose has an id, a display name and a description. The modal lists one row for each purpose.

Purposes live in `iac/consent.json` under `purposes`. The key is the purpose id. Use that id everywhere else, including in `zaraz_consent_choice()`:

```json
"purposes": {
  "analytics": {
    "name": "Analytics",
    "description": "Measure how the site is used."
  }
}
```

`sync_consent.py` refuses a purpose that has no name or no description.

Zaraz does not list a purpose that has no tool assigned. Defining purposes alone changes nothing a visitor can see.

### 3. Assign tools to purposes, which is the whole mechanism

The `defaultPurpose` field gates a tool. That one field decides whether consent applies to the tool.

**A tool with no `defaultPurpose` skips consent.** In Cloudflare's words: "When you add a new tool to your website, Zaraz does not assign any purpose to it. This means that this tool will skip consent by default."

That default makes the dangerous state quiet. Enable consent over unassigned tools and the system gates nothing. The modal appears. A choice is recorded. A cookie is written. Every tool keeps firing as before.

`iac/tool-purposes.json` maps a tool id to a purpose id. It ships empty:

```json
{}
```

The empty default is deliberate. It stops a sync from attaching Google, Meta or anything else. **A sync refuses to enable consent over an empty map.** That combination would show a modal and gate nothing. Add the tool to gate it:

```json
{
  "<tool-id-from-the-live-zaraz-config>": "analytics"
}
```

The tool must already exist in the zone. `sync_consent.py` does not create tools. It refuses a tool id that the live configuration does not hold. It also refuses a purpose id that `consent.json` does not hold.

### 4. Enable consent

`consent.enabled` in `iac/consent.json` switches the system on. On its own it does three things only. Zaraz draws the modal. Zaraz writes the consent cookie. The plugin button becomes usable. **It gates no tool at all.** Step 3 is the only source of gating.

`consent.cookieName` must match what the plugin reads. The default on both sides is `cf_consent`. If the zone uses another name, define `ZARAZ_CONSENT_COOKIE` in `wp-config.php` to the same string as `consent.cookieName`.

### 5. Install the plugin

```
cp zaraz-consent.php wp-content/mu-plugins/zaraz-consent.php
```

There is no activation step and no settings row. WordPress loads `mu-plugins` on its own.

**Check your Content Security Policy.** The plugin emits an inline `<script>`. WordPress builds that tag with `wp_get_inline_script_tag()`. That helper runs the attributes through the `wp_inline_script_attributes` filter. Add your nonce in that filter and the tag carries it. The plugin then works under a nonce-based policy as well as under `unsafe-inline`.

On WordPress older than 5.7 the helper does not exist. The plugin falls back to a plain tag. That tag needs `unsafe-inline` in `script-src`. Without it the browser blocks the script. The button then stays hidden and nothing reports an error.

## What Zaraz cannot gate

Zaraz gates Zaraz tools. It reaches nothing else.

WordPress, your theme and other plugins serve their scripts from your own origin. Zaraz never sees those scripts. No purpose maps to them. Consent has no effect on them.

This is not a corner case. The GGC store was measured on 2026-10-23. WooCommerce order attribution and its bundled sourcebuster library run on every page. They run with `allowTracking: true` and no consent check. They write eight `sbjs_*` cookies. They capture referrer, UTM parameters, session entry URL, page count, visit count and user agent. Checkout then posts all of that into the order. Every part of it is first-party WordPress, so Zaraz cannot reach it.

Configure Zaraz consent on that store and you get a modal, a recorded choice and a `cf_consent` cookie. The tracking above continues unchanged. **That is a consent record without consent. It is worse than no banner, because the code does not keep the compliance claim.**

List every tracker you must gate before you adopt this. Check that each one is a Zaraz tool. If some are not, this repo is not enough on its own. Turn those trackers off, move them into Zaraz, or gate them another way. The GGC measurement is in skyphusion-labs/ggc#49.

## Applying the configuration

`iac/sync_consent.py` writes the zone:

```
python3 iac/sync_consent.py iac/consent.json iac/tool-purposes.json
```

The script GETs the live configuration. It replaces the `consent` object. It sets `defaultPurpose` on the tools named in the map. It then PUTs the whole configuration back. It does not create tools. Both requests go to:

```
https://api.cloudflare.com/client/v4/zones/<zone-id>/settings/zaraz/config
```

Set `CLOUDFLARE_API_TOKEN` and `ZONE_ID` in the environment. `ZONE_ID` is the 32 character zone id. The script reads the token from the environment and never prints it.

The script refuses to enable consent over an empty tool map. It checks before the PUT, not after it. Pass `--allow-empty-tool-map` to proceed anyway. Use that flag when you stage the purposes first. Zaraz lists no purpose until a tool is assigned to it.

The script sends the whole configuration back, including `zarazVersion`. Nobody has tested whether the API accepts that field or manages it itself. Testing it needs a live write, so this is unverified.

### API token permissions

The Zaraz configuration sits behind its own permission group. A token that reads the zone can still be refused here.

The permission group list on a Cloudflare account holds three Zaraz groups. All three are zone scoped:

| Group | Use | Status |
|---|---|---|
| `Zaraz Read` | `GET .../settings/zaraz/config` | measured working end to end |
| `Zaraz Edit` | `PUT .../settings/zaraz/config` | named from the permission group list, not verified by a write |
| `Zaraz Admin` | not needed for a sync | named from the permission group list, not verified by a write |

The list does not say what `Zaraz Admin` grants beyond `Zaraz Edit`. This file does not guess. A sync reads the configuration and writes it back. So reach for `Zaraz Edit`. `Zaraz Admin` is wider than the task needs.

**Know the symptom. It does not look like a scope problem.** Without `Zaraz Read` the GET returns **403** with error code **10000, "Authentication error"**. A wrong path under the same prefix also returns 403. The status alone cannot tell the two apart. Most readers conclude they typed the URL wrong. Confirmed 2026-10-23. One token returned 200 on four zones holding `Zaraz Read`. It returned 403 on four zones without it. `GET /zones/<zone-id>` returned 200 on all eight.

That last reading is the trap. **A successful zone read proves nothing about Zaraz access.** Do not treat it as evidence that your token is scoped correctly. Test the Zaraz endpoint itself.

This file leaves out the group ids on purpose. An id rots, and readers copy one rather than look it up. Read the labels from the permission group list on your own account when you mint the token.

Scope the token to the zones you intend to change, and to no others.

## What the button does

Zaraz shows its own modal on a first visit. It does so when consent is enabled and a tool is assigned to a purpose. Later visits do not show the modal again. The button reopens it.

The cart cookie and the Cloudflare security cookies are not Zaraz tools. This plugin does not gate them.

`zaraz_consent_choice('analytics')` returns true, false, or null. Null means the visitor has not chosen. The purpose id is the key in the Zaraz config, not the display name.

## Writing your own text

`companyStreetAddress` in the example is empty. Add an address only when you have one. The intro HTML describes the choice. It is not a privacy policy. Replace it with your own wording, and point it at your privacy page.

## Not measured

Stated so that nobody reads a silence as a finding.

**The `cf_consent` cookie lifetime and flags.** The name and format are known. The cookie is a JSON object. It maps each purpose id to `true`, `false`, or absent. Cloudflare does not document the expiry, `Secure`, `SameSite`, `HttpOnly`, path or domain. No zone in reach had consent configured, so there was no live cookie to read. Measure it on your own zone before you write a cookie policy.

**The performance comparison.** The code supports the structural claim. There is no banner library, no stylesheet and no external script request. The footer markup is roughly 500 bytes, inline. Cloudflare runs the tags at the edge. `tests/contract.sh` checks that the plugin adds no enqueue and no remote URL. No before and after measurement exists. Neither Zaraz nor this plugin runs on a zone where someone could take one.

## Licence

GPL-2.0-or-later. The release tag matches the `Version` header in `zaraz-consent.php`.
