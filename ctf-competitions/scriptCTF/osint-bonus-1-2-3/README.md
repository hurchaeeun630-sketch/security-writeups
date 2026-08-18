# Bonus 1, 2 & 3

- **Event:** scriptCTF 2026
- **Category:** OSINT
- **Points:** 500 each

## Scope

All three challenges were solved through passive investigation of public profiles and repositories connected to the fictional “newbie” character. No messages were sent and no target accounts were contacted.

## Bonus 1

A Discord profile exposed the identifier `the.newbie.1337`, which led to a public Instagram account. Since GitHub usernames cannot contain periods, I tested the normalized form `the-newbie-1337` and found a matching GitHub profile and the public repository `securing-malware`.

Reviewing `virus-example.py` revealed a transaction-like value. Following that artifact through the public evidence exposed the first bonus flag.

```text
scriptCTF{h1dd3n_1n_fr0nt_0f_m3}
```

## Bonus 2

I continued reviewing the public account metadata rather than limiting the search to visible post text. An image's accessibility metadata contained the second flag. This demonstrated that alt text and other secondary fields can carry relevant OSINT evidence.

```text
scriptCTF{b0nus_fl4g_2_f0und}
```

## Bonus 3

The connected GitHub repository contained another clue in its web content. Inspecting the repository and page source revealed a flag embedded in a CSS comment:

```css
/* scriptCTF{th3_n3wb13_1s_n0w_4_pr0f3ss10n4l} */
```

## Investigation Pattern

```text
Discord identifier
  -> normalized username variants
  -> public social profile
  -> matching GitHub account
  -> repository files and metadata
  -> image accessibility metadata and page source
```

The main lesson was to preserve intermediate discoveries and inspect metadata, source files, and naming variations—not only the obvious visible content.
