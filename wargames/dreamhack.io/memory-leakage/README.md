# dreamhack.io: memory_leakage

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224313178214). Translated and reformatted in English.

memory_leakage memory_leakage.c
chaeeun@chaeeuns-MacBook-Air 87a12785-ba18-4ebf-9196-2d859dedbff2 % cat memory_leakage.c
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <string.h>

FILE *fp;

struct my_page {
 char name[16];
 int age;
};

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

int main()
{
 struct my_page my_page;
 char flag_buf[56];
 int idx;

 memset(flag_buf, 0, sizeof(flag_buf));
 
 initialize();

 while(1) {
 printf("1. Join\n");
 printf("2. Print information\n");
 printf("3. GIVE ME FLAG!\n");
 printf("> ");
 scanf("%d", &idx);
 switch(idx) {
 case 1:
 printf("Name: ");
 read(0, my_page.name, sizeof(my_page.name));

 printf("Age: ");
 scanf("%d", &my_page.age);
 break;
 case 2:
 printf("Name: %s\n", my_page.name);
 printf("Age: %d\n", my_page.age);
 break;
 case 3:
 fp = fopen("/flag", "r");
 fread(flag_buf, 1, 56, fp);
 break;
 default:
 break;
 }
 }

}%

The key vulnerability is here

read(0, my_page.name, sizeof(my_page.name));

The size of my_page.name is 16 bytes, but read() does not automatically add the null byte \0.

However, when printing, it is done like this.

printf("Name: %s\n", my_page.name);

%s continues printing until the end of the string is reached. In other words, if there is no \0 after my_page.name, the memory at the back of the stack can be continuously read and output.

attack flow

The important thing is to load the flag into memory first.

case 3:

fp = fopen("/flag", "r");

fread(flag_buf, 1, 56, fp);

break;

If you press 3 times, the contents of /flag are entered into flag_buf.

However, it does not print directly.

Next, if you enter the name in Join number 1 with a full 16 bytes, \0 will not be added.

After that, if you select Print information twice,

printf("Name: %s\n", my_page.name);

Therefore, starting from my_page.name, the rear stack memory is continuously output until \0 appears. In the process, the flag in flag_buf may leak out.

So the input is:

> 3

> 1

Name: AAAAAAAAAAAAAAAA

Age: 1094795585

> 2

You may be curious about the age value here, but the age value must be entered as a value without null bytes. (Even if the input is received separately, age is attached right after the name in memory)

The structure looks like this.
struct my_page {
char name[16];
int age;
};
Then the memory layout usually goes like this.
my_page.name[16] | my_page.age[4]
Looking more closely:
offset 0x00 ~ 0x0f : name[16]
offset 0x10 ~ 0x13: age

For example, 1234 can be stored in memory like this:

d2 04 00 00

If a 00 null byte is entered here, the output of %s may be cut off there.

For example:

1094795585

This value is in hex:

0x41414141

It goes into memory like "AAAA" and there is no \0 in the middle. So a better value is 1094795585.
