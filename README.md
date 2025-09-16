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

OpenTimestamps proofs are stored as base64 text files (`*.asc.ots.base64`) so pull requests stay text-only. Follow these steps to independently confirm the Bitcoin timestamp.

### 1) Install the OpenTimestamps client

Requires Python 3.8+. Upgrade an existing install if prompted.

- **Windows (PowerShell):**
  ```powershell
  py -m pip install --upgrade opentimestamps-client
  ```
- **macOS / Linux:**
  ```sh
  python3 -m pip install --upgrade opentimestamps-client
  ```

### 2) Obtain the base64 proof (choose ONE)

**A) From the site footer:**
1. Copy the base64 OpenTimestamps proof from the site footer.
2. Paste it into a new UTF-8 text file named `letter.md.asc.ots.base64`.

**B) From the repo history:**
1. Export the binary proofs locally (they’re ignored by git):
   ```sh
   bash scripts/export-ots-proofs.sh
   ```
2. Use the matching file under `letter/` (for example `letter/letter.md.asc.ots`).

### 3) Decode the proof to a binary `.ots` file

- **macOS / Linux:**
  ```sh
  base64 -d letter.md.asc.ots.base64 > letter.md.asc.ots
  ```
- **Windows (PowerShell):**
  ```powershell
  certutil -decode letter.md.asc.ots.base64 letter.md.asc.ots
  ```

> **Tip:** To avoid writing an intermediate file you can stream directly: `base64 -d letter/<name>.asc.ots.base64 | ots verify -`.

### 4) Verify the timestamp

> **Windows note:** `pip` installs `ots.exe` to `%APPDATA%\Python\Python3x\Scripts\`, which usually isn’t on your `PATH`.
> Choose either option below before running the generic command.
>
> 1. Add the Scripts directory to `PATH`: `py -m site --user-base` prints the base
>    path, so append `\Scripts` to that location (for example
>    `%APPDATA%\Python\Python312\Scripts\`) and add it to your PATH environment
>    variable.
> 2. Invoke the tool with its full path each time:
>    ```powershell
>    & "$env:APPDATA\Python\Python312\Scripts\ots.exe" verify letter.md.asc.ots
>    ```
>
> The commands below assume `ots` is already on your `PATH`.

```sh
ots verify letter.md.asc.ots
```

**Expected result (example):**
```
OK   bitcoin block 827000
```

- If the output says `Unknown` or `Pending`, the timestamp hasn’t been confirmed on-chain yet—re-run later or against your own Bitcoin node for the strongest assurance.

