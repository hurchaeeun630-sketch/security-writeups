# Rev/MeowvelousShop

**Challenge**

Analyze a custom virtual machine and uncover the hidden flag path.

**Solution**

**The program asks for a nine-character alphanumeric membership ID. Its VM updates a 64-bit accumulator for each character:**

```text
state = rol(state, 13) ^ (0xff51afd7ed558ccd * character)
```

**Because the final value is an XOR of nine independent terms, I split the ID into four and five characters and used a meet-in-the-middle search instead of trying all `62^9` possibilities. This produced one valid ID:**

```text
N0Fl4gY37
```

**Entering that ID and selecting Redeem prints a fake failure message. The interesting part is that the `printf` GOT entry at `0x40a008` does not contain its normal lazy-binding address, `0x402046`. It has been patched to point to a hidden stub at `0x4029d4`.**

```text
Redeem path
  -> call printf@plt
  -> jmp [0x40a008]
  -> hidden stub at 0x4029d4
  -> call the real printf
  -> call print_flag at 0x403620
```

**The stub first prints `gud try, but no flag for u`, then calls `print_flag()` and reads `flag.txt`. Since the hidden path is reached through a GOT data pointer rather than a normal branch, it is easy to miss during static analysis. The credits, jackpot, and shop grinding are all decoys.**

**Flag**

**`scriptCTF{bu5y_c47_unw1nd1ng_fr0m_h15_5h1f7_@_7h3_5h0p_4e7ca567d608}`**

## Methodology

The nine-character identifier has `62^9` candidates, which is impractical to brute-force directly. Because the accumulator is composed from XOR-linear contributions after fixed rotations, I computed all four-character partial states, stored them in a lookup table, and matched them against five-character states generated backward from the target. This meet-in-the-middle split reduces the effective work from one enormous search to two manageable searches plus a table lookup.

After obtaining a valid identifier, the visible failure text did not match the program state, so I inspected the call target rather than trusting the message. Cross-references to `printf@plt` alone were incomplete: the GOT slot had been rewritten to a hidden stub. Following the indirect jump exposed the real control flow and the call to `print_flag`.

This challenge reinforced two reversing habits: use algebraic structure to reduce search complexity, and inspect runtime linkage data when static cross-references do not explain observed behavior.
