<p align="center">
   <img src="./doc/LogoHFitted.svg" width="1600" alt="TuriX logo">
</p>

<h1 align="center">TuriX · Desktop Actions, Driven by AI</h1>

<p align="center"><strong>Talk to your computer, watch it work.</strong></p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-CN.md">中文</a>
</p>

## 📞 Contact & Community

Join our Discord community for support, discussions, and updates:

<p align="center">
   <a href="https://discord.gg/yaYrNAckb5">
      <img src="https://img.shields.io/discord/1400749393841492020?color=7289da&label=Join%20our%20Discord&logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord">
   </a>
</p>

Or contact us with email: contact@turix.ai

TuriX lets your powerful AI models take real, hands‑on actions directly on your desktop. 
It ships with a **state‑of‑the‑art computer‑use agent** (achieves 80% success rate on our OSWorld‑style Mac benchmark and 60% success rate on OSWorld) yet stays 100 % open‑source and cost‑free for personal & research use.  

Prefer your own model? **Change in `config.json` and go.**

## Table of Contents
- [📞 Contact & Community](#-contact--community)
- [🤖 OpenClaw Skill](#-openclaw-skill)
- [📰 Latest News](#-latest-news)
- [🖼️ Demos](#️-demos)
- [✨ Key Features](#-key-features)
- [📊 Model Performance](#-model-performance)
- [🚀 Quick‑Start (Linux)](#-quickstart-linux)
   - [1. Download the App](#1-download-the-app)
   - [2. Create a Python 3.12 Environment](#2-create-a-python-312-environment)
   - [Linux System Prerequisites](#linux-system-prerequisites)
   - [3. Configure & Run](#3-configure--run)
   - [3.4 Skills (Optional)](#34-skills-optional)
- [🤝 Contributing](#-contributing)
- [🗺️ Roadmap](#️-roadmap)

---

## 🤖 OpenClaw Skill

Use TuriX via OpenClaw with our published skill on ClawHub:  
https://clawhub.ai/Tongyu-Yan/turix-cua  
This lets OpenClaw call TuriX so it can act as your desktop agent.

Local OpenCLaw skill (macOS): this repo also includes a ready-to-use skill package in `OpenCLaw_TuriX_skill/` (`SKILL.md` + `scripts/run_turix.sh`).  
Copy it into your OpenClaw local skills folder (for example: `clawd/skills/local/turix-mac/`) and follow `OpenCLaw_TuriX_skill/README.md` for setup and permissions.

Local OpenClaw skill (Windows): on branch `multi-agent-windows`, `OpenCLaw_TuriX_skill/` is updated for Windows with `SKILL.md`, `scripts/run_turix.ps1`, and `agents/openai.yaml`.  
This update adds direct dispatch via `turix` (alias `turix-win`) in the current OpenClaw session, plus pre-flight checks in `run_turix.ps1` (required branch `multi-agent-windows`, conda/config validation, and `--dry-run` support).
You can also instruct OpenClaw directly: read `OpenCLaw_TuriX_skill/README.md` first, then install and configure TuriX.

---

## 📰 Latest News

**March 16, 2026** - 🐧 **Linux support is now available** on branch `multi-agent-linux`. If you want to run TuriX on Linux (for example Ubuntu), switch to that branch first:
```bash
git checkout multi-agent-linux
```

**March 9, 2026** - Added a new **OpenClaw Flash/Fast Mode skill for macOS** on branch `mac_legacy`. If you want to use this faster, lighter setup, switch to that branch first:
```bash
git checkout mac_legacy
```

**March 5, 2026** - Updated the **Windows OpenClaw local skill** on branch `multi-agent-windows`. This update adds a user-invocable `turix` skill alias, direct dispatch without requiring a Turix sub-session, branch-safe pre-flight checks in `run_turix.ps1`, and the new agent interface file `OpenCLaw_TuriX_skill/agents/openai.yaml`.

**January 30, 2026** - 🧩 We published the **TuriX OpenClaw Skill** on ClawHub: https://clawhub.ai/Tongyu-Yan/turix-cua. You can now use OpenClaw to call TuriX and automate desktop tasks.

**January 27, 2026 — v0.3** - 🎉 TuriX v0.3 is now live on the main branch! This release brings DuckDuckGo search, Ollama support, advanced recoverable memory compression, and Skills—unlocking smarter planning, more resilient memory, and reusable workflows for desktop automation. We’re excited to see more users try it out and share feedback as we keep pushing the platform forward.

**January 27, 2026** - 🎉 We released **Recoverable Memory Compression** and **Skills** in the `multi-agent` and `multi-agent-windows` branches. These features add more stable memory handling and reusable markdown playbooks for task planning.

**January 27, 2026** - 🎉 We released **Recoverable Memory Compression** and **Skills** in the `main` (formerly `multi-agent`) and `multi-agent-windows` branches. These features add more stable memory handling and reusable markdown playbooks for task planning.

**December 30, 2025** - 🎉 Significant update in Agent Archetecture. We introduce a multi-model archetecture in the `main` (formerly `multi-agent`) branch, releasing the stress from a single model to multiple models.

**October 16, 2025** - 🚀 Big news for automation enthusiasts! TuriX now fully supports the cutting-edge **Qwen3-VL** vision-language model, empowering seamless PC automation across both **macOS** and **Windows**. This integration boosts task success rates by up to 15% on complex UI interactions (based on our internal benchmarks), making your desktop workflows smarter and faster than ever. Whether you're scripting daily routines or tackling intricate projects, Qwen3-VL's advanced multimodal reasoning brings unparalleled precision to the table.

**September 30, 2025** - 🎉 Exciting update! We've just released our latest AI model on the [TuriX API platform](https://turixapi.io), bringing enhanced performance, smarter reasoning, and seamless integration for even more powerful desktop automation. Developers and researchers, this is your cue—head over to the platform to access it now and elevate your workflows!

Ready to level up? Update your `config.json` and start automating—happy hacking! 🎉

*Stay tuned to our [Discord](https://discord.gg/vkEYj4EV2n) for tips, user stories, and the next big drop.*

---

## 🖼️ Demos
<h3 align="center">MacOS Demo</h3>
<p align="center"><strong>Book a flight, hotel and uber.</strong></p>
<p align="center">
   <img src="./doc/booking_demo.gif" width="1600" alt="TuriX macOS demo - booking">
</p>

<p align="center"><strong>Search iPhone price, create Pages document, and send to contact</strong></p>
<p align="center">
   <img src="./doc/demo1.gif" width="1600" alt="TuriX macOS demo - iPhone price search and document sharing">
</p>

<p align="center"><strong>Generate a bar-chart in the numbers file sent by boss in discord and insert it to the right place of my powerpoint, and reply my boss.</strong></p>
<p align="center">
   <img src="./doc/complex_demo_mac.gif" width="1600" alt="TuriX macOS demo - excel graph to powerpoint">
</p>

<h3 align="center">Windows Demo</h3>
<p align="center"><strong>Search video content in youtube and like it</strong></p>
<p align="center">
   <img src="./doc/win_demo1.gif" width="1600" alt="TuriX Windows demo - video search and sharing">
</p>

<h3 align="center">MCP with Claude Demo</h3>
<p align="center"><strong>Claude search for AI news, and call TuriX with MCP, write down the research result to a pages document and send it to contact</strong></p>
<p align="center">
   <img src="./doc/mcp_demo1.gif" width="1600" alt="TuriX MCP demo - news search and sharing">
</p>

---

## ✨ Key Features
| Capability | What it means |
|------------|---------------|
| **SOTA default model** | Outperforms previous open‑source agents (e.g. UI‑TARS) on success rate and speed on Mac |
| **No app‑specific APIs** | If a human can click it, TuriX can too—WhatsApp, Excel, Outlook, in‑house tools… |
| **Hot‑swappable "brains"** | Replace the VLM policy without touching code (`config.json`) |
| **MCP‑ready** | Hook up *Claude for Desktop* or **any** agent via the Model Context Protocol (MCP) |
| **Skills (markdown playbooks)** | Planner selects relevant skill guides (name + description), brain uses full instructions to plan each step |

---
## 📊 Model Performance

Our agent achieves state-of-the-art performance on desktop automation tasks:

### OSWorld Benchmark — 3rd Place on the Leaderboard (50 Steps)

TuriX scores **59.7% (213.29 / 357)** on the full OSWorld benchmark, ranking **3rd overall** among all submitted agents. Notably, TuriX is built and optimized for **macOS**, where we achieve an **80%+ success rate** on our self-hosted OSWorld-style Mac benchmark. We used **zero Linux training data**, yet still achieve a top-3 finish on OSWorld's Linux-based environment.

<p align="center">
   <img src="./doc/os-world.png" width="600" alt="TuriX OSWorld benchmark score — 59.7%">
</p>

<p align="center">
   <img src="./doc/performance_sum.jpg" width="1600" alt="TuriX performance">
</p>

For more details, check our [report](https://turix.ai/technical-report/).

## 🚀 Quick‑Start (Linux)

> **We never collect data**—install, grant permissions, and hack away.
>
> For OpenClaw local skill installation, read `OpenCLaw_TuriX_skill/README.md` first.

### 1. Download the App
For easier usage, [download the app](https://turix.ai/)

Or follow the manual setup below:

### 2. Create a Python 3.12 Environment
Firstly Clone the repository and run:
```bash
conda create -n turix_env python=3.12
conda activate turix_env        # requires conda ≥ 22.9
pip install -r requirements.txt
```

### Linux System Prerequisites

If you run this branch on Linux (X11 desktop), install these system packages first:

```bash
sudo apt update
sudo apt install -y \
  xclip xdotool wmctrl x11-utils x11-xserver-utils xdg-utils \
  libglib2.0-bin libgtk-3-bin scrot python3-tk
```

Notes:
- `xclip`: clipboard backend used by `pyperclip`.
- `xdotool` and `wmctrl`: keyboard/window activation and window control.
- `x11-utils` and `x11-xserver-utils`: provide `xprop` and `xrandr`.
- `libglib2.0-bin`, `libgtk-3-bin`, `xdg-utils`: provide `gio`, `gtk-launch`, `xdg-open`.
- `scrot`: screenshot backend used by `pyautogui` on Linux.
- Current Linux implementation in this branch targets X11 sessions.

### 3. Configure & Run

#### 3.1 Edit Task Configuration

Edit task in `examples/config.json`:

> [!IMPORTANT]
> **Task Configuration is Critical**: The quality of your task instructions directly impacts success rate. Clear, specific prompts lead to better automation results.

```json
{
    "agent": {
         "task": "open Chrome, go to github, search for TuriX CUA, enter the TuriX repository, and star this repository. "
    }
}
```
This branch supports Linux desktop automation (X11). Configure your task directly in `examples/config.json` and run.

#### 3.2 Edit API Configuration

Get API now credit from our [official web page](https://turix.ai/api-platform/).
Login to our website and the key is at the bottom.

In this multi-agent branch, you need to set the brain, actor, and memory models. If you enable planning
(`agent.use_plan: true`), you also need to set the planner model.
We strongly recommend you set the turix-actor model as the actor. The brain can be any VLM you like.

Edit API in `examples/config.json`:
```json
"brain_llm": {
      "provider": "turix",
      "model_name": "turix-brain",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://turixapi.io/v1"
   },
"actor_llm": {
      "provider": "turix",
      "model_name": "turix-actor",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://turixapi.io/v1"
   },
"memory_llm": {
      "provider": "turix",
      "model_name": "turix-brain",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://turixapi.io/v1"
   },
"planner_llm": {
      "provider": "turix",
      "model_name": "turix-brain",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://turixapi.io/v1"
   }
```

For a local Ollama setup, point each role to your Ollama server:
```json
"brain_llm": {
      "provider": "ollama",
      "model_name": "llama3.2-vision",
      "base_url": "http://localhost:11434"
   },
"actor_llm": {
      "provider": "ollama",
      "model_name": "llama3.2-vision",
      "base_url": "http://localhost:11434"
   },
"memory_llm": {
      "provider": "ollama",
      "model_name": "llama3.2-vision",
      "base_url": "http://localhost:11434"
   },
"planner_llm": {
      "provider": "ollama",
      "model_name": "llama3.2-vision",
      "base_url": "http://localhost:11434"
   }
```

#### 3.3 Configure Custom Models (Optional)

If you want to use other models not defined by the build_llm function in the main.py, you need to first define it, then setup the config.

main.py:

```
if provider == "name_you_want":
        return ChatOpenAI(
            model="gpt-4.1-mini", api_key=api_key, temperature=0.3
        )
```
Switch between ChatOpenAI, ChatGoogleGenerativeAI, ChatAnthropic, or ChatOllama base on your llm. Also change the model name.

#### 3.4 Skills (Optional)

Skills are lightweight markdown playbooks stored in a single folder (default: `skills/`). Each skill file starts with YAML frontmatter containing `name` and `description`, followed by the instructions. The planner only sees the name + description to select relevant skills; the brain receives the full skill content to guide step goals.
Skills selection requires planning (`agent.use_plan: true`).

Example skill file (`skills/github-web-actions.md`):
```md
---
name: github-web-actions
description: Use when navigating GitHub in a browser (searching repos, starring, etc.).
---
# GitHub Web Actions
- Open GitHub, use the site search, and navigate to the repo page.
- If login is required, ask the user before proceeding.
- Confirm the Star button state before moving on.
```

Enable in `examples/config.json`:
```json
{
  "agent": {
    "use_plan": true,
    "use_skills": true,
    "skills_dir": "skills",
    "skills_max_chars": 4000
  }
}
```

#### 3.5 Start the Agent

```bash
python examples/main.py
```

**Enjoy hands‑free computing 🎉**

#### 3.6 Resume a Terminated Task

To resume a task after an interruption, set a stable `agent_id` and enable `resume` in `examples/config.json`:
```json
{
    "agent": {
         "resume": true,
         "agent_id": "my-task-001"
    }
}
```
Notes:
- Use the same `agent_id` as the run you want to resume.
- Keep the same `task` when resuming.
- Resume only works if prior memory exists at `src/agent/temp_files/<agent_id>/memory.jsonl`.
- To start fresh, set `resume` to `false`, change `agent_id`, or delete `src/agent/temp_files/<agent_id>`.

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guide](CONTRIBUTING.MD) to get started.

Quick links:
- [Development Setup](CONTRIBUTING.MD#development-setup)
- [Code Style Guidelines](CONTRIBUTING.MD#code-style-guidelines)
- [Testing](CONTRIBUTING.MD#testing)
- [Pull Request Process](CONTRIBUTING.MD#pull-request-process)

For bug reports and feature requests, please [open an issue](https://github.com/TurixAI/TuriX-CUA/issues).

