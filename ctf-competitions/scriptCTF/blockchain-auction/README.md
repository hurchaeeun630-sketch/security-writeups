# Auction | NoobMaster

- Description: Just win the auction. 

auction.zip: /attachments/auction.zip

# Write-up

Vulnerability 1: By funding the NoobMaster PDA before it is initialized (via `initialize_bidder`), the PDA would get an already initialized error (because of the lamports check). This causes NoobMaster's bid to fail, since the data expected by the `bid` function is not written on the PDA.

However, we are still not able to bid anything, because NoobMaster PDA has not bid yet.

Vulnerability 2: Call initialize again, with non-canonical bumps (for vault and winner PDAs). This allows us the call to `initialize()` to pass, setting us as the first bidder, and we can bid!

Note: While bidding, the winner PDA provided should be the one with canonical bump, because that's the one the server checks for.

Solve contract and script at `/src/solve/`

# Flag - scriptCTF{7h3_0nly_b1dd3r}

## Security Analysis

The exploit combines two state-management mistakes. First, the program assumes that a funded PDA must already contain valid initialized state. Sending lamports to the expected bidder PDA before `initialize_bidder` runs makes initialization fail, leaving NoobMaster unable to create the state later required by `bid`. Second, the initialization routine accepts caller-selected bump values instead of deriving and checking the canonical PDAs. This allows a parallel set of vault and winner accounts to satisfy initialization while avoiding the state expected by the challenge's automated bidder.

The order of operations matters: pre-fund the canonical bidder PDA, initialize the attacker-controlled state with non-canonical bumps, submit the first valid bid, and use the canonical winner PDA for the final server-side check. This distinction between accounts accepted by the program and accounts later inspected by the harness is the core of the solution.

## Defensive Lessons

- Derive PDAs inside the program and enforce canonical bumps with Anchor constraints.
- Validate account ownership, discriminators, seeds, and expected state transitions independently of lamport balance.
- Treat account initialization and business logic as one explicit state machine.
- Ensure that the verification harness checks the same account identities used by the program.
