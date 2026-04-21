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
- [🚀 Quick‑Start (Windows)](#-quickstart-windows)
   - [1. Download the App](#1-download-the-app)
   - [2. Create a Python 3.12 Environment](#2-create-a-python-312-environment)
   - [3. Configure & Run](#3-configure--run)
   - [3.4 Skills (Optional)](#34-skills-optional)
- [🤝 Contributing](#-contributing)
- [🗺️ Roadmap](#️-roadmap)

---

## 🤖 OpenClaw Skill

Use TuriX via OpenClaw with our published skill on ClawHub:  
https://clawhub.ai/Tongyu-Yan/turix-cua  
This lets OpenClaw call TuriX so it can act as your desktop agent.

Local OpenClaw skill (Windows): this branch includes a ready-to-use package in `OpenCLaw_TuriX_skill/` (`SKILL.md`, `scripts/run_turix.ps1`, and `agents/openai.yaml`).  
Copy it into your OpenClaw local skills folder (for example: `clawd/skills/local/turix-windows/`) and follow `OpenCLaw_TuriX_skill/README.md` for setup and permissions.
This update adds direct dispatch via `turix` (alias `turix-win`) in the current OpenClaw session, plus pre-flight checks in `run_turix.ps1` (branch validation, conda/config checks, and `--dry-run` support).
You can also instruct OpenClaw directly: read `OpenCLaw_TuriX_skill/README.md` first, then install and configure TuriX.

---

## 📰 Latest News

**March 16, 2026** - 🐧 **Linux support is now available** on branch `multi-agent-linux`. If you want to run TuriX on Linux (for example Ubuntu), switch to that branch first:
```bash
git checkout multi-agent-linux
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
<h3 align="center">Windows Demo</h3>
<p align="center"><strong>Search video content in youtube and like it</strong></p>
<p align="center">
   <img src="./doc/win_demo1.gif" width="1600" alt="TuriX Windows demo - video search and sharing">
</p>

<h3 align="center">MCP with Claude Demo</h3>
<p align="center"><strong>Claude search for AI news, and call TuriX with MCP, write down the research result to a Word document and send it to contact</strong></p>
<p align="center">
   <img src="./doc/mcp_demo1.gif" width="1600" alt="TuriX MCP demo - news search and sharing">
</p>

---

## ✨ Key Features
| Capability | What it means |
|------------|---------------|
| **SOTA default model** | Outperforms previous open‑source agents (e.g. UI‑TARS) on success rate and speed on Windows |
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

## 🚀 Quick‑Start (Windows)

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
There is no use_ui parameter in the windows version, the state is only a screenshot.

#### 3.2 Edit API Configuration

Get API now with credit from our [official web page](https://turix.ai/api-platform/).
Login to our website and the key is at the bottom.

In this main (multi-agent) branch, you need to set the brain, actor, and memory models. It only supports mac for now. If you enable planning
(`agent.use_plan: true`), you also need to set the planner model.
We strongly recommand you to set the turix-actor model as the actor. The brain can be any VLMs you like, we provide qwen3vl in out platform. Gemini-3-pro is tested to be smartest, and Gemini-3-flash is fast and smart enough for most of the tasks. Since turix-brain model is updating now, we recommend you to use gemini in our API platform.

Edit API in `examples/config.json`:
```json
"brain_llm": {
      "provider": "turix",
      "model_name": "gemini-3-flash-preview",
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
      "model_name": "gemini-3-flash-preview",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://turixapi.io/v1"
   },
"planner_llm": {
      "provider": "turix",
      "model_name": "gemini-3-flash-preview",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://turixapi.io/v1"
   }
```

In this multi-agent branch, you need to set the brain, actor, and memory models. If you enable planning
(`agent.use_plan: true`), you also need to set the planner model.
We strongly recommend you set the turix-actor model as the actor. The brain can be any VLM you like.

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
