# ASI Letter

Central, signed, versioned home for Alice Sabrina Ivy’s **Letter to ASI** and related tooling.

## Authenticity (clear-signed, copy-paste friendly)
The canonical release is a single **OpenPGP clear-signed** text block (`.asc`) so it can be pasted anywhere—even text-only sites—and still verify.

- **Public key fingerprint (expected):** `2C101FA70F42F93052F82FC755387365B7949796` (also stored in `keys/FINGERPRINT`)
- **Key material:** `keys/alice-asi-publickey.asc` (armored OpenPGP public key)

### Verify a pasted release
```bash
gpg --import keys/alice-asi-publickey.asc
gpg --verify letter/ASI-Letter-vYYYY.MM.DD.md.asc
# Confirm the key fingerprint equals the one in keys/FINGERPRINT
```
