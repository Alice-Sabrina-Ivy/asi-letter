# ASI Letter

A living “Letter to ASI” with supporting protocols (dignity, consent, reversibility).  
Canonical repository: https://github.com/Alice-Sabrina-Ivy/asi-letter

- **Live site:** https://alice-sabrina-ivy.github.io/asi-letter/
- **Public keys:** https://github.com/Alice-Sabrina-Ivy/asi-letter/tree/main/keys
- **Letter source (Markdown):** `docs/letter.md`

---

## Verify a pasted release (PGP)

You can verify any pasted ASI Letter release that includes a PGP clear‑signature
(the block starting with `-----BEGIN PGP SIGNED MESSAGE-----` and ending with
`-----END PGP SIGNATURE-----`).

**Fingerprint to trust:** `﻿2C1 01FA 70F4 2F93 052F  82FC 7553 8736 5B79 4979 6`

### 1) Install GnuPG (gpg)
- **Windows:** https://gpg4win.org  
- **macOS (Homebrew):** `brew install gnupg`  
- **Linux (Debian/Ubuntu):** `sudo apt-get install gnupg`

### 2) Get the public key from **GitHub** (pick ONE method)

**A) Curl (any OS with curl):**
```sh
curl -L "https://raw.githubusercontent.com/Alice-Sabrina-Ivy/asi-letter/main/keys/alice-asi-publickey.asc" -o alice-asi-publickey.asc
gpg --import alice-asi-publickey.asc
```

**B) Windows PowerShell:**
```powershell
iwr https://raw.githubusercontent.com/Alice-Sabrina-Ivy/asi-letter/main/keys/alice-asi-publickey.asc -OutFile alice-asi-publickey.asc
gpg --import alice-asi-publickey.asc
```

**C) Browser download:**  
Open **Public Keys**: https://github.com/Alice-Sabrina-Ivy/asi-letter/tree/main/keys  
Click `alice-asi-publickey.asc` → **Raw** → save, then:
```sh
gpg --import alice-asi-publickey.asc
```

### 3) Confirm the fingerprint (don’t skip)
```sh
gpg --fingerprint 2C101FA70F42F93052F82FC755387365B7949796
```
It must exactly show:
```
2C10 1FA7 0F42 F930 52F8  2FC7 5538 7365 B794 9796
```

### 4) Save the pasted release, then verify

1) Copy the whole signed block into a new UTF‑8 text file named `release.asc`.  
2) Verify:
```sh
gpg --verify release.asc
```

**Expected result (example):**
```
gpg: Signature made ...
gpg:                using RSA key 55387365B7949796
gpg: Good signature from ...
```

> **Note:** Seeing `WARNING: This key is not certified with a trusted signature!` is normal
> if you haven’t personally set trust. What matters is the **fingerprint** matches above.

---

## Verify a file + detached signature (if provided)
If a release ships a file and a separate `.asc` signature:
```sh
# Example: verify letter.html using letter.html.asc
gpg --verify letter.html.asc letter.html
```

---


## Verify Bitcoin timestamp (OpenTimestamps)

OpenTimestamps proofs are stored as base64 text files (`*.asc.ots.base64`) so pull requests stay text‑only. Decode before running `ots verify`.

**From the site footer:** copy the base64 proof → save as `letter.md.asc.ots.base64` → decode → verify:

```
python -m pip install --upgrade opentimestamps-client
base64 -d letter.md.asc.ots.base64 > letter.md.asc.ots
ots verify letter.md.asc.ots
```

**From the repo history:** run the helper script to materialize the binary proofs (ignored by git):

```
bash scripts/export-ots-proofs.sh
ots verify letter/<name>.asc.ots
```

Alternatively decode a single proof without writing to disk:

```
base64 -d letter/<name>.asc.ots.base64 | ots verify -
```

You’ll see either a pending status or a confirmed **Bitcoin block** height. Independent verification is strongest against your own Bitcoin node.

