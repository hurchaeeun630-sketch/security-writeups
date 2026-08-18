# dreamhack.io: Sigreturn-Oriented Programming (SROP)

> Originally published on [Naver Blog](https://blog.naver.com/chaeeunhur630/224325124965). Translated and reformatted in English.

In the past, shellcode was executed directly and system calls were made.

However, with the advent of NX, code execution in data areas such as stack/heap was blocked.

So the attackers developed the following approach:

Execute shellcode

→ Blocked by NX → RTL (Return-to-Libc) → ROP (Return-Oriented Programming) → SROP (SigReturn-Oriented Programming)

SROP is a ROP-based technique that exploits Linux’s signal processing process.

Signal is an “event notification” sent to a process. For example:

Signal

meaning

SIGINT

Enter Ctrl+C

SIGSEGV

Invalid memory access

SIGALRM

alarm time out

SIGKILL

force quit

SIGCHLD

kill child process

The operating system is largely divided into two areas.

User Mode: Area where general programs run

Kernel Mode: Area where the OS kernel runs

The program normally runs in User Mode. However, when a signal occurs, the kernel must intervene.

Signal generation → Enter Kernel Mode → Kernel prepares for signal processing → Return to User Mode → Execute registered Signal Handler

The important point is: To handle a signal, the kernel needs to save and restore the current process's registers, stack state, etc.

Kernel internal signal processing flow

The main flow from the lecture is this.

Signal generation

→ do_signal()

→ get_signal()

→ handle_signal()

→ setup_rt_frame()

→ Return to User Mode

→ Run Signal Handler

A quick look at what each function does:

function

role

do_signal() / arch_do_signal_or_restart()

Signal processing starting point

get_signal()

Check if there is a signal to process

handle_signal()

Preparing to run the actual Signal Handler

setup_rt_frame()

Configuring Signal Frame in User Stack

sigreturn

Return to original state after signal processing

Why setup_rt_frame is important

To run the Signal Handler, the kernel must store this information.

Current RIP/EIP

Current RSP/ESP

register values

Signal information

original execution location

This information is stored in the User Stack, and this structure is usually referred to as a Signal Frame. setup_rt_frame() creates this Signal Frame.

To put it simply: the kernel stores the current process state in the stack and returns to this state when the signal handler ends.

sigreturn is a system call to return to the original execution state after the signal handler ends.

If a signal comes while the program is running:

→ Signal generation

→ Kernel intervenes

→ Save current register/stack state

→ Run Signal Handler

→ call sigreturn

→ Restore saved state

→ Return to the original code

In other words, the role of sigreturn is to read the CPU state stored in the stack and restore the registers.

Context Switching refers to changing the running state.

For example:

Run an existing program

→ Signal generation

→ Execute kernel code

→ Execute signal handler

→ Return to the original program

At this time, the kernel must not forget the existing state. So, the information of the following other registers is stored. So, in fact, it can be said that sigreturn is due to context switching.
