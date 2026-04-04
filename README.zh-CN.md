<p align="center">
   <img src="./doc/LogoHFitted.svg" width="1600" alt="TuriX 标志">
</p>

<h1 align="center">TuriX · AI 驱动的数字牛马</h1>

<p align="center"><strong>描述你的任务给你的电脑，以启动你的数字牛马。</strong></p>

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

TuriX 让你的强大 AI 模型能在桌面上真正动手操作。
它内置 **最先进的计算机使用Agent**（在我们的内部电脑操作测试集中通过率 > 68%），同时保持 100% 开源，并对个人与科研用途免费。

想用你自己的模型？**在 `config.json` 中切换即可。**

## 目录
- [📞 联系方式与社区](#contact-community)
- [📰 最新动态](#latest-news)
- [🖼️ 演示](#demos)
- [✨ 关键特性](#key-features)
- [📊 模型性能指标](#model-performance)
- [🚀 快速开始（Windows 11）](#quickstart-windows)
   - [1. 下载应用](#download-app)
   - [2. 创建 Python 3.12 环境](#create-python-env)
   - [3. 配置并运行](#configure-run)
- [🤝 贡献指南](#contributing)
- [🗺️ 开发规划](#roadmap)

---

## <a id="latest-news"></a>📰 最新动态

**2026 年 3 月 16 日** - 🐧 **Linux 支持已上线**，位于 `multi-agent-linux` 分支。如果你要在 Linux（如 Ubuntu）上运行 TuriX，请先切换分支：
```bash
git checkout multi-agent-linux
```


**2025 年 12 月 30 日** - 🎉Agent架构迎来重要更新。我们在 multi-agent 分支引入多模型架构，将单一模型的压力分散到多个模型上，以减轻注意力机制的负担。

**2025 年 10 月 16 日** - 🚀 自动化爱好者的重大消息！TuriX 现已全面支持前沿的 **Qwen3-VL** 视觉语言模型，赋能 **Windows** 的顺畅自动化。基于我们的内部基准，该集成在复杂 UI 交互上可将成功率提升多达 15%。无论你是在脚本化日常流程还是处理复杂项目，Qwen3-VL 的多模态推理都能带来前所未有的精度。

**2025 年 9 月 30 日** - 🎉 激动人心的更新！我们在 [TuriX API 平台](https://turixapi.io) 发布了最新 AI 模型，带来更强性能、更聪明的推理以及更顺滑的集成，帮助你实现更强大的桌面自动化。开发者和研究者，现在就去平台获取并升级你的工作流！

准备好体验了吗？更新你的 `config.json` 并开始自动化吧——祝你玩得开心！🎉

*欢迎关注我们的 [Discord](https://discord.gg/vkEYj4EV2n) 获取使用技巧、用户故事以及后续的 重磅发布。*

---

## <a id="demos"></a>🖼️ 演示
<h3 align="center">Windows 演示</h3>
<p align="center"><strong>在 YouTube 搜索视频内容并点赞</strong></p>
<p align="center">
   <img src="./doc/win_demo1.gif" width="1600" alt="TuriX Windows 演示 - 视频搜索与点赞">
</p>

<h3 align="center">与 Claude 的 MCP 演示</h3>
<p align="center"><strong>Claude 搜索 AI 新闻并通过 MCP 调用 TuriX，将研究结果写入 Word 文档并发送给联系人</strong></p>
<p align="center">
   <img src="./doc/mcp_demo1.gif" width="1600" alt="TuriX MCP 演示 - 新闻搜索与共享">
</p>

---

## <a id="key-features"></a>✨ 关键特性
| 能力 | 含义 |
|------------|---------------|
| **SOTA 默认模型** | 在 Windows 上的成功率和速度上超越此前的开源Agent（如 UI‑TARS） |
| **无需应用专用 API** | 只要人能点，TuriX 就能点——WhatsApp、Excel、Outlook、内部工具… |
| **可热插拔的「大脑」** | 无需改代码即可替换 VLM 策略（`config.json`） |
| **MCP 就绪** | 可接入 *Claude for Desktop* 或 **任何** 支持 Model Context Protocol (MCP) 的Agent |

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

## <a id="quickstart-windows"></a>🚀 快速开始（Windows 11）

> **我们从不收集数据**——安装、配置，尽情折腾。


### <a id="download-app"></a>1. 下载应用
Windows 暂无桌面应用，请按下面的手动步骤安装：

### <a id="create-python-env"></a>2. 创建 Python 3.12 环境
首先克隆仓库并运行：
```bash
conda create -n turix_env python=3.12
conda activate turix_env        # requires conda ≥ 22.9
pip install -r requirements.txt
```

### <a id="configure-run"></a>3. 配置并运行

#### 3.1 编辑任务配置

> [!IMPORTANT]
> **任务配置非常关键**：任务指令的质量直接影响成功率。清晰、具体的提示会带来更好的自动化效果。

在 `examples/config.json` 中编辑任务：
```json
{
    "agent": {
         "task": "open Chrome, go to github, search for TuriX CUA, enter the TuriX repository, and star this repository."
    }
}
```
Windows 版本没有 use_ui 参数，状态只有截图。

#### 3.2 编辑 API 配置

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

#### 3.3 配置自定义模型（可选）

如果你想使用 build_llm 函数中未定义的其他模型，需要先在代码中定义，再在配置中设置。

main.py:

```
if provider == "name_you_want":
        return ChatOpenAI(
            model="gpt-4.1-mini", api_key=api_key, temperature=0.3
        )
```
请根据你的 LLM 在 ChatOpenAI、ChatGoogleGenerativeAI、ChatAnthropic 或 ChatOllama 之间切换，并修改对应的模型名称。

#### 3.4 启动Agent

```bash
python examples/main.py
```

**享受免手操作的计算体验 🎉**

#### 3.5 恢复已中断的任务

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
| **2026 Q1** | **可恢复的内存压缩** | 推进内存管理机制，稳定性能 |
| **2026 Q1** | **✅ Linux 支持** | Linux 支持已在 `multi-agent-linux` 分支上线（包含 Ubuntu 等发行版）。 |
| **2026 Q1** | **浏览器自动化** | 支持类 Chrome 浏览器以提升可扩展性 |
| **2026 Q1** | **长期记忆** | 学习用户偏好并跨会话保留任务历史 |
| **2026 Q2** | **示范学习** | 通过展示你偏好的方法与流程来训练Agent模型 |
