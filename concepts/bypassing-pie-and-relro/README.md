# Bypassing PIE and RELRO

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224304590008). Translated and reformatted in English.

ASLR (Address Space Layout Randomization) is a protection technique that randomly places memory addresses each time a program is executed.

When ASLR is applied, the following addresses change each time it is run.

stack address

heap address

Shared library address

libc address

Library function address such as printf()

However, for executable files without PIE applied, the internal address of the executable file may be fixed even if ASLR is turned on.

Even if you run it multiple times, for example:

main addr: 0x4011b6

If the main() address remains the same, the address of the code area of the executable file is fixed.

PIE (Position-Independent Executable) is a protection technique that allows the executable file itself to be loaded at a random address.

This means that when PIE is applied, ASLR is also applied to the code region of the executable.

If you organize it

status

stack/heap/libc address

Executable file code address

ASLR only applies

random

fixed

Apply ASLR + PIE

random

random

If PIE is not applied, the main() (executable) address is fixed.

When PIE is applied, the main() address also changes each time it is executed.

PIC (Position-Independent Code) is a code that can be executed normally no matter what address it is loaded into.

Shared libraries (libc.so, etc.) are usually created in PIC format because they are loaded into random locations in memory.

key differences

addr: ELF 64-bit LSB executable

libc.so.6: ELF 64-bit LSB shared object

addr → regular executable file

libc.so.6 → shared object, i.e. library

A shared library must operate at any address, so a PIC is required.

In regular code, you can reference specific data by its absolute address.

Example:

0x4005a1

However, PIC code never writes addresses directly, but uses relative addresses based on the current instruction location.

Example:

rip + 0xa2

In other words, PIC uses RIP-relative addressing.

PIE bypass key

When PIE is applied, the code address changes every time, so the attacker must first find out the code base address.

What is a code base?

This is the starting address at which the program is loaded into memory.

If you know the specific function address, you can calculate it like this:

code base = leaked address - offset

For example, if the actual address of main() is leaked, and you know the offset of main(), you can calculate the base address of the executable.

Partial Overwrite

Even if PIE is applied, the entire address is not completely random.

Typically, the lower 12 bits of the code region address are retained because of page alignment.

So, rather than covering the entire return address, you can attack by changing only the last 1-2 bytes.

This technique is called Partial Overwrite.

core idea

If the original return address and the target function address differ only by some lower bytes,

You can change the execution flow by covering only part of it.

However, changing more than 2 bytes may lower the success rate due to ASLR, and in some cases, brute force is required.

RELRO (Relocation Read-Only) is a protection technique that changes important data areas in the ELF binary to read-only to prevent attackers from overwriting the values.

In particular, protecting the following areas is key:

GOT

.got

.got.plt

.init_array

.fini_array

GOT and Lazy Binding

ELF uses the Global Offset Table (GOT) when calling external library functions.

For example, the actual addresses of functions such as printf, puts, and malloc are stored in the GOT.

Lazy Binding

Lazy Binding is a method of finding the actual address of a library function when it is first called and storing that address in the GOT.

That is:

Before first call → No actual function address in GOT

When calling for the first time → find the actual address

After that → save the address in GOT and reuse it

The problem is that this process requires that the GOT be able to be modified during execution.

So, if write permission remains in the GOT, an attacker can overwrite the GOT value. This allows the attacker to change the flow of execution.

For example:

printf@GOT → Overwrite with system address

Then, when your program calls printf(), system() can actually run.

This type of attack is called GOT Overwrite.

Partial RELRO

Partial RELRO protects only some areas as read-only.

Protected areas:

.init_array

.fini_array

.got

However, the following areas may still be writable:

.got.plt

reason

Partial RELRO uses Lazy Binding.

Lazy Binding requires writing the function address to .got.plt during execution.

So .got.plt still has write permission, and a GOT Overwrite attack using this area may be possible.

Full RELRO

Full RELRO makes the entire GOT-related area read-only.

Full RELRO does not use lazy binding, but all library function addresses are pre-bound when the program starts.

This is called Now Binding.

Lazy Binding → Address is determined when the function is first called

Now Binding → All addresses are determined when the program starts.

Because address resolution is done early in execution, the GOT does not require write permission thereafter.

So in Full RELRO:

.got

.got.plt

Write permission to the zone is removed.

Full RELRO detour direction

It is difficult to overwrite GOT in Full RELRO.

So the attacker looks for another function pointer or hook instead of GOT.

Representative examples:

__malloc_hook

__free_hook

These values exist within libc, and in the past could have been exploited to change the flow of malloc() or free() calls.

For example:

__free_hook → system

free("/bin/sh")

Connecting like this may lead to shell execution.
