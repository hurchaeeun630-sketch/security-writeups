# Leaks

- **Event:** scriptCTF 2026
- **Category:** Pwn
- **Points:** 500
- **Author:** NoobMaster
- **Constraint:** No binary was provided

## Summary

The service passed user input directly to `printf`, creating a format-string vulnerability. With no local binary, I used the vulnerability as an arbitrary-read primitive, reconstructed the remote executable from memory, analyzed the recovered code, and built a 24-byte final payload.

## Reconnaissance

The service disclosed an address labeled `stdin`. Positional format specifiers confirmed that the input was used as the format string, equivalent to `printf(buf)`. The input was limited to 28 bytes, making payload size a central constraint.

By placing an address after the format string and referencing its stack position with `%s`, I could read arbitrary mapped memory. The leaked `stdin` address also provided a stable offset for recovering the PIE base.

## Recovering the Program

I iteratively read the executable's mapped pages and saved the recovered bytes locally. Disassembling them with Capstone exposed the program flow and the relevant writable targets. This replaced the normal workflow of analyzing a supplied ELF file.

The final exploit used a half-word write through `%hn`. A four-byte alignment marker kept the target pointer at the expected stack position:

```python
payload = b"%26465c%8$hn" + b"FSOP" + p64(base + 0x4012)
```

The write redirected the relevant global function pointer/GOT-controlled path so that subsequent program behavior printed the flag.

## Takeaway

A format-string bug can provide both disclosure and write primitives. When a remote-only challenge withholds its binary, sufficient memory disclosure can reconstruct the executable and restore a conventional analysis workflow.

## Flag

```text
scriptCTF{ju57_l34k_3v3ry7h1ng_4nd_r34d_fl4g_7cf6ffef725e}
```
