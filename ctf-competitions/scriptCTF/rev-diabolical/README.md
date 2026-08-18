# Diabolical

- **Event:** scriptCTF 2026
- **Category:** Reversing
- **Points:** 489
- **Author:** NoobMaster

## Summary

The challenge presented a large, statically linked, stripped Go executable. Its size, obfuscated symbols, and references to cryptographic primitives suggested that the intended path involved extensive reverse engineering. Those features were distractions: the flag was appended to the ELF section-name string table, `.shstrtab`.

## Analysis

Initial inspection identified a 64-bit x86 ELF executable of roughly 3 MB. `strings` produced a large amount of Go runtime and cryptographic noise, so I inspected the end of the file and the section table instead of immediately reconstructing program logic.

```bash
readelf -S vault
tail -c 512 vault | xxd
```

The final bytes included a Base64-looking string after the normal section names. Decoding it revealed the flag:

```bash
printf '%s' '<base64-value>' | base64 -d
```

The data belonged to `.shstrtab`, which normally stores section names such as `.text`, `.data`, and `.bss`. Because this table is metadata rather than executable logic, it is easy to overlook when focusing only on disassembly.

## Takeaway

Before committing to complex static analysis, inspect the complete file structure, including overlays, section tables, string tables, and trailing data. File-format anomalies can be more informative than the apparent program logic.

## Flag

```text
scriptCTF{n0t_s0_h4rd_4ft3r_4ll}
```
