# Solana Verifiable Simulation Proofs (Playground Setup)

This folder contains the artifacts for the Solana-based "Verifiable Simulation Proofs".

## 1. Anchor Program Code

Copy and paste this code into [Solana Playground](https://beta.solpg.io).

```rust
use anchor_lang::prelude::*;

declare_id!("B3BSjdSyKkteD8vGEoszeRK33WgDwjbzJP3cBaRvY17f");

#[program]
pub mod genesis_proof {
    use super::*;

    pub fn commit_checkpoint(
        ctx: Context<CommitCheckpoint>,
        episode_fingerprint: [u8; 32],
        merkle_root: [u8; 32],
        checkpoint_index: u32,
        day: u32,
        leaf_count: u32,
    ) -> Result<()> {
        let checkpoint = &mut ctx.accounts.checkpoint;
        checkpoint.merkle_root = merkle_root;
        checkpoint.episode_fingerprint = episode_fingerprint;
        checkpoint.checkpoint_index = checkpoint_index;
        checkpoint.day = day;
        checkpoint.leaf_count = leaf_count;
        checkpoint.authority = ctx.accounts.authority.key();
        checkpoint.slot = Clock::get()?.slot;
        
        Ok(())
    }
}

#[derive(Accounts)]
#[instruction(episode_fingerprint: [u8; 32], merkle_root: [u8; 32], checkpoint_index: u32)]
pub struct CommitCheckpoint<'info> {
    #[account(
        init,
        payer = authority,
        space = 8 + 32 + 32 + 4 + 4 + 4 + 32 + 8,
        seeds = [b"genesis_proof", episode_fingerprint.as_ref(), &checkpoint_index.to_le_bytes()],
        bump
    )]
    pub checkpoint: Account<'info, Checkpoint>,
    #[account(mut)]
    pub authority: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[account]
pub struct Checkpoint {
    pub episode_fingerprint: [u8; 32],
    pub merkle_root: [u8; 32],
    pub checkpoint_index: u32,
    pub day: u32,
    pub leaf_count: u32,
    pub authority: Pubkey,
    pub slot: u64,
}
```

## 2. Deployment Steps

1.  **Open [Solana Playground](https://beta.solpg.io).**
2.  Create a new Anchor project named `genesis_proof`.
3.  Paste the code above into `lib.rs`.
4.  **Build:** Click the "Build" button (hammer icon).
5.  **Deploy:**
    *   Switch to "Devnet" in the bottom left.
    *   Ensure you have SOL (use the Playground faucet button or `solana airdrop 2` in the terminal).
    *   Click "Deploy".
6.  **Export IDL:**
    *   After deployment, go to the "Build & Deploy" tab.
    *   Click "Export IDL" and save it as `blockchain/solana/idl/genesis_proof.json` in this repository.
7.  **Program ID:** Copy the "Program Id" and add it to your `.env` file as `GENESIS_SOLANA_PROGRAM_ID`.

## 3. Environment Variables

Create a `.env` file in the root (or update your existing one) with:

```bash
GENESIS_SOLANA_RPC_URL=https://api.devnet.solana.com
GENESIS_SOLANA_PROGRAM_ID=YOUR_PROGRAM_ID_FROM_PLAYGROUND
GENESIS_SOLANA_KEYPAIR_JSON=[...] # Exported from Playground (Settings -> Export Wallet)
```

## 4. Verification

You can verify the committed proofs on [Solana Explorer](https://explorer.solana.com/?cluster=devnet) by searching for the checkpoint PDA or the transaction signature returned by the `commit_simulation_proof` tool.
