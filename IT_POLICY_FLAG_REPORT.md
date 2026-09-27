# IT Security Policy Flag — Investigation Report

**Repository:** `artifactory_navigator` (LBS Artifactory Navigator)
**Origin:** https://github.com/MarkyXP/artifactory_navigator.git
**Commit examined:** `b88a45e` (tag `v1.2.20260511`)
**Date of analysis:** 2026-09-27
**Scope:** Read-only review. No code was modified.

---

## 1. Summary

This is a legitimate internal Windows desktop tool (wxPython GUI) for browsing a JFrog
Artifactory instance, with a "Document Shipping Tool" that emails signed PDFs to suppliers.

**There is no malware here.** I specifically searched for and confirmed the *absence* of:

| Malware indicator | Result |
|---|---|
| Network listeners / reverse shells (`socket`, `bind`, `listen`, `http.server`) | None |
| Persistence (registry `Run` keys, `schtasks`, startup folder, `winreg`) | None |
| Obfuscation / encoded payloads (`b64decode`, `bytes.fromhex`, `xor`, `marshal.loads`) | None |
| Dynamic code execution (`eval`, `exec`, `compile`, `__import__`, `pickle`) | None |
| Hidden window + detached process launch | **Present** (see 3.3) — but a legitimate updater, disabled |
| C2 / beaconing to attacker infrastructure | None |

The flag is **almost certainly a false positive driven by the combination of behaviours
described below** — specifically (a) a genuine embedded secret committed to the repo, and
(b) the classic static-analysis signature of *steal credentials → decrypt → hide the window
→ upload to the cloud*. Every one of those four steps is present in this code, in
`app/core/credentials.py` and `app/services/azure_storage.py`, in service of a legitimate
document-shipping workflow.

Findings are ranked by how likely each is to have triggered the policy.

---

## 2. Findings, ranked by likelihood of triggering the flag

### 2.1 CRITICAL — A real encryption key is committed to the repository
**`app/services/DSTFile`** (tracked in git, added 2025-09-19 in commit `ce36334`)

```
51795250495347475150475453765753565010554494963505550514954975348
```

- 65-character uppercase-hex blob with no file extension. This is a **DPAPI decryption key**
  (see 2.2 for how it is consumed). A bare, unlabelled high-entropy hex file sitting in the
  source tree is exactly what secret-scanning and DLP tooling flag as a hardcoded key.
- It is **shipped to end users**: `pyinstaller.spec:44` copies it next to the executable, and
  `installer.iss:51` installs it into the Program Files directory.
- Its purpose is to decrypt a real Azure Storage **account key** (see 2.2). So this is a
  live secret that grants access to the blob container holding customer shipping documents.

**Why this matters most:** the key is in git history and has been public on GitHub since
September 2025. Anyone who clones the repo can decrypt the Azure key and access the Document
Shipping Tool blob storage.

**Also note:** the README (lines 127-130) explicitly claims *"I have three secrets that I
don't want to commit anywhere public"* and lists this one. The code contradicts the
documentation. That mismatch is the kind of thing an automated review flags.

### 2.2 HIGH — PowerShell invocation to decrypt a secret, window hidden
**`app/services/azure_storage.py:40-62`**

```python
decrypt_cmd = textwrap.dedent(
    """\
    $key = Get-Content """ + key_location + """
    $data = \"""" + _encrypted_key + """\"
    $decrypted = $data | ConvertTo-SecureString -key $key | ForEach-Object {
        [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($_)) }
    $decrypted
"""
).strip()
startupinfo = subprocess.STARTUPINFO()
startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
startupinfo.wShowWindow = subprocess.SW_HIDE
result = subprocess.run(["powershell", "-Command", decrypt_cmd],
                        capture_output=True, text=True, startupinfo=startupinfo)
```

This is the single highest-signal pattern in the repository. It hits, simultaneously:

- A **string-concatenated PowerShell command** built from variables (`key_location`,
  `_encrypted_key`) — a textbook command-injection pattern to static analysis.
