# dreamhack.io Reversing Basic Challenge #6

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224286480790). Translated and reformatted in English.

1. Problem overview

This problem is a reverse engineering problem that finds the correct input value by analyzing the executable file with IDA. After the program receives a string from the user, it checks whether the input value is correct through an internal verification function.

If the input value is correct, Correct is output, and if it is incorrect, Wrong is output.

2. Main function analysis

If you check the main function in IDA, you can see the following code structure.

int __fastcall main(int argc, const char **argv, const char **envp)
{
 char v4[256]; // [rsp+20h] [rbp-118h] BYREF

 memset(v4, 0, sizeof(v4));
 sub_1400011B0("Input : ", argv, envp);
 sub_140001210("%256s", v4);

 if ( (unsigned int)sub_140001000(v4) )
 puts("Correct");
 else
 puts("Wrong");

 return 0;
}

Looking at the code above, the program first creates a 256-byte buffer called v4 and initializes it to 0 using memset.

After that, the string "Input: " is output and the user input is saved in v4 through sub_140001210("%256s", v4);

The most important part is the following code:

if ( (unsigned int)sub_140001000(v4) )
 puts("Correct");
else
 puts("Wrong");

In other words, the input value v4 is passed to the sub_140001000 function, and if this function returns 1, Correct is output, and if it returns 0, Wrong is output.

Therefore, the key is to analyze how the sub_140001000 function verifies the input value.

3. Verification function analysis

If you check the sub_140001000 function in IDA, you will see the following code.

__int64 __fastcall sub_140001000(__int64 a1)
{
 int i; // [rsp+0h] [rbp-18h]

 for ( i = 0; (unsigned __int64)i < 0x12; ++i )
 {
 if ( byte_140003020[*(unsigned __int8 *)(a1 + i)] != byte_140003000[i] )
 return 0LL;
 }

 return 1LL;
}

This function checks the first 18 bytes of the input value. Here, 0x12 is 18 in decimal.

In other words, the loop statement is executed 18 times as follows. The verification conditions are interpreted as follows.

byte_140003020[input[i]] == byte_140003000[i]

If even one thing is different, 0 is immediately returned, and if all 18 bytes satisfy the condition, 1 is returned.

Therefore, in order to find the input value, you must find at what index each value of byte_140003000 is located in the byte_140003020 array. If you convert the index value to a character, it becomes the correct answer string.

4. Solution idea

The conditions of the verification function are as follows.

byte_140003020[input[i]] == byte_140003000[i]

Thinking of this in reverse, it is as follows.

input[i] = index of byte_140003000[i] in byte_140003020

In other words, you just need to find what position the byte_140003000[i] value is in byte_140003020 array.

For example, if the value of byte_140003000[0] is 0x00, and 0x00 is at the 0x52nd position in the byte_140003020 array, the first input character will be ASCII 0x52, that is, 'R'.

By repeating this process 18 times, you can get the entire correct answer string.

Because IDA's Script command window was configured for IDC, the recovery logic was implemented with the following IDC script.

auto target, table, answer, i, b, j;

answer = "";

for (i = 0; i < 0x12; i++)
{
 b = Byte(0x140003000 + i);

 for (j = 0; j < 0x100; j++)
 {
 if (Byte(0x140003020 + j) == b)
 {
 answer = answer + sprintf("%c", j);
 break;
 }
 }
}

Message("%s\n", answer);

The end!
