<p align="center">
   <img src="./doc/LogoHFitted.svg" width="1600" alt="TuriX logo">
</p>

<h1 align="center">TuriX · Desktop Actions, Driven by AI</h1>

<p align="center"><strong>Talk to your computer, watch it work.</strong></p>

## 📞 Contact & Community

Join our Discord community for support, discussions, and updates:

<p align="center">
   <a href="https://discord.gg/BRxXtnGg">
      <img src="https://img.shields.io/discord/1400749393841492020?color=7289da&label=Join%20our%20Discord&logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord">
   </a>
</p>

Or contact us with email: contact@turix.ai

---

TuriX lets your powerful AI models take real, hands‑on actions directly on your desktop. 
It ships with a **state‑of‑the‑art computer‑use agent** (passes > 68 % of our internal OSWorld‑style test set) yet stays 100 % open‑source and cost‑free for personal & research use.  

Prefer your own model? **Change in `config.json` and go.**

## Table of Contents
- [📞 Contact & Community](#-contact--community)
- [📰 Latest News](#-latest-news)
- [🖼️ Demos](#️-demos)
- [✨ Key Features](#-key-features)
- [📊 Model Performance](#-model-performance)
- [🚀 Quick‑Start (Windows)](#-quickstart-windows)
   - [1. Download the App](#1-download-the-app)
   - [2. Create a Python 3.12 Environment](#2-create-a-python-312-environment)
   - [3. Configure & Run](#3-configure--run)
- [🤝 Contributing](#-contributing)
- [🗺️ Roadmap](#️-roadmap)

---

## 📰 Latest News

**March 16, 2026** - 🐧 **Linux support is now available** on branch `multi-agent-linux`. If you want to run TuriX on Linux (for example Ubuntu), switch to that branch first:
```bash
git checkout multi-agent-linux
```


**October 16, 2025** - 🚀 Big news for automation enthusiasts! TuriX now fully supports the cutting-edge **Qwen3-VL** vision-language model, empowering seamless PC automation across **Windows**. This integration boosts task success rates by up to 15% on complex UI interactions (based on our internal benchmarks), making your desktop workflows smarter and faster than ever. Whether you're scripting daily routines or tackling intricate projects, Qwen3-VL's advanced multimodal reasoning brings unparalleled precision to the table.

Ready to level up? Update your `config.json` and start automating—happy hacking! 🎉

**September 30, 2025** - 🎉 Exciting update! We've just released our latest AI model on the [TuriX API platform](https://turixapi.io), bringing enhanced performance, smarter reasoning, and seamless integration for even more powerful desktop automation. Developers and researchers, this is your cue—head over to the platform to access it now and elevate your workflows!

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

---
## 📊 Model Performance

Our agent achieves state-of-the-art performance on desktop automation tasks:
<p align="center">
   <img src="./doc/performance_sum.jpg" width="1600" alt="TuriX performance">
</p>

For more details, check our [report](https://turix.ai/technical-report/).

## 🚀 Quick‑Start (Windows)

> **Legacy Branch**—we will switch to the multi-agent-windows branch as the main windows branch, and this branch will not be updated after 2025.12.31.

> **We never collect data**—install, grant permissions, and hack away.

### 1. Download the App
The desktop app is not available on Windows yet. Please use the manual setup below.

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

Get API now with $20 credit from our [official web page](https://turix.ai/api-platform/).
Login to our website and the key is at the bottom.

Edit API in `examples/config.json`:
```json
"llm": {
      "provider": "turix",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://llm.turixapi.io/v1"
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
Switch between ChatOpenAI, ChatGoogleGenerativeAI and ChatAnthropic base on your llm. Also change the model name.

#### 3.4 Start the Agent

```bash
python examples/main.py
```

**Enjoy hands‑free computing 🎉**

#### 3.5 Resume a Terminated Task

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

We welcome contributions! Please read our [Contributing Guide](CONTRIBUTING.md) to get started.

Quick links:
- [Development Setup](CONTRIBUTING.md#development-setup)
- [Code Style Guidelines](CONTRIBUTING.md#code-style-guidelines)
- [Testing](CONTRIBUTING.md#testing)
- [Pull Request Process](CONTRIBUTING.md#pull-request-process)

For bug reports and feature requests, please [open an issue](https://github.com/TurixAI/TuriX-CUA/issues).

