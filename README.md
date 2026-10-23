# Zaraz Consent

A WordPress must-use file for [Cloudflare Zaraz](https://developers.cloudflare.com/zaraz/consent-management/) cookie consent.

Cloudflare injects Zaraz on the proxied zone. This file does not ship a banner, a stylesheet, or a script request. The only front-end work is a footer button that stays hidden until `zarazConsentAPIReady`, then sets `zaraz.consent.modal = true`. The consent cookie is read in PHP when something asks.

## Read this before you install it

**This file does not gate anything. Installing it does not give your site consent.**

The plugin is a withdrawal control and a cookie reader. It reopens a modal that Zaraz draws, and it reads the choice back in PHP. All of the gating happens on the Cloudflare side, in the Zaraz configuration, and none of it happens here.

**Zaraz can only gate Zaraz tools.** If a script is enqueued by WordPress, by your theme, or by another plugin, it is not a Zaraz tool, no purpose reaches it, and no amount of correct Cloudflare configuration will stop it. See [What Zaraz cannot gate](#what-zaraz-cannot-gate), which is the section most likely to decide whether this repo solves your problem.

Work through the configuration below before you copy the file. The order matters, and the failure mode for doing it out of order is a button that does nothing with no way to tell why.

## Prerequisite order

Each step depends on the one above it.

1. Zaraz is enabled on the zone.
2. Purposes are defined.
3. Tools are assigned to purposes.
4. Consent is enabled.
5. The plugin is installed.

An operator who starts at step 5 sees a hidden button and no modal, and nothing in WordPress explains why. An operator who stops after step 4 gets a consent modal that records a choice and enforces nothing.

### 1. Zaraz must be enabled on the zone

Check it from the edge. This needs no credential:

```
curl -o /dev/null -w "%{http_code}\n" https://<your-zone>/cdn-cgi/zaraz/i.js
curl -o /dev/null -w "%{http_code}\n" https://<your-zone>/cdn-cgi/trace
```

`i.js` returns 200 when Zaraz is on and 404 when it is not. The second request is the control: `/cdn-cgi/trace` returns 200 on any Cloudflare proxied zone, so a 200 there with a 404 on `i.js` means Zaraz specifically is off, and not that the whole `cdn-cgi` namespace is unreachable or the host is wrong.

Measured 2026-10-23 on `ggc.sh`, `skyphusion.org` and `vivijure.com`: `i.js` 404 and `trace` 200 on all three. Zaraz is not serving on any of them.

A zone can hold a Zaraz configuration and still not serve the script. On those same zones the configuration exists, reports `autoInjectScript: true`, and contains zero tools. Reading the configuration is therefore not a substitute for the check above.

### 2. Purposes

A purpose is the thing a visitor actually agrees to. It is not a tool and not a vendor. It is a category such as analytics or marketing, with an id, a display name and a description, and the modal lists one row per purpose.

Purposes live in `iac/consent.json` under `purposes`. The key is the purpose id, which is what you use everywhere else, including in `zaraz_consent_choice()`:

```json
"purposes": {
  "analytics": {
    "name": "Analytics",
    "description": "Measure how the site is used."
  }
}
```

`sync_consent.py` refuses a purpose that is missing a name or a description.

Zaraz does not list a purpose that has no tool assigned, so defining purposes alone changes nothing a visitor can see.

### 3. Assign tools to purposes, which is the whole mechanism

A tool is gated by its `defaultPurpose` field. This single field is what decides whether consent applies to it.

**A tool with no `defaultPurpose` skips consent.** In Cloudflare's words: "When you add a new tool to your website, Zaraz does not assign any purpose to it. This means that this tool will skip consent by default."

That default is why the dangerous state here is quiet rather than loud. Consent enabled over a set of unassigned tools is a switched-on system that gates nothing: the modal appears, a choice is recorded, a cookie is written, and every tool keeps firing exactly as before.

`iac/tool-purposes.json` maps a tool id to a purpose id and it ships empty:

```json
{}
```

That empty default is deliberate, so that a sync never silently attaches Google, Meta or anything else. What is easy to miss is what it means operationally: **a sync run against this file as shipped enables consent and gates nothing.** To gate a tool, add it:

```json
{
  "<tool-id-from-the-live-zaraz-config>": "analytics"
}
```

The tool must already exist in the zone. `sync_consent.py` does not create tools, and it refuses a tool id that is not in the live configuration and a purpose id that is not in `consent.json`.

### 4. Enable consent

`consent.enabled` in `iac/consent.json` switches the system on. On its own it does three things and only three: it makes Zaraz draw the modal, it makes Zaraz write the consent cookie, and it makes the plugin's button usable. **It does not gate a single tool.** Gating comes from step 3 and nowhere else.

`consent.cookieName` must match what the plugin reads. The default on both sides is `cf_consent`. If the zone uses another name, define `ZARAZ_CONSENT_COOKIE` in `wp-config.php` to the same string as `consent.cookieName`.

### 5. Install the plugin

```
cp zaraz-consent.php wp-content/mu-plugins/zaraz-consent.php
```

There is no activation step and no settings row. WordPress loads `mu-plugins` on its own.

**One more prerequisite that is easy to miss: the plugin emits an inline `<script>`, so it needs a Content Security Policy that allows `unsafe-inline` in `script-src`.** Under a nonce-based policy the script is blocked, the code that un-hides the button never runs, and the button silently disappears. The page renders normally and nothing reports an error. An operator hardening their CSP would remove their own consent withdrawal control and have no signal that it happened. Tracked as #2.

## What Zaraz cannot gate

Zaraz gates Zaraz tools. Nothing else is in reach.

A script that WordPress, your theme or another plugin enqueues is served from your own origin as part of the page. Zaraz never sees it, no purpose maps to it, and consent has no effect on it.

This is not a corner case. On the GGC store, measured 2026-10-23, WooCommerce order attribution and its bundled sourcebuster library run on every page with `allowTracking: true` and no consent check. They write eight `sbjs_*` cookies and capture referrer, UTM parameters, session entry URL, page count, visit count and user agent, which are then posted into the order at checkout. All of it is first-party WordPress, so all of it is outside Zaraz.

Configure Zaraz consent on that store and you get a modal, a recorded choice and a `cf_consent` cookie, while the tracking above continues unchanged. **That is a consent record without consent, and it is worse than no banner, because it is a compliance claim the code does not keep.**

Before you adopt this, list every tracker you need to gate and check each one is a Zaraz tool. If some are not, this repo is not sufficient on its own and you need to turn those off, move them into Zaraz, or gate them another way. Measurement for the GGC case is in skyphusion-labs/ggc#49.

## Applying the configuration

`iac/sync_consent.py` is the zone write:

```
python3 iac/sync_consent.py iac/consent.json iac/tool-purposes.json
```

It GETs the live configuration, replaces the `consent` object, sets `defaultPurpose` on the tools named in the map, and PUTs the whole configuration back. It does not create tools. Both requests go to:

```
https://api.cloudflare.com/client/v4/zones/<zone-id>/settings/zaraz/config
```

Set `CLOUDFLARE_API_TOKEN` and `ZONE_ID` in the environment. `ZONE_ID` is the 32 character zone id. The token is read from the environment and is never printed.

The script prints its warning about an empty tool map after the PUT has already happened, so it cannot stop you reaching the state described in step 3. Tracked as #1.

### API token permissions

The Zaraz configuration sits behind its own permission group. A token that reads the zone perfectly well is still refused here.

The permission group list on a Cloudflare account contains three Zaraz groups, all of them zone scoped:

| Group | Use | Status |
|---|---|---|
| `Zaraz Read` | `GET .../settings/zaraz/config` | measured working end to end |
| `Zaraz Edit` | `PUT .../settings/zaraz/config` | named from the permission group list, not verified by a write |
| `Zaraz Admin` | not needed for a sync | named from the permission group list, not verified by a write |

The list does not say what `Zaraz Admin` grants beyond `Zaraz Edit`, so this file does not guess. A sync reads the configuration and writes it back, so `Zaraz Edit` is the group to reach for and `Zaraz Admin` is wider than the task needs.

**Know the symptom, because it does not look like a scope problem.** Without `Zaraz Read` the GET returns **403** with error code **10000, "Authentication error"**. A wrong path under the same prefix returns 403 as well, so the status alone cannot tell you which you are looking at, and the natural reading is that you typed the URL wrong. Confirmed 2026-10-23: the same token returned 200 on four zones carrying `Zaraz Read` and 403 on four zones without it, while `GET /zones/<zone-id>` returned 200 on all eight.

That last detail is the trap. **Being able to read the zone proves nothing about being able to read its Zaraz configuration.** Do not use a successful zone read as evidence that your token is scoped correctly; test the Zaraz endpoint itself.

Group ids are deliberately left out of this file. An id rots, and a reader will copy one rather than look it up. Read the labels from the permission group list on your own account when you mint the token.

Scope the token to the zones you intend to change and no others.

## What the button does

Zaraz shows its own modal on a first visit when consent is enabled and a tool is assigned to a purpose. Later visits do not show it again. The button reopens it.

The cart cookie and Cloudflare's security cookies are not Zaraz tools. This file does not gate them.

`zaraz_consent_choice('analytics')` returns true, false, or null. Null means the visitor has not chosen. The purpose id is the key in the Zaraz config, not the display name.

## Writing your own text

`companyStreetAddress` in the example is empty. Put an address there only when you have one. The intro HTML is a description of the choice, not a privacy policy. Replace it with the wording you actually use, and point it at your privacy page.

## Not measured

Stated so that nobody reads a silence as a finding.

**The `cf_consent` cookie's lifetime and flags.** Its name and format are known: a JSON object mapping each purpose id to `true`, `false`, or absent. Cloudflare does not document the expiry, `Secure`, `SameSite`, `HttpOnly`, path or domain, and no zone in reach had consent configured, so there was no live cookie to observe. Measure it on your own zone before you write it into a cookie policy.

**The performance comparison.** The structural claim is verifiable from the code: no banner library, no stylesheet, no external script request, roughly 500 bytes of inline footer markup, and tag execution moved to Cloudflare's edge. `tests/contract.sh` enforces the absence of an enqueue and of any remote URL in the drop-in. There is no before and after measurement against a conventional consent plugin, because neither Zaraz nor this plugin is deployed on a zone where one could be taken.

## Licence

GPL-2.0-or-later. The release tag matches the `Version` header in `zaraz-consent.php`.
