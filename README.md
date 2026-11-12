# CrossOverReset

适用于 macOS 的 CrossOver 试用记录重置脚本。默认只预览，执行修改时自动备份，并提供恢复命令。

脚本按[这篇教程](https://www.cnblogs.com/msbfb/p/20047167)的步骤实现：将 `FirstRunDate` 设置为当前时间的前 24 小时，并删除各 Bottle 的 `system.reg` 中准确匹配的 `Software\\CodeWeavers\\CrossOver\\cxoffice` 段落。

这是一次性重置操作，不会自动定时运行，也不是永久授权；再次到期时需要重新运行。参考文章未提供官方许可依据。

## 运行环境

- macOS，已安装并至少启动过一次 CrossOver。
- Python 3，仅使用标准库，无需安装第三方依赖。
- 使用 CrossOver 的默认用户目录，且已创建至少一个 Bottle。

已在 CrossOver 26.3 的本机数据上验证记录识别与预览，并通过临时数据验证备份、恢复和失败回滚。实际试用效果需要运行后自行确认；其他版本的记录格式可能不同。

## 快速开始

### 1. 下载脚本

安装 Git 的用户可在终端运行：

```bash
git clone https://github.com/SherryTTK/CrossOverReset.git
cd CrossOverReset
```

也可以在 GitHub 点击 **Code → Download ZIP**，解压后在终端进入解压目录。

检查 Python：

```bash
python3 --version
```

如果提示找不到命令，请先从 [Python 官网](https://www.python.org/downloads/macos/)安装 Python 3。

### 2. 预览

```bash
python3 crossover-trial-reset.py
```

脚本会显示计划写入的日期（UTC）和每个 Bottle 中匹配的段落数量。此命令不写入 CrossOver 配置，也不创建备份。

### 3. 执行重置

保存并退出所有 Bottle 内运行的程序（包括 Steam、游戏等），然后完全退出 CrossOver。请使用运行 CrossOver 的同一 macOS 用户执行，不要加 `sudo`：

```bash
python3 crossover-trial-reset.py --apply
```

执行时会：

1. 检查是否仍有从 `CrossOver.app/Contents/` 启动的当前用户进程；发现后停止。
2. 备份 CrossOver 偏好设置和需要修改的 `system.reg` 文件。
3. 更新 `FirstRunDate`，清除匹配的试用记录段落，并核对日期是否写入成功。
4. 输出备份位置和恢复命令。

完成后重新打开 CrossOver，检查试用状态。脚本会处理默认目录下的所有 Bottle，目前不支持只指定某一个 Bottle。进程检查不能替代手动退出程序，尤其是在应用被重命名或使用其他 Wine 运行器的情况下。

## 备份与恢复

每次使用 `--apply` 都会创建独立备份，位置为：

```text
~/Library/Application Support/CrossOver Trial Backups/时间戳/
├── preferences.plist          # 修改前的完整偏好设置
├── preferences-updated.plist  # 计划写入的偏好设置
└── Bottles/                   # 有匹配记录时才会创建
    └── Bottle名称/
        └── system.reg        # 修改前的完整注册表文件
```

恢复前同样需要退出 CrossOver 及 Bottle 内的程序。优先复制脚本输出的恢复命令，也可以手动填写备份目录：

```bash
python3 crossover-trial-reset.py --restore "$HOME/Library/Application Support/CrossOver Trial Backups/实际时间戳"
```

将 `实际时间戳` 替换为真实目录名称，并保留路径外的引号。恢复会覆盖备份所对应的完整偏好设置及注册表文件，因此备份之后对这些文件的其他修改也会被还原。

执行重置途中发生异常时，脚本会尝试回滚本次已写入的内容。若回滚失败，可使用保留的备份再次恢复。这里的备份仅包含偏好设置和相关注册表文件，不是整个 Bottle 的备份。

## 命令一览

| 命令 | 用途 |
| --- | --- |
| `python3 crossover-trial-reset.py` | 只预览，不修改 |
| `python3 crossover-trial-reset.py --apply` | 备份并重置 |
| `python3 crossover-trial-reset.py --restore "备份目录"` | 恢复指定备份 |
| `python3 crossover-trial-reset.py --help` | 查看参数说明 |

`--apply` 和 `--restore` 不能同时使用。

## 常见问题

### 提示退出 CrossOver

先关闭游戏、Steam 等 Windows 程序，再退出 CrossOver。必要时在“活动监视器”确认相关进程已结束，然后重新执行。脚本不会强制终止进程。

### 找不到 FirstRunDate 或导出偏好设置失败

确认已用当前 macOS 用户启动过 CrossOver。脚本要求 `FirstRunDate` 是日期类型；缺失或类型不符合时会停止，不会猜测或新建该记录。

### 找不到 Bottle 目录，或检测到符号链接

脚本使用固定目录 `~/Library/Application Support/CrossOver/Bottles`。自定义存储位置或符号链接布局需要先人工检查，当前版本不提供路径参数。

### 某个 Bottle 匹配到 0 个段落

该 Bottle 中没有脚本识别的试用记录，不会改写它的 `system.reg`。这不代表已获得永久授权，也不保证该版本可以重置。

### 重置后仍然过期

确认程序已完全退出后再操作，并检查输出是否有错误。CrossOver 更新可能改变试用记录机制；当前脚本不保证所有版本有效。

## 许可证

本项目使用 [GNU AGPL v3](LICENSE) 许可证。项目许可证仅适用于本仓库代码，不授予 CrossOver 的使用许可。
