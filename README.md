# 🎶 Music Tagger (音乐标签与封面自动处理工具)

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)

一个轻量级、智能化的命令行音乐元数据（ID3 / Vorbis Tags）批量整理工具。支持根据文件名自动提取元数据、联网匹配下载高清专辑封面与 LRC 歌词、擦除旧有乱码标签，以及规范化批量重命名文件。
使用 Gemini 3.1Pro 辅助生成，可能存在Bug。

---

## ✨ 核心特性

- 🧹 **彻底清除乱码与旧标签**：支持一键抹除 MP3/FLAC 中乱码或非标准的冗余元数据，不破不立。
- 🏷️ **智能文件名解析**：内置正则表达式，自动提取 `艺术家 - 歌曲名`（兼容短横线 `-`、下划线 `_` 等分隔符），并支持自定义正则匹配。
- 🌐 **网络自动配对**：
  - 自动向 **iTunes API** 请求并嵌入最高 1000x1000 的高清专辑封面。
  - 自动向 **LRCLIB API** 获取嵌入同步滚动歌词（LRC）或纯文本歌词。
- 📁 **安全重命名**：支持将非标准文件名统一清洗重命名为 `艺术家 - 歌曲名.后缀`，并自动过滤 Windows 非法字符。
- 🛡️ **试运行预览模式 (Dry Run)**：默认开启安全预览，在不实际修改/改名任何文件的前提下预检匹配结果，防误操作。
- 💻 **交互式 CLI 菜单**：零命令行参数负担，运行后通过终端提示一键配置，上手即用。

---

## 📦 支持格式

| 音频格式 | 基础标签 (Artist/Title) | 嵌入封面 (Cover) | 嵌入歌词 (Lyrics) | 抹除乱码旧标签 |
| :--- | :---: | :---: | :---: | :---: |
| **MP3** (`.mp3`) | ✅ | ✅ | ✅ | ✅ |
| **FLAC** (`.flac`) | ✅ | ✅ | ✅ | ✅ |
| **APE** (`.ape`) | ✅ | ❌ | ❌ | ✅ |
| **M4A / OGG** | ✅ | ❌ | ❌ | ✅ |

---

## 🚀 快速开始

### 方式一：直接运行源码 (需要 Python 环境)

1. **克隆仓库**
   ```bash
   git clone https://github.com/quanjindeng/music-tagger.git
   cd music-tagger
   ```

2. **安装依赖**
   ```bash
   pip install mutagen requests
   ```

3. **启动程序**
   ```bash
   python music_tagger.py
   ```

---

### 方式二：双击运行 `.exe` (无需 Python 环境)

你可以直接前往 [Releases页面](../../releases) 下载最新打包好的 `music_tagger.exe` 文件：
1. 双击打开 `music_tagger.exe`。
2. 按照控制台终端的提示输入目标音乐文件夹路径。
3. 根据提示完成配置，按回车即可自动处理。

---

## 🛠️ 打包指南 (开发者)

如果你想自行将 Python 脚本打包为独立的 Windows `.exe` 单文件，可使用 PyInstaller：

```bash
pip install pyinstaller
pyinstaller -F music_tagger.py
```
打包成功后，可执行文件将生成于 `dist/music_tagger.exe`。

---

## 📖 推荐使用流程

1. **第一轮：开启【试运行模式】**
   运行程序，全选 `Y` 保持默认配置。观察控制台输出，确认文件名的艺术家和歌曲名提取无误。
2. **第二轮：开启【正式修改】**
   重新运行程序，在前几项配置保持 `Y` 的情况下，在最后一项 `[6] 试运行模式` 中选择 `n`，程序将正式开始修改文件标签与重命名。

---

## 📄 开源许可

本项目基于 [MIT License](LICENSE) 开源。欢迎提交 Pull Request 或 ISSUE 来改进本项目！
