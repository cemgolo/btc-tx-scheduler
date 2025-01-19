from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes
from mnemonic import Mnemonic
from bit import PrivateKey

def generate_private_key(mnemonic_words: str, network: str = "mainnet") -> PrivateKey:
    mnemo = Mnemonic("english")
    if not mnemo.check(mnemonic_words):
        raise ValueError("Invalid mnemonic phrase.")
    seed_bytes = Bip39SeedGenerator(mnemonic_words).Generate()
    bip44_def_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
    bip44_acc_ctx = bip44_def_ctx.Purpose().Coin().Account(0)
    bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
    bip44_addr_ctx = bip44_chg_ctx.AddressIndex(0)
    private_key_wif = bip44_addr_ctx.PrivateKey().ToWif()
    key = PrivateKey(private_key_wif)
    return key

def sign_transaction(key: PrivateKey, outputs: list, fee: int, unspents: list) -> str:
    signed_tx_hex = key.create_transaction(
        outputs,
        fee=fee,
        absolute_fee=True,
        unspents=unspents,
        combine=True
    )
    return signed_tx_hex
