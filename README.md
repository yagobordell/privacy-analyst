## Installation Notes (Windows + WSL2)

### Problem: WSL2 cannot connect to Ollama (`localhost:11434`)

By default, WSL2 might not correctly resolve `localhost` to services running natively on Windows (like Ollama), even when they are on the same machine.

**Symptom:**
curl http://localhost:11434
curl: (7) Failed to connect to localhost port 11434

**Applied solution:** Enable WSL2's "mirrored" networking mode, which unifies the WSL network stack with the Windows one (requires Windows 11 22H2+).

1. Create/edit `C:\Users\<user>\.wslconfig`:
   [wsl2]
   networkingMode=mirrored

2. Restart WSL from PowerShell:
   wsl --shutdown

3. Verify from the Ubuntu terminal:
   curl http://localhost:11434
   # Should return: "Ollama is running"

**Alternative** (if your Windows version does not support `mirrored` mode): Use the Windows host IP instead of `localhost`. You can obtain it by running `cat /etc/resolv.conf` from WSL, and then configure it as `OLLAMA_HOST` in your Python code.
