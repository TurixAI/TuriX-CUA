# TuriX Skill for OpenClaw (Windows)

This package adds a local OpenClaw skill that dispatches desktop-computer-use tasks to TuriX on Windows.

## Package Contents

- `SKILL.md`
- `scripts/run_turix.ps1`
- `agents/openai.yaml`

## 1. Install TuriX-CUA (Windows branch required)

Use the Windows branch only:

```powershell
cd $env:USERPROFILE\Desktop
git clone -b multi-agent-windows --single-branch https://github.com/TurixAI/TuriX-CUA.git
cd .\TuriX-CUA
git branch --show-current
```

Expected output:

```text
multi-agent-windows
```

## 2. Prepare Conda Environment

This skill uses `turix_env` by default (same value in `SKILL.md` and `scripts/run_turix.ps1`).

```powershell
conda create -n turix_env python=3.12 -y
conda activate turix_env
pip install -r requirements.txt
```

If you use another env name, update both:

- `scripts/run_turix.ps1` (`$EnvName`)
- Any env examples in `SKILL.md`

## 3. Configure API Keys (Required)

Before running tasks, configure API/model keys first, otherwise the run will fail.

- Configure your API/model keys in `examples/config.json` (set `base_url`, `api_key`, and `model_name` for each role).
- Suggested setup: keep actor on `turix-actor`, choose a fast/stable brain model.

## 4. Install This Skill into OpenClaw

Copy this folder into OpenClaw workspace skills:

```powershell
$skillRoot = "$env:USERPROFILE\.openclaw\workspace\skills"
New-Item -ItemType Directory -Force -Path $skillRoot | Out-Null
Copy-Item -Recurse -Force ".\turix-cua-windows" $skillRoot
```

Final path:

```text
%USERPROFILE%\.openclaw\workspace\skills\turix-cua-windows
```

## 5. Replace Placeholder Path

Edit:

- `%USERPROFILE%\.openclaw\workspace\skills\turix-cua-windows\scripts\run_turix.ps1`

Replace:

- `your_dir\TuriX-CUA`

With your real local path, for example:

- `C:\Users\<YOU>\Desktop\TuriX-CUA`

## 6. Verify Skill and Runtime

Check skill loading:

```powershell
openclaw skills info turix
```

Dry run:

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.openclaw\workspace\skills\turix-cua-windows\scripts\run_turix.ps1" --dry-run "Open Edge and search TuriX"
```

Real task:

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\.openclaw\workspace\skills\turix-cua-windows\scripts\run_turix.ps1" "Open Edge and go to youtube.com"
```

## 7. Trigger from OpenClaw Chat

Example prompts:

- `Send task to turix: open Chrome and go to YouTube`
- `turix: open Settings and switch to dark mode`

## 8. Publish Checklist

- Branch is `multi-agent-windows`
- Conda env naming is consistent (`turix_env`)
- `run_turix.ps1` placeholder path instructions are clear
- API setup reminder is present (configure keys/`base_url` in `examples/config.json`)
- `openclaw skills info turix` returns ready
