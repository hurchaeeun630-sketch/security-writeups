# FaaS 1.5

- **Event:** scriptCTF 2026
- **Category:** Pwn
- **Points:** 500
- **Result:** First blood at the time of solving

## Summary

The service fetched a user-supplied host with curl and displayed the page title. The host was inserted into the curl command without safe argument handling. Because spaces were permitted, additional curl arguments could be injected, enabling an arbitrary file read.

## Exploitation

curl concatenates the output of multiple URLs. I hosted a short document containing an opening `<title>` tag without a closing tag, then supplied a local `file://` URL as an additional argument:

```text
paste.rs/hS49H -L -k file:///etc/hostname
```

The first response began the title, and the local file content was appended inside it. The application's title parser therefore returned the file contents. Inspecting `/etc/passwd` revealed the challenge user's home directory, after which the same technique read the flag directly:

```text
paste.rs/hS49H -L -k file:///home/crazy_user_for_challenge/flag.txt
```

For longer files, curl's `--next` and `-r` options could request selected byte ranges. This made the primitive practical even with the service's input and output limits.

## Root Cause

The application treated a validated string as part of a shell command rather than passing it as a single argument to a process API. Input validation did not account for curl's argument grammar.

## Mitigation

- Avoid invoking a shell for network requests.
- Pass the URL as a single argument through a process API.
- Enforce an allowlist of schemes and destinations.
- Block access to local-file schemes and internal resources.

## Flag

```text
scriptCTF{0S_c0mm4nd_1nj3ct10n_1s_t3chn1c4lly_Pwn_0d8b9e3df3f4}
```
