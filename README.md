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
- [📁 Project Architecture](#-project-architecture)
- [🔍 Implementation Principles](#-implementation-principles)
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

**April 8, 2026** - 🚀 Introducing **TuriX SuperPower 3.0.0-alpha** for macOS (Apple Silicon):  
[Download dmg(ONLY for mac)](https://turix-staging-apollo.sfo3.cdn.digitaloceanspaces.com/turix-app/desktop/releases/Turix-SuperPower_3.0.0-alpha_aarch64.dmg)

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

**Earlier updates (Jan 2026 and before)** - We shipped v0.3 (DuckDuckGo, Ollama, recoverable memory compression, Skills), published the TuriX OpenClaw skill on ClawHub, upgraded the core architecture to multi-model, and rolled out major model capability improvements including Qwen3-VL support and TuriX API model upgrades.

Ready to level up? Update your `config.json` and start automating—happy hacking! 🎉

*Stay tuned to our [Discord](https://discord.gg/vkEYj4EV2n) for tips, user stories, and the next big drop.*

---

## 🖼️ Demos
<p align="center"><strong>TuriX SuperPower App Demo</strong></p>
<p align="center">
   <img src="./doc/app_demo.jpg" width="1600" alt="TuriX SuperPower app demo">
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
For easier usage, [download the app](https://turix.ai/)

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

Get API now with credit from our [official web page](https://turix.ai/api-platform/).
Login to our website and the key is at the bottom.

In this main (multi-agent) branch, you need to set the brain, actor, and memory models. It only supports mac for now. If you enable planning
(`agent.use_plan: true`), you also need to set the planner model.
We strongly recommand you to set the turix-actor model as the actor. The brain can be any VLMs you like, we provide qwen3.5vl in our platform. Gemini-3-pro is tested to be smartest, and Gemini-3-flash is fast and smart enough for most of the tasks. 

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

## 📁 Project Architecture

TuriX采用模块化的多智能体架构，由以下核心组件组成：

### Core Components

| Component | Description | Location |
|-----------|-------------|----------|
| **Agent** | The main orchestrator that coordinates all other components | `src/agent/service.py` |
| **Controller** | Executes actions on the desktop and manages the action registry | `src/controller/service.py` |
| **MacUITreeBuilder** | Builds UI tree and captures screenshots for macOS | `src/mac/tree.py` |
| **MessageManager** | Manages messages between different components | `src/agent/message_manager/service.py` |
| **Planner** | Creates step-by-step plans based on user tasks | `src/agent/planner_service.py` |
| **BrainSearchFlow** | Integrates with search engines for information gathering | `src/utils/brain_search.py` |
| **Skills System** | Loads and uses skill playbooks for task execution | `src/utils/skills.py` |
| **RecordStore** | Stores and manages recorded information | `src/utils/record_store.py` |

### Multi-Model Architecture

TuriX uses a multi-model approach with specialized roles:

- **Brain LLM**: Analyzes screenshots and determines the next goal
- **Actor LLM**: Generates specific actions to achieve the goal
- **Planner LLM**: Creates high-level plans for complex tasks
- **Memory LLM**: Manages and compresses agent memory

### Key Technical Features

1. **Memory Compression**: Automatically summarizes and compresses memory to stay within token limits
2. **Skills System**: Uses markdown playbooks to guide task execution
3. **Search Integration**: Leverages search engines for information gathering
4. **Task Resume**: Supports resuming interrupted tasks
5. **MCP Integration**: Compatible with Model Context Protocol for third-party agent connectivity

## 🗺️ Roadmap

| Quarter | Feature | Description |
|---------|---------|-------------|
| **2025 Q3** | **✅ Terminate and Resume** | Support resuming from terminated task. |
| **2025 Q3** | **✅ Windows Support** | Cross-platform compatibility bringing TuriX automation to Windows environments *(Now Available)* |
| **2025 Q3** | **✅ Enhanced MCP Integration** | Deeper Model Context Protocol support for seamless third-party agent connectivity *(Now Available)*|
| **2025 Q4** | **✅ Next-Gen AI Model** | Significantly improved clicking accuracy and task execution capabilities |
| **2025 Q4** | **✅ Windows-Optimized Model** | Native Windows model architecture for superior performance on Microsoft platforms
| **2025 Q4** | **✅ Support Gemini-3-pro model** | Run with any compatible vision language models |
| **2025 Q4** | **✅ Planner** | Understands user intent and makes step-by-step plans to complete tasks |
| **2025 Q4** | **✅ Multi-Agent Architecture** | Evaluate and guide each step in working |
| **2025 Q4** | **✅ Duckduckgo Integration** | Speed up the information gathering process, for smarter planning (now on main) |
| **2026 Q1** | **✅ Ollama Support** | Support the Ollama Qwen3vl models |
| **2026 Q1** | **✅ Recoverable Memory Compression** | Advance memory management mechanism to stabelize performance (Commited beta version) |
| **2026 Q1** | **✅ Skills** | Stablize the agent workflow. |
| **2026 Q1** | **✅ OpenClaw Skill** | Published on ClawHub (https://clawhub.ai/Tongyu-Yan/turix-cua) so OpenClaw can use TuriX as its eyes and hands. |
| **2026 Q1** | **✅ OpenClaw Windows Skill Refresh** | Updated `multi-agent-windows` local skill package with direct dispatch (`turix`/`turix-win`), required-branch checks, and `--dry-run` support. |
| **2026 Q1** | **✅ Linux Support** | Linux support is now available on branch `multi-agent-linux` (Ubuntu and other distributions). |
| **2026 Q2** | **Browser Automation** | Support a Chrome-like browser for scalability |
| **2026 Q2** | **Persistent Memory** | Learn user preferences and maintain task history across sessions |
| **2026 Q2** | **Learning by Demonstration** | Train the agent by showing it your preferred methods and workflows |
