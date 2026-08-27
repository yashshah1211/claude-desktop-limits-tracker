# Release Verification Guide

This guide explains how to verify the cryptographic checksum of **`ClaudeLimitTracker.exe`** on Windows before running it.

Verifying the checksum guarantees that:
1. The downloaded binary was compiled directly by the official [GitHub Actions workflow](.github/workflows/build-release.yml) from the open-source repository.
2. The binary has not been modified, corrupted, or tampered with in transit or by any third party.

---

## 🔍 How to Verify the Checksum on Windows

Every GitHub release includes two files:
- **`ClaudeLimitTracker.exe`** (the standalone executable)
- **`ClaudeLimitTracker.exe.sha256`** (the official SHA256 checksum file)

Download both files into the same folder, open a terminal in that folder, and use either method below:

### Method 1: Windows Command Prompt (`cmd.exe`)

Run Windows built-in `certutil` tool:

```cmd
certutil -hashfile ClaudeLimitTracker.exe SHA256
```

**Example Output:**
```
SHA-256 hash of ClaudeLimitTracker.exe:
a1b2c3d4e5f6... [64 hexadecimal characters]
CertUtil: -hashfile command completed successfully.
```

Compare the 64-character hexadecimal string with the contents of `ClaudeLimitTracker.exe.sha256` or the hash displayed on the GitHub Release page. They must match exactly (case-insensitive).

---

### Method 2: PowerShell

Run `Get-FileHash`:

```powershell
Get-FileHash .\ClaudeLimitTracker.exe -Algorithm SHA256
```

Or run this automated comparison one-liner:

```powershell
$expected = (Get-Content .\ClaudeLimitTracker.exe.sha256).Trim().Split(" ")[0].ToLower()
$actual = (Get-FileHash .\ClaudeLimitTracker.exe -Algorithm SHA256).Hash.ToLower()
if ($expected -eq $actual) {
    Write-Host "✅ Checksum verified: Binary is authentic and matches GitHub Actions build." -ForegroundColor Green
} else {
    Write-Host "❌ Checksum MISMATCH! Do not run this binary." -ForegroundColor Red
}
```

---

## 🛡️ Reproducibility & Transparency

- The executable is never uploaded manually from local development machines.
- Every release is automatically built in a clean Microsoft Azure-hosted GitHub Actions runner (`windows-latest`) on tag creation (`v*`).
- You can inspect the exact commit, dependencies, and build commands in the [GitHub Actions tab](../../actions) of this repository.
