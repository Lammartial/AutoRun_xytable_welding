import base64
import pickle
from pathlib import Path
from binascii import unhexlify
from Cryptodome.Cipher import AES
from Cryptodome.Random import get_random_bytes
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


#--------------------------------------------------------------------------------------------------

def encrypt(raw, key_idx: int) -> bytes:
    """
    Encrypts the given plaintext "raw" by using the
    key number "key_idx" of our keyring and returns the encrypted bytes.

    Args:
        raw (_type_): _description_
        key_idx (int): Number of key of keyring to use; 0 .. len(keyring)

    Returns:
        bytes: encrypted bytes representing raw input

    """

    with open(Path(__file__).parent / "rok.bin", "rb") as file:
        keyring = pickle.loads(file.read())
    assert((key_idx is not None) and (key_idx < len(keyring)))
    BS = AES.block_size
    pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
    raw = base64.b64encode(pad(raw).encode('utf8'))
    iv = get_random_bytes(AES.block_size)
    __key__ = unhexlify(keyring[key_idx])
    cipher = AES.new(key=__key__, mode= AES.MODE_CFB,iv= iv)
    return base64.b64encode(iv + cipher.encrypt(raw))

#--------------------------------------------------------------------------------------------------

def decrypt(enc, key_idx: int) -> str:
    """Decrypts an encrypted input by using the secret from keyring, number "key_idx".

    Args:
        enc (_type_): _description_
        key_idx (int): Number of key of keyring to use; 0 .. len(keyring)

    Raises:
        UnicodeDecodeError or binascii.Error
            if wrong key is used as the decoding to string does not work.

    Returns:
        str: Plaintext or crap if wrong key is used.

    """
    with open(Path(__file__).parent / "rok.bin", "rb") as file:
        keyring = pickle.loads(file.read())
    assert((key_idx is not None) and (key_idx < len(keyring)))
    unpad = lambda s: s[:-ord(s[-1:])]
    enc = base64.b64decode(enc)
    iv = enc[:AES.block_size]
    __key__ = unhexlify(keyring[key_idx])
    cipher = AES.new(__key__, AES.MODE_CFB, iv)
    return unpad(base64.b64decode(cipher.decrypt(enc[AES.block_size:])).decode('utf8'))

#---------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("keyidx", type=int, choices=range(0,10), metavar="[0-9]", help="Index of key to use.")
    parser.add_argument("text", type=str, help="Plaintext to encrypt or encrypted input to decrypt.")
    parser.add_argument("--decrypt", action="store_true", help="If set, the text is encrpted and should be unencrypted.")
    args = parser.parse_args()

    if args.decrypt:
        print(decrypt(args.text, args.keyidx))
    else:
        print(encrypt(args.text, args.keyidx))

# END OF FILE
