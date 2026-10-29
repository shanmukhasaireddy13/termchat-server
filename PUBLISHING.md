# Step-by-Step Guide: Publishing to PyPI (Python Package Index)

This document provides exact instructions to publish `termchat-bridge` to PyPI so anyone in the world can install and run it using:
```bash
pip install termchat-bridge
termchat
```

---

## 1. Prerequisites

1. Create an account on [PyPI (pypi.org)](https://pypi.org/account/register/).
2. Enable Two-Factor Authentication (2FA) in your PyPI Account Settings.
3. Generate an **API Token**:
   - Go to [Account Settings > API Tokens](https://pypi.org/manage/account/token/).
   - Click **Add API Token**.
   - Set Token Name (e.g. `termchat-token`) and Scope to **Entire Account** (for first upload).
   - Copy the token starting with `pypi-...` (keep it safe).

*(Optional)* You can also create an account on [TestPyPI (test.pypi.org)](https://test.pypi.org/) to test your release in a sandbox first.

---

## 2. Check Package Name Availability

The name configured in `pyproject.toml` is currently `termchat-bridge`.
If you want to use a different custom name (e.g., `yourname-termchat` or `termchat-cli`), simply edit line 5 of `pyproject.toml`:
```toml
[project]
name = "termchat-bridge"  # Change this if desired
```

---

## 3. Clean and Build Distributions

Make sure your virtual environment has the latest build tools:
```bash
python -m pip install --upgrade build twine
```

Clean any previous builds and generate fresh `.whl` and `.tar.gz` files:
```powershell
# Windows PowerShell
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
python -m build
```
Or on Linux / macOS:
```bash
rm -rf dist/ build/
python -m build
```

You will see:
```text
Successfully built termchat_bridge-0.1.0.tar.gz and termchat_bridge-0.1.0-py3-none-any.whl
```

---

## 4. Validate Package Artifacts

Run `twine check` to ensure your metadata, README markdown rendering, and package structure comply with PyPI standards:
```bash
twine check dist/*
```
Expected output:
```text
Checking dist/termchat_bridge-0.1.0-py3-none-any.whl: PASSED
Checking dist/termchat_bridge-0.1.0.tar.gz: PASSED
```

---

## 5. (Recommended) Test Upload to TestPyPI

Before publishing to the real PyPI, verify on TestPyPI:
```bash
twine upload --repository testpypi dist/*
```
- **Username**: `__token__`
- **Password**: `pypi-your-testpypi-token`

Then test installing it in a clean environment:
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ termchat-bridge
```

---

## 6. Official Upload to PyPI

Upload the built packages to PyPI:
```bash
twine upload dist/*
```
When prompted:
- **Username**: `__token__`
- **Password**: Paste your official PyPI token (`pypi-AgEI...`)

---

## 7. Verify Live Installation

Once uploaded, anyone on **Windows**, **Linux**, **macOS**, or **Raspberry Pi** can install and use it:

```bash
# In any terminal or command prompt:
pip install termchat-bridge

# Start server & host web UI:
termchat server --port 8000

# Connect terminal:
termchat join --server localhost:8000 --name Alice

# Or run everything with one command:
termchat dev
```
