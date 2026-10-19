# 下载、拆图与 agent 收图

这是 [Plot Is All You Need](../../SUITES.md) 的 `collect` 套件使用的工具。通常不用自己运行，只需对 agent 说：

```text
/plot-is-all-you-need:collect 帮我收集“作品地址或主页地址”里面的画图作品
```

收集内容默认只进本机的 `gallery-local/`。公开图库的边界见 [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md)。

## 三个脚本

| 脚本 | 用途 |
|---|---|
| `download.py` | 下载单条作品或主页全部作品，不要求拆图校准 |
| `extract.py` | 读本地媒体、自动选帧、为不可靠片段输出复核材料，接收 agent 的判断 |
| `main_entry.py` | 单独调用上述能力，或串联下载与拆图；将 agent 选中的正式图入库 |

旧文件名 `douyin_archive.py` 只转发到新入口，使用新子命令；旧的 sample / calibrate / accept 命令已移除。
不再要求用户填写选帧时间。程序不调用模型，当前 agent 通过 skill 指令完成视觉判断。

## 依赖

需要 Python 3.10+、FFmpeg；下载需要 f2、browser-cookie3，拆图预览需要 Pillow，图库入库还需项目根目录的 numpy 等依赖。
安装新 Python 包前先询问用户，不自动安装。

本机已有环境可以分开复用：

- 工具目录 `.venv/bin/python`：下载依赖。
- `$HOME/miniforge3/envs/gpm/bin/python`：拆图、预览、入库。

统一入口优先用本工具目录的 `.venv/bin/python` 执行下载，其余阶段用启动入口的 Python。以下 `python` 表示含 Pillow、numpy 的解释器。

## 只下载

在本工具目录运行：

```sh
# 单条作品；也接受 /note/<作品ID> 和带 modal_id 的链接
.venv/bin/python download.py --video "https://www.douyin.com/video/<作品ID>"
.venv/bin/python download.py --video "https://www.douyin.com/user/<主页ID>?modal_id=<作品ID>"

# 主页全部作品
.venv/bin/python download.py --user "https://www.douyin.com/user/<主页ID>" --output "./downloads"
```

`--video`、`--user` 必须且只能选一个。默认保存到当前工作目录的 `douyin_archive/`。
接受完整的 `https://www.douyin.com` 或 `https://douyin.com` 链接；短链接先用正常浏览器打开为完整链接，不解析整段分享文案。

首次读取 Chrome 的抖音 Cookie，保存到输出目录的 `secrets.json`，权限为 `0600`，后续复用。
可用 `--browser safari` 改用 Safari。读取失败就停止；登录失效时在浏览器重新登录，把旧凭据文件移走后重跑。
不要提交、分享凭据或贴到聊天里。自定义保存目录也要排除在版本控制之外。

主页逐页枚举，防止把残缺列表当成全部。下载两路并发、有限重试；未完成媒体先写 `.part`，损坏原件改名保留。
视频完整解码后才算成功；图集原图检查能否解析。已完成且大小、修改时间未变化的文件会跳过，未完成文件从头重新下载，不按字节续传。
遇到 401、403、429 或验证问题停止，不尝试绕过。网络失败会返回非零退出码，不宣称下载成功。

## 拆本地媒体

```sh
# 下载目录；每个作品生成独立 extraction/，保留原视频与原图
python extract.py extract "./downloads"

# 单个本地视频
python extract.py extract "./video.mp4" --output "./video-extracted"

# 如需比较其他阈值，另出一版，不覆盖已有结果
python extract.py extract "./video.mp4" --output "./video-extracted-005" --threshold 0.05
```

检测仍按场景变化、亮度差、色度差分段，从每段最长稳定区间选帧；不设最短停留时间、不跨段去重。
默认阈值为 `0.02`，是需要 agent 看图检查的起点，不保证每张图都能自动识别。

有明显段内变化或没有稳定区间的段落标为 `pending`，不放进正式 `images/`。
复核包包含短视频、最多 24 张原尺寸候选图、编号预览、原视频路径与帧号。预览采样可能遗漏内容，agent 必要时直接看片段并从原视频提取其余帧。

