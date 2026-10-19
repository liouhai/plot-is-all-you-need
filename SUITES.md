# 两个套件，共用一个图库

| 入口 | 负责什么 |
|---|---|
| `/plot-is-all-you-need:plot` | 看图选图、用用户数据绘图、与样例并排验收 |
| `/plot-is-all-you-need:collect` | 下载作品、拆图、由 agent 处理不可靠片段、筛选并扩充图库 |

`skills/plot/SKILL.md` 和 `skills/collect/SKILL.md` 是实际入口；根目录 `SKILL.md` 保留为旧安装方式的路由。
阶段细则、`scripts/`、两个图库与 `taste.md` 仍放在共享根目录。收集默认进入私人 `gallery-local/`，不会自动公开。

## 本地加载

Claude Code 的插件清单在 `.claude-plugin/plugin.json`。可直接从仓库验证和加载：

```sh
claude plugin validate .
claude --plugin-dir "/绝对路径/plot-is-all-you-need"
```

加载后即可说：

```text
/plot-is-all-you-need:collect 帮我收集“作品地址或主页地址”里面的画图作品
/plot-is-all-you-need:plot 帮我把这份数据画成图
```

本机开发副本继续用 `./install.sh` 复制到 `~/.claude/skills/plot-is-all-you-need/`，不使用符号链接、也不删除目标文件。
安装会同步两个入口、共享资源与工具代码；原有私人图库、品味记录和下载状态保持原位。
本机已有下载虚拟环境且安装目录尚无该环境时，会复制已有依赖供新入口使用，不运行包安装命令。
新会话可以通过该安装目录加载插件；旧会话需要重启或重新加载才会发现新入口。

根目录 `plugin.json` 同时提供 OpenAI 的 Agent Plugins 清单。Codex 以插件方式安装后提供命名空间套件；
仅以旧的单 skill 方式安装时，通过 `$plot-is-all-you-need` 路由到对应套件，不声称旧会话已自动注册新命令。

格式依据：[Claude Code 插件](https://code.claude.com/docs/en/plugins)、[OpenAI 插件打包](https://developers.openai.com/plugins/build/plugins)。

## 程序怎么配合 agent

```text
download.py → 原视频/图集
extract.py  → 正式图片 + 不可靠片段包
当前 agent  → 看片段，提交可恢复的图，或舍弃
main_entry.py ingest → 去重、压缩、建空卡片
当前 agent  → Appreciation 鉴赏、重建索引、报告结果
```

`main_entry.py run` 只串联下载和检测，不会在程序内部假装完成视觉判断，也不要求另配模型 API。
`collect` 的 skill 指令要求当前 agent 继续检查片段、提交判断并完成入库。单独运行程序时，pending 会明确保留，入库会拒绝未处理的作品。

人工填写选帧时间的旧流程已移除。不可靠片段会保留原尺寸候选图、短视频、原视频路径和帧号；
agent 可以提交多张图，也可以裁去无关边缘。无法轻易恢复的直接舍弃，不补画、不猜数字、不删除原始媒体。

下载、拆图和统一入口的命令与依赖说明见 [工具用法](tools/douyin-archive/README.md)。