- `ConvertTo-SecureString -key` — the DPAPI/credential-decryption cmdlet.
- `Marshal::PtrToStringAuto` / `SecureStringToBSTR` — the low-level "reveal the plaintext
  secret" idiom.
- **A hidden window** (`STARTF_USESHOWWINDOW` + `SW_HIDE`) so the user cannot see it run.
- **Silenced output** — the plaintext key is captured into `AZURE_KEY` and never displayed.
- The result is a **full storage account key** that then authenticates to Azure Blob Storage.

Read alone, `hidden window + decrypt a secret + capture output to a variable` is the
signature of credential-stealing malware. Here it is a legitimate DPAPI unwrap of a
company-issued key, but the code makes no attempt to explain that to a reviewer or a scanner.

### 2.3 HIGH — Undisclosed telemetry: usernames and document paths leave the machine
**`app/core/telemetry.py`** (14 call sites)

```python
_client = CosmosClient(url=CONFIG.AZURE_COSMOS_ENDPOINT,
                       credential=CONFIG.AZURE_COSMOS_KEY)   # long-lived account key
_container.upsert_item({
    "id": _session_id + "_" + str(_msg_count),
    "src": "LBS_Artifactory_Navigator",
    "app_version": CONFIG.VERSION,
    "session_id": _session_id,
    "user": os.getlogin(),          # <-- Windows domain username, every event
    "msg": msg,
})
```

The concerning parts:

- **A long-lived Azure Cosmos DB account key** is used as the credential
  (`AZURE_COSMOS_KEY`). Modern policy treats full account keys as secrets; managed identity
  is expected.
- `os.getlogin()` is attached to **every** logged event. The README (line 94) claims under a
  GDPR heading: *"No personally identifiable information is collected, or any information that
  could be used to track back to a user."* **The code does the opposite** — it explicitly
  records the logged-in domain user. This is a direct documentation/implementation
  contradiction and a data-protection issue in its own right.
- Data leaves the corporate network to a **personal Azure subscription**: the endpoint in
  `app/core/config.json:8` is `https://mark.documents.azure.com:443/` — an individual's
  account, named after the developer, not a corporate tenant. Egress to a personal cloud
  tenant is a classic DLP/exfiltration trigger.
- The `user` field means the telemetry store is a **per-user activity log** tying domain
  usernames to specific document operations.
- `app/gui/explorer.py:767` logs **actual Artifactory file paths**:
  `telemetry.log(f"DST - {', '.join([str(item) for item in selected_items])}")` — i.e. the
  specific documents being shipped are recorded off-site.
- `app/services/email.py:88` ships **full stack traces** off-machine:
  `telemetry.log("ERROR:\t" + traceback.format_exc())` — which can embed internal paths,
  hostnames and repository structure.
- Every write is fired from a `run_in_background` daemon thread (`app/core/tools.py`), and
  **all exceptions are silently swallowed** and merely disable logging. A user has no way to
  know telemetry is active, and no opt-out control exists anywhere in the GUI.

### 2.4 MEDIUM — Credential harvesting and storage
**`app/core/credentials.py`**

- **Password capture** (`set_password`) — stores the Artifactory username and password.
- **Stored in the Windows credential store via `keyring`**, then **Fernet-encrypted** and
  re-blobbed into the same keyring entry (`_get_store` / `_save_store`). The Fernet key
  (`APP_SECRET`) is loaded from `.env` and baked into the distributed binary by
  `pyinstaller.spec:9`. So the encryption is defeated for anyone with the executable — they
  can decrypt every saved password.
- **Credential re-use for a different service** (`telemetry.py:29-38`): the same
  username/password the user typed for Artifactory is attached to the outbound telemetry
  session (`_session.auth = (username, pw)`) specifically *"to get through the LBS firewall"*
  (comment at `telemetry.py:31-32`). This is **sending a corporate domain password to a
  telemetry endpoint** — very likely what tripped the alert.
- `shell=True` with an f-string into a shell pipeline (`credentials.py:29-31`):
  ```python
  subprocess.check_output(f'net user {username} /domain | FIND /I "Full Name"', shell=True)
  ```
  A command-injection sink, reachable if a username is ever attacker-influenced.

