# Zaraz Consent

One must-use file, `zaraz-consent.php`, copied to `wp-content/mu-plugins/zaraz-consent.php`. Do not turn it into a plugin with an admin screen, an options row, or its own banner assets. Zaraz draws the modal. This file reopens it and reads `cf_consent`.

`iac/sync_consent.py` is the zone write. It replaces `consent` on the live config and sets `defaultPurpose` for ids listed in `iac/tool-purposes.json`. It must not create a tool. The example map stays `{}`.

Do not put a street address into the example. `companyStreetAddress` stays empty until the operator has one. Do not print `CLOUDFLARE_API_TOKEN` or the Zaraz debug key.

License is GPL-2.0-or-later, the same grant as WordPress. `gh` as skyphusion: `env -u GH_TOKEN -u GITHUB_TOKEN -u GITHUB_PERSONAL_ACCESS_TOKEN gh`.
