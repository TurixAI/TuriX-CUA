<p align="center">
   <img src="./doc/LogoHFitted.svg" width="1600" alt="TuriX 标志">
</p>

<h1 align="center">TuriX · AI 驱动的桌面操作</h1>

<p align="center"><strong>对电脑说话，看它工作。</strong></p>

<p align="center">
  <a href="README.md">English</a> | <a href="README.zh-CN.md">中文</a>
</p>

## <a id="contact-community"></a>📞 联系方式与社区

加入我们的 Discord 社区获取支持、讨论与更新：

<p align="center">
   <a href="https://discord.gg/yaYrNAckb5">
      <img src="https://img.shields.io/discord/1400749393841492020?color=7289da&label=Join%20our%20Discord&logo=discord&logoColor=white&style=for-the-badge" alt="加入我们的 Discord">
   </a>
</p>

或通过邮件联系我们：contact@turix.ai

TuriX 让强大的 AI 模型能在你的桌面上真正动手操作。
它内置 **最先进的计算机使用 Agent**（在我们内部的 OSWorld 风格测试集中通过率 > 68%），同时保持 100% 开源，并对个人与科研用途免费。

想用你自己的模型？**在 `config.json` 中切换即可开始。**

## 目录
- [📞 联系方式与社区](#contact-community)
- [🤖 OpenClaw 技能](#openclaw-skill)
- [📰 最新动态](#latest-news)
- [🖼️ 演示](#demos)
- [✨ 关键特性](#key-features)
- [📊 模型性能指标](#model-performance)
- [🚀 快速开始（macOS 15+）](#quickstart-macos-15)
   - [1. 下载应用](#download-app)
   - [2. 创建 Python 3.12 环境](#create-python-env)
   - [3. 授予 macOS 权限](#grant-macos-permissions)
      - [3.1 mac辅助功能](#accessibility)
      - [3.2 Safari 自动化](#safari-automation)
   - [4. 配置并运行](#configure-run)
- [🤝 贡献指南](#contributing)
- [🗺️ 开发规划](#roadmap)

---

## <a id="openclaw-skill"></a>🤖 OpenClaw 技能

本分支已内置 macOS 快速模式的 OpenClaw 本地技能包，位于 `OpenCLaw_TuriX_skill/`（包含 `SKILL.md` 与 `scripts/run_turix.sh`）。

将该目录复制到你的 OpenClaw 本地技能目录（例如：`clawd/skills/local/turix-mac-fast/`），并按 `OpenCLaw_TuriX_skill/README.md` 完成配置。

该技能包针对 `mac_legacy` 分支做了安全检查，使用更轻量的单模型配置路径（`llm` + 可选 `use_planner`）。

---

## <a id="latest-news"></a>📰 最新动态

**2026 年 3 月 16 日** - 🐧 **Linux 支持已上线**，位于 `multi-agent-linux` 分支。如果你要在 Linux（如 Ubuntu）上运行 TuriX，请先切换分支：
```bash
git checkout multi-agent-linux
```


**2026 年 1 月 27 日** - 🎉🎉 我们在 `multi-agent` 与 `multi-agent-windows` 分支发布了 **可恢复的内存压缩** 和 **Skills**。这两项功能带来更稳定的记忆管理与可复用的 Markdown Skills手册，用于规划与执行任务。

**2025 年 12 月 30 日** - 🎉 Agent 架构迎来重要更新。我们在 multi-agent 分支引入多模型架构，将单一模型的压力分散到多个模型上。

**2025 年 10 月 16 日** - 🚀 自动化爱好者的重大消息！TuriX 现已全面支持前沿的 **Qwen3-VL** 视觉语言模型，赋能 **macOS** 与 **Windows** 的顺畅自动化。基于我们的内部基准，该集成在复杂 UI 交互上可将成功率提升多达 15%。无论你是在脚本化日常流程还是处理复杂项目，Qwen3-VL 的多模态推理都能带来前所未有的精度。

**2025 年 9 月 30 日** - 🎉 激动人心的更新！我们在 [TuriX API 平台](https://turixapi.io) 发布了最新 AI 模型，带来更强性能、更聪明的推理以及更顺滑的集成，帮助你实现更强大的桌面自动化。开发者和研究者，现在就去平台获取并升级你的工作流！

准备好体验了吗？更新你的 `config.json` 并开始自动化吧——祝你玩得开心！🎉

*欢迎关注我们的 [Discord](https://discord.gg/vkEYj4EV2n) 获取使用技巧、用户故事以及后续的重磅发布。*

---

## <a id="demos"></a>🖼️ 演示
<h3 align="center">MacOS 演示</h3>
<p align="center"><strong>预订机票、酒店和 Uber。</strong></p>
<p align="center">
   <img src="./doc/booking_demo.gif" width="1600" alt="TuriX macOS 演示 - 预订">
</p>

<p align="center"><strong>查询 iPhone 价格，创建 Pages 文档，并发送给联系人</strong></p>
<p align="center">
   <img src="./doc/demo1.gif" width="1600" alt="TuriX macOS 演示 - 查询 iPhone 价格并共享文档">
</p>

<p align="center"><strong>在老板通过 Discord 发送的 Numbers 文件中生成柱状图，插入到 PowerPoint 的正确位置，并回复老板。</strong></p>
<p align="center">
   <img src="./doc/complex_demo_mac.gif" width="1600" alt="TuriX macOS 演示 - Excel 图表到 PowerPoint">
</p>

<h3 align="center">Windows 演示</h3>
<p align="center"><strong>在 YouTube 搜索视频内容并点赞</strong></p>
<p align="center">
   <img src="./doc/win_demo1.gif" width="1600" alt="TuriX Windows 演示 - 视频搜索与点赞">
</p>

<h3 align="center">与 Claude 的 MCP 演示</h3>
<p align="center"><strong>Claude 搜索 AI 新闻并通过 MCP 调用 TuriX，将研究结果写入 Pages 文档并发送给联系人</strong></p>
<p align="center">
   <img src="./doc/mcp_demo1.gif" width="1600" alt="TuriX MCP 演示 - 新闻搜索与共享">
</p>

---

## <a id="key-features"></a>✨ 关键特性
| 能力 | 含义 |
|------------|---------------|
| **SOTA 默认模型** | 在 Mac 上的成功率和速度上超越此前的开源 Agent（如 UI‑TARS） |
| **无需应用专用 API** | 只要人能点，TuriX 就能点——WhatsApp、Excel、Outlook、内部工具… |
| **可热插拔的「大脑」** | 无需改代码即可替换 VLM 策略（`config.json`） |
| **MCP 就绪** | 可接入 *Claude for Desktop* 或 **任何** 支持 Model Context Protocol (MCP) 的 Agent |

---
## <a id="model-performance"></a>📊 模型性能

我们的 Agent 在桌面自动化任务上达到了业界领先的表现：

### OSWorld 基准测试 — 排行榜第 3 名（50 步）

TuriX 在完整 OSWorld 基准测试中取得 **59.7%（213.29 / 357）** 的成绩，在所有提交的 Agent 中**排名第 3**。值得注意的是，TuriX 专为 **macOS** 打造和优化，在我们自建的 OSWorld 风格 Mac 基准测试中达到了 **80% 以上的成功率**。我们**没有使用任何 Linux 训练数据**，却依然在 OSWorld 的 Linux 环境中取得了前三的成绩。

<p align="center">
   <img src="./doc/os-world.png" width="600" alt="TuriX OSWorld 基准测试成绩 — 59.7%">
</p>

<p align="center">
   <img src="./doc/performance_sum.jpg" width="1600" alt="TuriX 性能">
</p>

更多细节请查看我们的 [报告](https://turix.ai/technical-report/)。

## <a id="quickstart-macos-15"></a>🚀 快速开始（macOS 15+）

> **我们从不收集数据**——安装、授权，尽情折腾。

> **0. Windows 用户**：请切换到 `windows` 分支获取 Windows 专属的安装与设置说明。
>
> ```bash
> git checkout windows
> ```


### <a id="download-app"></a>1. 下载应用
为了更方便使用，[下载应用](https://turix.ai/)

或按下面的手动步骤安装：

### <a id="create-python-env"></a>2. 创建 Python 3.12 环境
首先克隆仓库并运行：
```bash
conda create -n turix_env python=3.12
conda activate turix_env        # requires conda ≥ 22.9
pip install -r requirements.txt
```

### <a id="grant-macos-permissions"></a>3. 授予 macOS 权限

#### <a id="accessibility"></a>3.1 辅助功能
1. 打开 **系统设置 ▸ 隐私与安全性 ▸ 辅助功能**  
2. 点击 **＋**，然后添加 **Terminal** 和 **Visual Studio Code**（或你使用的任何 IDE）
3. 如果运行仍然失败，也请添加 **/usr/bin/python3**

#### <a id="safari-automation"></a>3.2 Safari 自动化
1. **Safari ▸ 设置 ▸ 高级** → 启用 **显示针对 Web 开发者的功能**  
2. 在新出现的 **开发** 菜单中启用  
    * **允许远程自动化**  
    * **允许来自 Apple Events 的 JavaScript**  

##### 触发权限对话框（每个 shell 运行一次）
```
# macOS 终端
osascript -e 'tell application "Safari" \
to do JavaScript "alert(\"Triggering accessibility request\")" in document 1'

# VS Code 集成终端（重复一次以授权 VS Code）
osascript -e 'tell application "Safari" \
to do JavaScript "alert(\"Triggering accessibility request\")" in document 1'
```

> **在每个弹窗中点击“允许”**，这样 Agent 才能驱动 Safari。

### <a id="configure-run"></a>4. 配置并运行

#### 4.1 编辑任务配置

> [!IMPORTANT]
> **任务配置非常关键**：任务指令的质量直接影响成功率。清晰、具体的提示会带来更好的自动化效果。

在 `examples/config.json` 中编辑任务：
```json
{
    "agent": {
         "task": "open system settings, switch to Dark Mode"
    }
}
```

#### 4.2 编辑 API 配置

从我们的[官网](https://turix.ai/api-platform/)获取 API，现在可获 $20 额度。
登录网站，密钥在页面底部。

在 `examples/config.json` 中编辑 API：
```json
"llm": {
      "provider": "turix",
      "api_key": "YOUR_API_KEY",
      "base_url": "https://llm.turixapi.io/v1"
   }
```

如果要使用本地 Ollama，请选择支持视觉的模型，并指向你的 Ollama 服务：
```json
"llm": {
      "provider": "ollama",
      "model_name": "llama3.2-vision",
      "base_url": "http://localhost:11434"
   }
```
若希望 planner_llm 也使用 Ollama，请同样配置。

#### 4.3 配置自定义模型（可选）

如果你想使用 build_llm 函数中未定义的其他模型，需要先在代码中定义，再在配置中设置。

main.py:

```
if provider == "name_you_want":
        return ChatOpenAI(
            model="gpt-4.1-mini", api_key=api_key, temperature=0.3
        )
```
请根据你的 LLM 在 ChatOpenAI、ChatGoogleGenerativeAI、ChatAnthropic 或 ChatOllama 之间切换，并修改对应的模型名称。

#### 4.4 启动 Agent

```bash
python examples/main.py
```

**享受免手操作的计算体验 🎉**

#### 4.5 恢复已中断的任务

如果任务中断，想从上次位置继续，请在 `examples/config.json` 中设置固定的 `agent_id` 并开启 `resume`：
```json
{
    "agent": {
         "resume": true,
         "agent_id": "my-task-001"
    }
}
```
注意：
- 使用与你要恢复的运行相同的 `agent_id`。
- 恢复时请保持同一个 `task`。
- 只有在 `src/agent/temp_files/<agent_id>/memory.jsonl` 已存在时才会生效。
- 想重新开始：将 `resume` 设为 `false`、更换 `agent_id`，或删除 `src/agent/temp_files/<agent_id>`。

## <a id="contributing"></a>🤝 贡献指南

我们欢迎贡献！请阅读我们的 [Contributing Guide](CONTRIBUTING.MD) 了解如何开始。

快速链接：
- [开发环境配置](CONTRIBUTING.MD#development-setup)
- [代码风格指南](CONTRIBUTING.MD#code-style-guidelines)
- [测试](CONTRIBUTING.MD#testing)
- [Pull Request 流程](CONTRIBUTING.MD#pull-request-process)

如果你发现 bug 或有功能需求，请 [提交 issue](https://github.com/TurixAI/TuriX-CUA/issues)。

## <a id="roadmap"></a>🗺️ 路线图

| 季度 | 功能 | 描述 |
|---------|---------|-------------|
| **2025 Q3** | **✅ Windows 支持** | 跨平台兼容，把 TuriX 自动化带到 Windows 环境（现已可用） |
| **2025 Q3** | **✅ 增强的 MCP 集成** | 更深度的 Model Context Protocol 支持，第三方Agent连接更顺畅（现已可用）|
| **2025 Q4** | **✅ 下一代 AI 模型** | 大幅提升点击准确率和任务执行能力 |
| **2026 Q2** | **✅ Windows 优化模型** | 面向微软平台的原生 Windows 模型架构，性能更优 |
| **2025 Q4** | **✅ 支持 Gemini-3-pro 模型** | 可运行任意兼容的视觉语言模型 |
| **2025 Q4** | **✅ 规划器** | 理解用户意图并制定分步计划以完成任务 |
| **2025 Q4** | **✅ 多智能体架构** | 评估并指导每一步执行 |
| **2025 Q4** | **✅ Duckduckgo 集成** | 加速信息收集，提升规划效果（multi-agent 分支） |
| **2026 Q1** | **✅ Ollama 支持** | 支持 Ollama Qwen3vl 模型 |
| **2026 Q1** | **可恢复的内存压缩** | 推进内存管理机制，稳定性能（`multi-agent` 与 `multi-agent-windows` 分支提供 beta） |
| **2026 Q1** | **Skills** | 让 CUA 执行流程更标准化、更稳定（仅在 `multi-agent` 与 `multi-agent-windows` 分支提供）。 |
| **2026 Q1** | **✅ Linux 支持** | Linux 支持已在 `multi-agent-linux` 分支上线（包含 Ubuntu 等发行版）。 |
| **2026 Q1** | **浏览器自动化** | 支持类 Chrome 浏览器以提升可扩展性 |
| **2026 Q1** | **长期记忆** | 学习用户偏好并跨会话保留任务历史 |
| **2026 Q2** | **示范学习** | 通过展示你偏好的方法与流程来训练Agent模型 |
