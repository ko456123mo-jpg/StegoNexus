# Usage Policy

## In one line

StegoNexus is a **defensive analysis and teaching tool**. Use it only on
files and systems **you own or are authorized to analyze in writing**.

## Allowed

| Use | |
|---|---|
| Forensic triage of your own files or evidence | ✅ |
| Authorized incident-response or internal investigation work | ✅ |
| Academic research and teaching in an isolated lab | ✅ |
| CTF and training exercises on provided artifacts | ✅ |
| Detecting steganography / covert channels in traffic you own | ✅ |

## Prohibited

| Use | |
|---|---|
| Analyzing files or traffic you have no authorization for | ❌ |
| Any offensive, extortionate, or harmful application | ❌ |
| Publishing another client's case data | ❌ |
| Running malware specimens (the tool never does, and neither should you) | ❌ |
| Exposing the network channel beyond loopback / RFC1918 | ❌ |

## When working for a client

Obtain in writing, before starting:

1. Identity and authority of the party owning the artifact
2. Explicit scope (file hashes / case ID / package name)
3. Authorization period and expiry date
4. A named technical contact
5. Confirmation that the analysis will run on a copy they are aware of

## Evidence handling

- Original evidence is treated as **read-only**; all operations run on derived copies.
- Every action is written to an audit trail tied to the case.
- Hashes (MD5 · SHA-1 · SHA-256 · SHA-512) and chain-of-custody records are produced per case.
- Delete client artifacts after the engagement unless agreed otherwise.
- Sample cases shipped or generated are labelled **TRAINING CASE — SYNTHETIC DATA**.

## No forensic certification

This tool produces **technical analysis**, not an expert certification admissible
before a court. Courts require licensed expert testimony; use this output as
technical input to your own licensed examiner.

## Disclaimer

Provided "as is" under the MIT License, without warranty of any kind. The author
is not liable for misuse or for any direct or indirect damage. **Legal compliance
is the sole responsibility of the user.**
