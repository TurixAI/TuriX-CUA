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
It ships with a **state‑of‑the‑art computer‑use agent** (achieves 80% success rate on our OSWorld‑style Mac benchmark and 64.2% success rate on OSWorld) yet stays 100 % open‑source and cost‑free for personal & research use.  

Prefer your own model? **Change in `config.json` and go.**

## Table of Contents
- [📞 Contact & Community](#-contact--community)
- [🤖 OpenClaw Skill](#-openclaw-skill)
- [📰 Latest News](#-latest-news)
- [🖼️ Demos](#️-demos)
- [✨ Key Features](#-key-features)
- [📊 Model Performance](#-model-performance)
- [🚀 Quick‑Start (macOS 15+)](#-quickstart-macos-15)
   - [1. Download the App](#1-download-the-app)
   - [2. Create a Python 3.12 Environment](#2-create-a-python-312-environment)
   - [3. Grant macOS Permissions](#3-grant-macos-permissions)
      - [3.1 Accessibility](#31-accessibility)
      - [3.2 Safari Automation](#32-safari-automation)
   - [4. Configure & Run](#4-configure--run)
   - [4.4 Skills (Optional)](#44-skills-optional)
- [🤝 Contributing](#-contributing)
- [🗺️ Roadmap](#️-roadmap)

---

## 🤖 OpenClaw Skill

Use TuriX via OpenClaw with our published ClawHub skill:  
https://clawhub.ai/Tongyu-Yan/turix-cua

This repo also includes local OpenClaw skill packages in `OpenCLaw_TuriX_skill/`:
- macOS package in `main` (`SKILL.md` + `scripts/run_turix.sh`)
- Windows package in `multi-agent-windows` (`SKILL.md` + `scripts/run_turix.ps1` + `agents/openai.yaml`)

For installation and permissions, follow `OpenCLaw_TuriX_skill/README.md`.

---

## 📰 Latest News

**May 11, 2026** - Now can download **TuriX** from our [official web page](https://www.ngtechai.com).

**April 8, 2026** - 🚀 Introducing **TuriX 3.0.0-alpha**

[Download the app](https://www.ngtechai.com/)

This is our all-in-one productivity app that combines **TuriX CUA + CLI** in one workflow, and adds two new capabilities:
- **TuriX-work** for everyday office execution and task orchestration
- **TuriX-code** for coding, automation, and engineering tasks

From writing code to handling office tasks, you can execute with CLI precision and close the loop through GUI actions in one continuous flow.

**March 16, 2026** - 🐧 **Linux support is now available** on branch `multi-agent-linux`. If you want to run TuriX on Linux (for example Ubuntu), switch to that branch first:
```bash
git checkout multi-agent-linux
```

**March 9, 2026** - Added a new **OpenClaw Flash/Fast Mode skill for macOS** on branch `mac_legacy`. If you want to use this faster, lighter setup, switch to that branch first:
```bash
git checkout mac_legacy
```

**March 5, 2026** - Updated the **Windows OpenClaw local skill** on branch `multi-agent-windows` with direct dispatch, safer pre-flight checks, and the new `OpenCLaw_TuriX_skill/agents/openai.yaml`.

**Earlier updates (Jan 2026 and before)** - We shipped v0.3 (DuckDuckGo, Ollama, recoverable memory compression, Skills), published the TuriX OpenClaw skill on ClawHub, upgraded the core architecture to multi-model, and rolled out major model capability improvements including Qwen3-VL support.

Ready to level up? Update your `config.json` and start automating—happy hacking! 🎉

*Stay tuned to our [Discord](https://discord.gg/vkEYj4EV2n) for tips, user stories, and the next big drop.*

---

## 🖼️ Demos
<p align="center"><strong>TuriX App Demo</strong></p>
<p align="center">
   <img src="./doc/app_demo.png" width="1600" alt="TuriX app demo">
</p>

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

TuriX scores **64.2% (229.88 / 358)** on the full OSWorld benchmark, ranking **3rd overall** among all submitted agents. Notably, TuriX is built and optimized for **macOS**, where we achieve an **80%+ success rate** on our self-hosted OSWorld-style Mac benchmark. We used **zero Linux training data**, yet still achieve a top-3 finish on OSWorld's Linux-based environment.

<p align="center">
   <img src="./doc/os-world.png" width="600" alt="TuriX OSWorld benchmark score — 64.2%">
</p>

<p align="center">
   <img src="./doc/performance_sum.jpg" width="1600" alt="TuriX performance">
</p>

For more details, check our [report](https://turix.ai/technical-report/).

For complementary live-web browser-agent evaluation, see [ClawBench](https://github.com/TIGER-AI-Lab/ClawBench); this is an external benchmark reference and does not imply integration with or support from TuriX.

## 🚀 Quick‑Start (macOS 15+)

> **We never collect data**—install, grant permissions, and hack away.

> **0. Windows Users**: Switch to the `multi-agent-windows` branch for Windows-specific setup and installation instructions.
>
> ```bash
> git checkout multi-agent-windows
> ```
>
> For the updated OpenClaw Windows local skill package, see `OpenCLaw_TuriX_skill/README.md` in that branch.
>
> **0. Linux Users**: Switch to the `multi-agent-linux` branch for Linux-specific setup and installation instructions.
>
> ```bash
> git checkout multi-agent-linux
> ```
>
> **0. Windows Legacy Users**: For the previous Windows setup, switch to the `windows_legacy` branch.
>
> **0. macOS Legacy Users**: For the previous single-model macOS setup, switch to the `mac_legacy` branch.


### 1. Download the App
For easier usage, [download the app](https://www.ngtechai.com/)

Or follow the manual setup below:

### 2. Create a Python 3.12 Environment
Firstly Clone the repository and run:
```bash
conda create -n turix_env python=3.12
conda activate turix_env        # requires conda ≥ 22.9
pip install -r requirements.txt
```

### 3. Grant macOS Permissions

#### 3.1 Accessibility
1. Open **System Settings ▸ Privacy & Security ▸ Accessibility**  
2. Click **＋**, then add **Terminal** and **Visual Studio Code** ANY IDE you use
3. If the agent still fails, also add **/usr/bin/python3**

#### 3.2 Safari Automation
1. **Safari ▸ Settings ▸ Advanced** → enable **Show features for web developers**  
2. In the new **Develop** menu, enable  
    * **Allow Remote Automation**  
    * **Allow JavaScript from Apple Events**  

##### Trigger the Permission Dialogs (run once per shell)
```
# macOS Terminal
osascript -e 'tell application "Safari" \
to do JavaScript "alert(\"Triggering accessibility request\")" in document 1'

# VS Code integrated terminal (repeat to grant VS Code)
osascript -e 'tell application "Safari" \
to do JavaScript "alert(\"Triggering accessibility request\")" in document 1'
```

> **Click "Allow" on every dialog** so the agent can drive Safari.

### 4. Configure & Run

#### 4.1 Edit Task Configuration

> [!IMPORTANT]
> **Task Configuration is Critical**: The quality of your task instructions directly impacts success rate. Clear, specific prompts lead to better automation results.

Edit task in `examples/config.json`:
```json
{
    "agent": {
         "task": "open system settings, switch to Dark Mode"
    }
}
```

#### 4.2 Edit API Configuration

In this main (multi-agent) branch, you need to set the brain, actor, and memory models. It only supports mac for now. If you enable planning
(`agent.use_plan: true`), you also need to set the planner model.

Edit API in `examples/config.json`:
```json
"brain_llm": {
      "provider": "turix",
      "model_name": "turix-brain",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://your-endpoint/v1"
   },
"actor_llm": {
      "provider": "turix",
      "model_name": "turix-actor",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://your-endpoint/v1"
   },
"memory_llm": {
      "provider": "turix",
      "model_name": "turix-brain",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://your-endpoint/v1"
   },
"planner_llm": {
      "provider": "turix",
      "model_name": "turix-brain",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://your-endpoint/v1"
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

#### 4.3 Configure Custom Models (Optional)

If you want to use other models not defined by the build_llm function in the main.py, you need to first define it, then setup the config.

main.py:

```
if provider == "name_you_want":
        return ChatOpenAI(
            model="gpt-4.1-mini", api_key=api_key, temperature=0.3
        )
```
Switch between ChatOpenAI, ChatGoogleGenerativeAI, ChatAnthropic, or ChatOllama base on your llm. Also change the model name.

#### 4.4 Skills (Optional)

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

#### 4.5 Start the Agent

```bash
python examples/main.py
```

**Enjoy hands‑free computing 🎉**

#### 4.6 Resume a Terminated Task

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

[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/turixai-turix-cua-badge.png)](https://mseep.ai/app/turixai-turix-cua)
