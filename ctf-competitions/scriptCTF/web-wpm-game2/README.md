**Web/wpm-game2**

**Challenge**

Recover the flag through a constrained server-side expression.

**Solution**

The `wpm` parameter is passed to `eval()`, but the input filter blocks most useful characters and allows at most 18 distinct characters.

In the original wpm-game, Flask debug mode exposed exception messages. This time debug mode is disabled, so every useful payload only returns the same 500 error. The response body gives us nothing, but a large calculation inside `eval()` still makes the response noticeably slower.

This gives us a timing oracle.

To stay within the 18-character limit, the payload only uses:

```text
o p e n x t b y s ( ) [ ] + - * 0 1
```

Quotes are replaced with `bytes([...])`, and the flag is opened in binary mode so each indexed character becomes an integer. Since writing `"rb"` is impossible, the letters are taken from the first line of `/etc/passwd`:

```python
next(open(P))[0] + next(open(P))[23]
```

For a flag byte `B` and a guess `k`, this expression is slow only when `B > k`:

```python
11**(1111111*(0**(0**(B-k))))
```

Using this as a binary-search oracle lets us recover `/app/flag.txt` one byte at a time. A second equality check was used to confirm each byte because occasional network delays could otherwise produce a wrong character.

**Flag**

**scriptCTF{r3v3ng3_1337_52c85480111a}**

## Experimental Design

Because successful and unsuccessful evaluations both returned the same HTTP 500 response, each guess was measured repeatedly and compared against a baseline. A deliberately expensive exponentiation amplified the timing difference, while binary search reduced the number of requests needed per byte. A final equality probe confirmed each recovered byte and limited errors caused by transient latency.

The character-set restriction shaped every part of the payload. `bytes([...])` replaced quoted strings, `/etc/passwd` supplied the letters needed to construct binary mode, and indexed reads converted flag bytes into integers suitable for arithmetic comparison. The exploit therefore demonstrates that denying visible output does not eliminate information leakage when attacker-controlled computation affects response time.

The correct defense is to remove `eval`, parse the expected numeric input with a strict grammar, impose execution limits, and keep error handling and response timing independent of secret-dependent computation.
