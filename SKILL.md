---
name: plot-is-all-you-need
description: >-
  Plot Is All You Need 的兼容入口。画图、选图、改配色与版式使用 plot；
  从视频或主页收集参考图、扩充与维护图库使用 collect。
---

# Plot Is All You Need

现在由两个套件共用图库、脚本和阶段细则：

- **画图**：读取 [plot](skills/plot/SKILL.md)，插件入口为 `/plot-is-all-you-need:plot`。
- **收图**：读取 [collect](skills/collect/SKILL.md)，插件入口为 `/plot-is-all-you-need:collect`。

按用户请求进入对应套件，不要同时加载两个套件的全部说明。插件结构与本地安装见 [SUITES.md](SUITES.md)。
