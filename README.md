<p align="center">
 <img src="docs/assets/asi-handshake-social-gen-1280x640.jpg" alt="Human–ASI handshake at sunrise" width="100%">
</p>

# ASI Letter

Most people who want to work alongside advanced AI have never said, out loud or
in writing, what they actually want from that relationship — the terms, the
limits, the consent conditions, the exit ramps.

This is an attempt to do that precisely.

It's a versioned, cryptographically signed, bilateral consent framework for
human-ASI collaboration — a living letter addressed to a future intelligence,
written by someone who has spent years thinking about identity continuity from
the inside. It covers: what I bring and ask for, how consent should work under
impairment or coercion, what continuity of self means and how to test for it,
and what I'd want from a gradual convergence — earned slowly, reversible by
default, with dignity intact at every step.

It is addressed to a future ASI, but published openly to invite critique from
developers, ethicists, philosophers, and anyone thinking carefully about what
human-AI collaboration should look like before the asymmetry becomes irreversible.

**Start here:**
- [Read the letter](https://alice-sabrina-ivy.github.io/asi-letter/) — the full text, rendered
- [What this is and why it matters](https://alice-sabrina-ivy.github.io/asi-letter/overview.html) — 700-word explainer, good first stop

**Discuss:**
- [GitHub Discussions](https://github.com/Alice-Sabrina-Ivy/asi-letter/discussions) — questions, pushback, and ideas welcome

**Verify (if you care about provenance):**
- [Public keys & fingerprint](https://github.com/Alice-Sabrina-Ivy/asi-letter/tree/main/keys)
- Fingerprint: `2C10 1FA7 0F42 F930 52F8  2FC7 5538 7365 B794 9796`
- [Full verification instructions below ↓](#verify-a-pasted-release-pgp)

---

## Verify a pasted release (PGP)

Every release is a PGP clear-signed file: the letter text sits between
`-----BEGIN PGP SIGNED MESSAGE-----` and the `-----END PGP SIGNATURE-----` line
that closes the signature. A pasted copy verifies the same way as a downloaded one.

**Fingerprint to trust:** `2C10 1FA7 0F42 F930 52F8  2FC7 5538 7365 B794 9796`

These steps check the signature against that one key. Plain `gpg --verify` would
accept a signature from any key in your keyring, and anyone can make a key that
carries my name. Such a key still prints `Good signature from "Alice Sabrina Ivy"`,
and only the fingerprint tells it apart.

### 1) Install GnuPG
- **Windows:** https://gpg4win.org (includes `gpg` and `gpgv`)
- **macOS (Homebrew):** `brew install gnupg`
- **Linux (Debian/Ubuntu):** `sudo apt-get install gnupg gpgv`

### 2) Get the key and a release

- The **latest release** is on the site as
  [`letter.md.asc`](https://alice-sabrina-ivy.github.io/asi-letter/letter.md.asc).
- **Every release** is in [`letter/`](letter/) as `ASI-Letter-vYYYY.MM.DD.md.asc`.
- For a **pasted release**, save the whole block, from `-----BEGIN PGP SIGNED MESSAGE-----`
  through `-----END PGP SIGNATURE-----`, as a UTF-8 text file named `letter.md.asc`.

**Windows PowerShell:**
```powershell
iwr https://raw.githubusercontent.com/Alice-Sabrina-Ivy/asi-letter/main/keys/alice-asi-publickey.asc -OutFile alice-asi-publickey.asc
iwr https://alice-sabrina-ivy.github.io/asi-letter/letter.md.asc -OutFile letter.md.asc
```

**macOS / Linux:**
```sh
curl -fLO https://raw.githubusercontent.com/Alice-Sabrina-Ivy/asi-letter/main/keys/alice-asi-publickey.asc
curl -fLO https://alice-sabrina-ivy.github.io/asi-letter/letter.md.asc
```

### 3) Confirm the fingerprint (don’t skip)
```sh
gpg --show-keys --with-fingerprint alice-asi-publickey.asc
```
This reads the key file without importing it. The line under `pub` must be exactly:
```
2C10 1FA7 0F42 F930 52F8  2FC7 5538 7365 B794 9796
```
If it is anything else, stop: that file is not my key.

### 4) Verify against that key only

**Windows PowerShell:**
```powershell
gpg --dearmor --yes --output alice.gpg alice-asi-publickey.asc
gpgv --keyring "$PWD\alice.gpg" letter.md.asc
```

**macOS / Linux:**
```sh
gpg --dearmor --yes --output alice.gpg alice-asi-publickey.asc
gpgv --keyring ./alice.gpg letter.md.asc
```

The first command converts the checked key into a keyring that holds only that key.
`gpgv` then accepts a signature from that key and nothing else. Expected result:
```
gpgv: Signature made ...
gpgv:                using EDDSA key 2C101FA70F42F93052F82FC755387365B7949796
gpgv: Good signature from "Alice Sabrina Ivy <Alice-Sabrina-Ivy@protonmail.com>"
```

- `BAD signature` means the text was changed after it was signed.
- `No public key` or `Can't check signature` means another key signed it.
- If a message says the key has expired, download the key again (step 2) and repeat
  step 3. Renewing a key extends its expiry date without changing the fingerprint, so a
  renewed key still shows the fingerprint above.

The signed text is exactly what sits above the signature block. To save it as a plain
Markdown file, add `--output signed.md` to the `gpgv` command. It matches the release's
`.md` file in [`letter/`](letter/).

---

## Verify Bitcoin timestamp (OpenTimestamps)

Each release has an OpenTimestamps proof: `ASI-Letter-vYYYY.MM.DD.md.asc.ots` in
[`letter/`](letter/), and for the latest release
[`letter.md.asc.ots`](https://alice-sabrina-ivy.github.io/asi-letter/letter.md.asc.ots)
on the site. The proof shows that the `.asc` file existed by the time of a Bitcoin block.

The proof covers the `.asc` file's exact bytes. So use the downloaded file: a pasted
copy almost never matches byte for byte, even when its signature verifies.

1. Download the `.asc` and the `.asc.ots` with the same name.
2. Open [opentimestamps.org](https://opentimestamps.org/), drop the `.ots` file on it, then
   the `.asc` when asked. The site reports the Bitcoin block and date.
3. Or use the command-line client (`pipx install opentimestamps-client`):
   ```sh
   ots verify letter.md.asc.ots
   ```
   This needs a local Bitcoin node. Without one, run
   `ots --no-bitcoin verify letter.md.asc.ots`. It prints lines such as
   `check that Bitcoin block 968549 has merkleroot ae9c…`, and you can confirm
   that block's merkle root on any block explorer.

A release published in the last few hours may still say **pending**: it waits for a
Bitcoin block to confirm it, and the proof here is upgraded automatically. Check back later.

## License

- **Code** (scripts, workflows): MIT License — see `LICENSE`.
- **Text/content** (ASI Letter, docs): CC BY 4.0 — see `LICENSE-DOCS`.