### 2.5 MEDIUM — Undetected, unsigned self-updater
**`app/core/run_updater.py`**

```python
process = subprocess.Popen(
    [updater_path],                    # "af_updater.exe" - relative path
    creationflags=subprocess.CREATE_NO_WINDOW,
    startupinfo=startupinfo,           # window hidden
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,   # all output suppressed
    shell=False)
sys.exit()
```

Launches an adjacent executable **with no window, no output, and no signature or integrity
check**. `af_updater.exe` is not present in the repository and is not produced by
`pyinstaller.spec` or `installer.iss`, so its provenance is unverifiable. The call is
currently **commented out** in `main.py:2-3`, which reduces live risk, but the module ships in
the binary.

### 2.6 MEDIUM — Binary shipped without code signing
- `pyinstaller.spec:37` — `codesign_identity=None`; `strip=False`, `upx=True`.
- `installer.iss:37` — `; SignTool=signtool` is **commented out**.
- No Authenticode signature anywhere. Unsigned executables that self-extract, spawn hidden
  PowerShell and open network connections are a default quarantine trigger on managed Windows
  estates, independent of the code's actual behaviour.

### 2.7 LOW — `upx=True` packing in the build
`pyinstaller.spec:30` enables UPX compression. Packers are a standard heuristic for
packers/droppers. It is benign here (a size optimisation) but adds a detection hit.

### 2.8 LOW — Weak `pip-system-certs` truststore injection
`main.py:13` calls `pip_system_certs.wrapt_requests.inject_truststore()`, which makes the
process trust the **entire OS certificate store**. The code comment in `telemetry.py:52-54`
confirms the motivation: *"it doesn't like using my cert"* — i.e. a corporate inspection
proxy was being bypassed by swapping the Azure SDK onto a different `requests` session.
Defeating TLS inspection is a recognised control-bypass signal.

### 2.9 LOW — COM automation of Outlook
`app/services/email.py:59` — `win32.Dispatch("outlook.application")`, plus a raw
`mail._oleobj_.Invoke(*(64209, 0, 8, 0, account))` to switch sending accounts, and
`mail.Display()` to pre-populate a draft. COM-driven mail automation is flagged by most
mail-security policy sets.

### 2.10 LOW — Command injection sinks via the clipboard helper
`app/services/file_handler.py:270-283` builds a PowerShell command by interpolating **file
paths** and runs it:
```python
ps_command = f"Set-Clipboard -LiteralPath {local_path_strings}"
subprocess.run(["powershell", "-NoProfile", "-Command", ps_command], ...)
```
Paths come from Artifactory-derived names, so a crafted filename could break out of the
intended argument list.

### 2.11 LOW — Archive extraction without path sanitisation
`file_handler.py:69-70` — `zip_ref.extractall(o_path)` with no member-path validation
(Zip Slip). Minor, since source is a trusted internal Artifactory, but it is a flagged
pattern.

### 2.12 INFORMATIONAL — Commit history and repo hygiene

These do not indicate compromise, but they commonly trip heuristics and annoy reviewers:

- **`.gitignore` is ineffective.** It lists `.Notebooks/*` and `dist/*`, but 9 AI-generated
  scratch files under `tests/.Notebooks/` are nonetheless **tracked** (added before the ignore
  rule, so git keeps tracking them). Two of them, `wxtb-deepseek2.py:193` and
  `wxtb-deepseek3.py:212`, contain:
  ```python
  command = f"powershell Set-Clipboard -LiteralPath {names}"
  os.system(command)
  ```
  `os.system` with an interpolated PowerShell string is a very strong static-analysis hit,
  and it is **in the shipped repo**. The files are throwaway prototypes; their filenames
  (`wxtb-deepcoder`, `wxtb-deepseek`, `wxtb-mistral`, `wxtb-gpt4o`, `wxtb2_qwen2.5-coder`)
  also advertise unattended LLM-generated code, which some policies prohibit outright.
