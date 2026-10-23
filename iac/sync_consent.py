#!/usr/bin/env python3
"""Write Zaraz consent onto the live zone config.

GET the current config, replace consent, set defaultPurpose on tools named
in the map, and PUT the result. The script does not create tools. It does
not print the API token or the Zaraz debug key.

IT REFUSES TO ENABLE CONSENT OVER AN EMPTY TOOL MAP (issue #1). Cloudflare
does not gate a tool that has no defaultPurpose, so consent.enabled with no
tool assigned is a switched-on system that gates nothing: the modal appears,
a choice is recorded, a cookie is written, and every tool keeps firing. That
is worse than no banner, because it is a compliance claim the zone does not
keep.

The check runs inside merge(), BEFORE the PUT. It used to be a line printed
after the write, which could report the state but not prevent it.

Pass --allow-empty-tool-map to proceed anyway. That is the documented
bootstrap path: Zaraz does not list a purpose until a tool is assigned to it,
so an operator staging the purposes first has a real reason to want this. It
is a flag on the command line rather than a value in a file, so it is chosen
once per run and cannot become a default nobody re-reads.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request


def merge(config, consent, tool_purposes, allow_empty_tool_map=False):
    if not isinstance(config, dict):
        raise ValueError("config must be an object")
    if not isinstance(consent, dict) or not isinstance(consent.get("enabled"), bool):
        raise ValueError("consent.enabled must be a boolean")
    purposes = consent.get("purposes", {})
    if not isinstance(purposes, dict):
        raise ValueError("consent.purposes must be an object")
    for purpose_id, purpose in purposes.items():
        if (
            not isinstance(purpose, dict)
            or not isinstance(purpose.get("name"), str)
            or not isinstance(purpose.get("description"), str)
            or purpose.get("name") == ""
            or purpose.get("description") == ""
        ):
            raise ValueError("purpose %s needs a name and a description" % purpose_id)
    if not isinstance(tool_purposes, dict):
        raise ValueError("tool map must be an object")
    # BEFORE THE WRITE, not after it. Reported after the PUT this is a
    # description of a state the operator is already in.
    if consent["enabled"] and purposes and not tool_purposes and not allow_empty_tool_map:
        raise ValueError(
            "refusing to enable consent with an empty tool map: no tool has a "
            "defaultPurpose, so Zaraz would gate nothing while showing a modal "
            "and writing a cookie. Assign a tool to a purpose in the map, or "
            "pass --allow-empty-tool-map if you are staging the purposes first."
        )
    tools = config.get("tools")
    if tools is None:
        tools = {}
    if not isinstance(tools, dict):
        raise ValueError("config.tools must be an object")
    updated = json.loads(json.dumps(config))
    updated["tools"] = json.loads(json.dumps(tools))
    for tool_id, purpose_id in tool_purposes.items():
        if not isinstance(purpose_id, str) or purpose_id == "":
            raise ValueError("tool %s needs a purpose id" % tool_id)
        if tool_id not in updated["tools"]:
            raise ValueError("tool %s is not in the live config" % tool_id)
        if purpose_id not in purposes:
            raise ValueError("purpose %s is not in consent.json" % purpose_id)
        if not isinstance(updated["tools"][tool_id], dict):
            raise ValueError("tool %s is not an object" % tool_id)
        updated["tools"][tool_id]["defaultPurpose"] = purpose_id
    updated["consent"] = consent
    return updated


def _fail(step, code, body):
    print("%s HTTP %s" % (step, code))
    if isinstance(body, dict):
        for err in body.get("errors") or []:
            if isinstance(err, dict):
                message = err.get("message") or ""
                print("error", err.get("code"), str(message)[:200])
    sys.exit(1)


def _call(method, url, token, payload):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"success": False, "errors": [{"code": exc.code, "message": raw[:200]}]}
        return exc.code, body


def main(argv):
    allow_empty = "--allow-empty-tool-map" in argv
    argv = [a for a in argv if a != "--allow-empty-tool-map"]
    if len(argv) != 2:
        print(
            "usage: sync_consent.py [--allow-empty-tool-map] consent.json "
            "tool-purposes.json",
            file=sys.stderr,
        )
        return 1
    token = os.environ.get("CLOUDFLARE_API_TOKEN") or ""
    zone_id = os.environ.get("ZONE_ID") or ""
    if token == "":
        print("CLOUDFLARE_API_TOKEN is required", file=sys.stderr)
        return 1
    if re.fullmatch(r"[a-f0-9]{32}", zone_id) is None:
        print("ZONE_ID must be a 32 character zone id", file=sys.stderr)
        return 1
    with open(argv[0], encoding="utf-8") as handle:
        consent = json.load(handle)
    with open(argv[1], encoding="utf-8") as handle:
        tool_purposes = json.load(handle)
    url = "https://api.cloudflare.com/client/v4/zones/%s/settings/zaraz/config" % zone_id
    code, body = _call("GET", url, token, None)
    if code != 200 or not isinstance(body, dict) or not body.get("success"):
        _fail("get", code, body if isinstance(body, dict) else {})
    config = body.get("result")
    if not isinstance(config, dict):
        print("get returned no config")
        return 1
    try:
        updated = merge(config, consent, tool_purposes, allow_empty)
    except ValueError as exc:
        print(str(exc))
        return 1
    # THE INTENT, PRINTED BEFORE THE WRITE. Everything this script used to
    # print described a zone it had already changed.
    print("about to PUT:")
    print("  consent.enabled   %s" % consent.get("enabled"))
    print("  purposes          %d" % len(consent.get("purposes") or {}))
    print("  tools to assign   %d" % len(tool_purposes))
    if allow_empty and not tool_purposes:
        print("  --allow-empty-tool-map given: this sync will gate nothing")
    code, body = _call("PUT", url, token, updated)
    if code != 200 or not isinstance(body, dict) or not body.get("success"):
        _fail("update", code, body if isinstance(body, dict) else {})
    result = body.get("result") if isinstance(body.get("result"), dict) else {}
    saved = result.get("consent") if isinstance(result.get("consent"), dict) else {}
    purposes = saved.get("purposes") if isinstance(saved.get("purposes"), dict) else {}
    print("consent_enabled", saved.get("enabled"))
    print("purpose_count", len(purposes))
    print("tools_assigned", len(tool_purposes))
    if len(tool_purposes) == 0 and len(purposes) > 0:
        print("no tools assigned; Zaraz does not list a purpose until one is")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