## agent 处理不可靠片段

agent 看 `review/<片段>/preview.jpg`、原尺寸图和 `clip.mp4`，能轻易取得完整可读图就提交图片；可以一段提供多张。
采用的是 agent 提供的实际图片，不再使用自动选中的问题帧。只允许从原帧提取或裁掉无关边缘，不猜数字、补画遮挡或生成替代图。

```sh
python main_entry.py review "./downloads/works/<作品ID>/extraction" \
  --segment s0002 --images "<完整图1.png>" "<完整图2.png>" --note "说明检查依据"

# 难以恢复就舍弃；原视频和复核材料都保留
python main_entry.py review "./downloads/works/<作品ID>/extraction" \
  --segment s0003 --drop --note "运动模糊且文字无法辨认，舍弃"
```

判断按片段存档，重复提交同一结果不会重写图片。更改已完成结果或阈值需要新输出目录，避免覆盖。
输入图片无法解码、源文件变化、已有图片缺失时会报错，不静默覆盖。

## 统一入口与入库

```sh
python main_entry.py download --video "<作品完整链接>" --output "./downloads"
python main_entry.py extract "./downloads"

# 串联下载与拆图；由调用它的 agent 继续处理 pending
python main_entry.py run --user "<主页完整链接>" --output "./downloads"

# agent 看过正式输出，选出画图作品，所有 pending 处理完后再入库
python main_entry.py ingest "./downloads/works/<作品ID>/extraction" --images "<选中的正式图片>" ...
```

`ingest` 只接受正式输出里的明确选择，不能把 pending 候选直接入库。内容摘要命名避免把来源 ID 带进图库文件名。
复用项目的入库脚本去重、压缩、生成空卡片；不改写 `edited: true` 的卡片。来源及 agent 判断留在本机拆图记录，卡片只写鉴赏。
之后 agent 按 [Appreciation](../../stages/1-appreciation.md) 写新卡片并重建索引。检测完成和空卡片生成都不代表收集闭环完成。

## 输出

```text
downloads/
  state.json / manifest.csv / report.csv
  secrets.json                 私密登录信息
  collection.json              各作品输出位置及检测时的待判断数量快照
  works/<作品ID>/
    video.mp4 / originals/     原始媒体
    source.json                下载校验记录
    extraction/
      images/                  自动可靠帧 + agent 提交的可用图
      preview.jpg / frames.csv
      extraction.json          片段状态、判断理由、图片与入库记录
      review/s0002/
        clip.mp4
        segment.json           原视频、起止帧、候选图对应的帧号和时间
        images/ / preview.jpg  候选原图与预览，不直接入库
```

单个本地视频默认输出到同级的 `<视频名>-extracted/`。`extraction.json` 的 `complete` 表示检测已完成，`pending` 为零才表示片段判断已处理完；是否为绘图作品还要由 agent 目视筛选。复核后的最新数量以每个作品的 `extraction.json` 为准；重跑拆图会刷新汇总快照。

## 离线验证

```sh
.venv/bin/python test_download.py
python test_extract.py
python test_douyin_archive.py   # 兼容原检查命令，运行相同拆图测试
python demo.py                 # 生成新演示目录，不覆盖旧演示
```

演示用自己画的 24 张图合成 25 段内容。程序先输出可靠图与待判断片段，再由测试夹具为已知完整的短暂画面提交图片，验证恢复后的总数与来源。
这是对流程和帧位置的验证，不冒充真实模型的视觉判断评测。

## 使用边界

只归档自己的主页或获得作者许可的内容，遵守平台约定。下载、截图不改变原作者权利；本工具不提供绕过验证、破解或多账号批量抓取。
接口可能变化，下载能否成功取决于平台响应；离线测试通过不代表真实下载已通过。
代码随仓库使用 MIT；运行依赖 f2（Apache-2.0）、browser-cookie3（LGPL-3.0）、Pillow（MIT-CMU）与 FFmpeg（LGPL/GPL 外部程序）。
