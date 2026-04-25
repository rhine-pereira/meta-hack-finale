import os
import json
from typing import Optional, List, Dict, Any
from hashlib import sha256
from dotenv import load_dotenv

# Solana proof support is optional: most users only need the environment + training.
# On Colab/Windows, Solana python packages can conflict with the httpx/websockets
# requirements of openenv-core/fastmcp. So we import lazily and degrade gracefully.
_SOLANA_IMPORT_ERROR: Optional[str] = None
try:
    import base58  # noqa: F401
    from solders.keypair import Keypair  # type: ignore
    from solders.pubkey import Pubkey  # type: ignore
    from solders.system_program import ID as SYS_PROG_ID  # type: ignore
    from solders.instruction import Instruction, AccountMeta  # type: ignore
    from solana.rpc.async_api import AsyncClient  # type: ignore
    from solana.rpc.commitment import Confirmed  # type: ignore
    from solana.transaction import Transaction  # type: ignore
    from solana.rpc.types import TxOpts  # type: ignore
except Exception as e:  # pragma: no cover
    _SOLANA_IMPORT_ERROR = str(e)
    Keypair = None  # type: ignore
    Pubkey = None  # type: ignore
    SYS_PROG_ID = None  # type: ignore
    Instruction = None  # type: ignore
    AccountMeta = None  # type: ignore
    AsyncClient = None  # type: ignore
    Confirmed = None  # type: ignore
    Transaction = None  # type: ignore
    TxOpts = None  # type: ignore

# Load env vars
load_dotenv()

IDL_PATH = os.path.join(os.path.dirname(__file__), "../../blockchain/solana/idl/genesis_proof.json")

class SolanaProofClient:
    def __init__(self):
        self.rpc_url = os.getenv("GENESIS_SOLANA_RPC_URL", "https://api.devnet.solana.com")
        self.program_id_str = os.getenv("GENESIS_SOLANA_PROGRAM_ID")
        self.keypair_json = os.getenv("GENESIS_SOLANA_KEYPAIR_JSON")
        self.commitment = os.getenv("GENESIS_SOLANA_COMMITMENT", "confirmed")
        
        if Pubkey is None:
            self.program_id = None
        else:
            self.program_id = Pubkey.from_string(self.program_id_str) if self.program_id_str else None
        self.payer = self._load_keypair()
        
    def _load_keypair(self) -> Optional[Keypair]:
        if Keypair is None:
            return None
        if not self.keypair_json:
            return None
        try:
            secret = json.loads(self.keypair_json)
            return Keypair.from_bytes(bytes(secret))
        except Exception as e:
            print(f"Error loading Solana keypair: {e}")
            return None

    def is_configured(self) -> bool:
        # Must have deps + env configuration.
        if _SOLANA_IMPORT_ERROR is not None:
            return False
        return all([self.program_id, self.payer, self.rpc_url])

    def get_episode_fingerprint(self, episode_id: str, seed: int) -> bytes:
        """Derives a stable 32-byte fingerprint for an episode."""
        payload = f"{episode_id}:{seed}".encode('utf-8')
        return sha256(payload).digest()

    def derive_checkpoint_pda(self, episode_fingerprint: bytes, checkpoint_index: int) -> Pubkey:
        """Derives the PDA for a specific checkpoint."""
        if Pubkey is None or self.program_id is None:
            raise RuntimeError("Solana dependencies not available (cannot derive PDA).")
        seeds = [
            b"genesis_proof",
            episode_fingerprint,
            checkpoint_index.to_bytes(4, 'little')
        ]
        pda, _ = Pubkey.find_program_address(seeds, self.program_id)
        return pda

    async def commit_checkpoint(
        self,
        episode_id: str,
        seed: int,
        merkle_root: bytes,
        checkpoint_index: int,
        day: int,
        leaf_count: int
    ) -> Dict[str, Any]:
        if not self.is_configured():
            if _SOLANA_IMPORT_ERROR is not None:
                return {
                    "success": False,
                    "error": (
                        "Solana proof dependencies are not installed or incompatible. "
                        f"Import error: {_SOLANA_IMPORT_ERROR}"
                    ),
                }
            return {"success": False, "error": "Solana not configured in .env"}

        episode_fingerprint = self.get_episode_fingerprint(episode_id, seed)
        checkpoint_pda = self.derive_checkpoint_pda(episode_fingerprint, checkpoint_index)
        
        # Anchor instruction discriminator for "commit_checkpoint"
        # sighash("global:commit_checkpoint")
        sighash_input = "global:commit_checkpoint"
        discriminator = sha256(sighash_input.encode('utf-8')).digest()[:8]
        
        # Data layout (Borsh):
        # episode_fingerprint [u8; 32]
        # merkle_root [u8; 32]
        # checkpoint_index u32
        # day u32
        # leaf_count u32
        data = (
            discriminator +
            episode_fingerprint +
            merkle_root +
            checkpoint_index.to_bytes(4, 'little') +
            day.to_bytes(4, 'little') +
            leaf_count.to_bytes(4, 'little')
        )

        accounts = [
            AccountMeta(pubkey=checkpoint_pda, is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.payer.pubkey(), is_signer=True, is_writable=True),
            AccountMeta(pubkey=SYS_PROG_ID, is_signer=False, is_writable=False),
        ]

        instruction = Instruction(
            program_id=self.program_id,
            data=data,
            accounts=accounts
        )

        async with AsyncClient(self.rpc_url) as client:
            latest_blockhash = (await client.get_latest_blockhash()).value.blockhash
            
            tx = Transaction()
            tx.add(instruction)
            tx.recent_blockhash = latest_blockhash
            tx.sign(self.payer)
            
            try:
                # Use standard opts
                opts = TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
                res = await client.send_raw_transaction(tx.serialize(), opts)
                
                signature = str(res.value)
                return {
                    "success": True,
                    "signature": signature,
                    "pda": str(checkpoint_pda),
                    "explorer_url": f"https://explorer.solana.com/tx/{signature}?cluster=devnet"
                }
            except Exception as e:
                return {"success": False, "error": str(e)}