- **Filename contains a space and parentheses**: `tests/Assets/Complete_with_Docusign_21_4170_110_C02_B3EXP (1).zip` — a "suspicious archive" heuristic trigger.
- **Test fixtures include real signed PDFs and DocuSign ZIPs** (23 files under
  `tests/Assets/`) — genuine customer engineering documents (bond/label drawings, approval
  sheets, regulatory change assessments). Digitally signed, externally-sourced documents
  committed to a repo are a data-handling and licensing concern independent of the code.
- **CI injects secrets via shell `echo` into `.env`** (`release.yml:40-43`) — using
  `echo "KEY = `"${{ secrets.X }}`""` is the GitHub Actions secret-masking anti-pattern;
  it is quote-injection-prone and this exact idiom is flagged by many secret scanners.
- **CI runs `choco install innosetup -y`** on a self-hosted Windows runner, and the pipeline
  publishes a public GitHub Release containing the unsigned installer.
- **No code signing, no SBOM, no dependency pinning by hash** beyond `uv.lock`, and
  `requirements.txt` lists `pywin32` twice (lines 8 and 10) while omitting `keyring`,
  `msal` and `PyMuPDF` that the code actually imports.

---

## 3. The two patterns that most likely produced the alert

### 3.1 The composite credential-theft signature
Read in sequence by a scanner, these lines form a textbook chain:

```
credentials.py   capture username + password, persist encrypted
     ↓
telemetry.py     re-use those credentials to authenticate outbound to the cloud,
                 attach os.getlogin() to every event
     ↓
azure_storage.py hide a PowerShell window, decrypt a secret, capture plaintext to a variable
     ↓
Cosmos / Blob    upload the collected data to an external endpoint
```

Every individual step has a plausible business reason in this application. Together, in a
static scan, they are indistinguishable from infostealer malware.

### 3.2 The committed key
`app/services/DSTFile` is a 65-char hex blob, unlabelled, committed, and shipped to every
customer. Secret scanners identify such blobs with high confidence and with little regard
for context.

---

## 4. Suggested remediation (not applied — per your instruction)

1. **Rotate and remove the Azure storage key.** Treat it as compromised: it is public in git
   history since 2025-09-19. Replace the DPAPI blob with a managed identity or a Key Vault
   reference; do not ship a decryption key inside the product.
2. **Purge `app/services/DSTFile` from git history**, and confirm the Cosmos key and
   `APP_SECRET` in GitHub Secrets are also rotated.
3. **Stop sending the domain password to telemetry.** Use a service identity for Cosmos
   egress; drop `os.getlogin()` from the payload; either delete the telemetry module or add a
   visible, opt-out consent control.
4. **Move telemetry to a corporate Azure tenant** rather than `mark.documents.azure.com`.
5. **Replace the PowerShell DPAPI unwrap** with `cryptography`'s Windows DPAPI support
   (`CryptUnprotectData`) so no hidden shell is spawned.
6. **Add Authenticode signing** to both the executable and the Inno Setup installer; uncomment
   `SignTool` in `installer.iss`.
7. **Untrack `tests/.Notebooks/`** (`git rm -r --cached tests/.Notebooks`) and fix the
   ineffective ignore rules.
8. **Fix the shell-injection sinks**: drop `shell=True` in `credentials.py:30`; pass paths as
   arguments rather than interpolating them into PowerShell strings in `file_handler.py`.
9. **Review whether `tests/Assets/` should contain real signed customer documents**; replace
   with synthetic fixtures.
10. **Add a short threat-model note to the README** explaining the hidden PowerShell and the
    telemetry, so the next reviewer or scanner has context. The existing GDPR claim is
    inaccurate and should be corrected regardless.

---

## 5. Note on the README's accuracy

For whoever reviews the flag: the README is, on this point, actively misleading. It asserts
that three secrets are kept out of the repo and that telemetry collects no personally
identifiable information. In the committed code:

- one of the three secrets (`DSTFile`) **is** in the repo and in the distributed binary;
- telemetry **does** collect the logged-in username and document paths on every event.

Reconciling the documentation with the code is probably the fastest path to an IT approval.
