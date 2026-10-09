<div align="center">

<img src="public/gugugaga-icon.png" width="112" alt="GuGuGaGa 图标" />

# GuGuGaGa

**每天一点，把知识记牢。**

把学习笔记变成知识卡，让复习成为每天的小习惯。

![Windows](https://img.shields.io/badge/Windows-桌面应用-0078D4?style=flat-square)
![Python / C++](https://img.shields.io/badge/刷题-Python%20%2F%20C%2B%2B-3776AB?style=flat-square)
![Local](https://img.shields.io/badge/学习数据-本地保存-536D59?style=flat-square)

[快速开始](#快速开始) · [功能一览](#功能一览) · [笔记导入](#笔记导入) · [开发指南](docs/development.md)

</div>

---

GuGuGaGa 是一款本地知识复习与打卡软件。无论是 C++、英语、Blender 还是 UE5，都可以建立自己的知识库，用问答、填空和实践卡片巩固记忆。内置 LeetCode Hot100 专区，让知识学习与算法练习共用一份复习计划。

![GuGuGaGa 今日学习界面（示例数据）](docs/images/overview.png)

## 功能一览

| 功能 | 你可以做什么 |
| --- | --- |
| 📚 通用知识库 | 按主题管理知识点，创建问答、填空、实践步骤，搜索、收藏与归档 |
| 📝 笔记转卡片 | 导入 Markdown / TXT，按标题拆分，或使用 AI 生成知识卡；预览编辑后保存 |
| 🔁 间隔复习 | 先回忆、再揭晓，用四档记忆反馈安排下一次复习 |
| 📅 打卡与日历 | 设置每日目标，查看完成情况、连续打卡和学习记录 |
| 💻 Hot100 练习 | Python / C++ × LeetCode / ACM，两种语言、两种答题模式与本地运行 |
| ✍️ 个人题解 | 编辑并保存简洁版、注释版和完整解析，配合 Markdown 笔记复盘 |
| 🎨 个人工作空间 | 浅色与深色主题、自定义头像、适应窗口尺寸的侧边栏 |
| 💾 备份与迁移 | 学习数据保存在本机，通过完整 JSON 备份迁移或恢复 |

## 快速开始

### 1. 打开软件

打开桌面包中的 **`GuGuGaGa.exe`**，当前构建目录为 `release/GuGuGaGa-v2.1.1/`。包内已包含 Python、C++ 工具链和界面资源。

将 **`.exe` 与 `_internal` 文件夹一起保留**。双击同目录的 **`create-shortcut.cmd`**，即可创建桌面快捷方式。

### 2. 准备学习内容

进入「我的知识库」创建主题与卡片，导入自己的笔记，或从内置示例开始。算法练习可直接进入 Hot100 题库，按专题选择题目。

点击左下角个人工作空间设置头像与每日目标。专注自己的知识库时，可关闭「每日计划包含 Hot100」。

### 3. 开始每日复习

打开「今日学习」，完成到期复习和新内容：**独立回忆 → 揭晓答案 → 选择记忆反馈**。达到每日目标后自动打卡，在日历中回看进度。

## 笔记导入

在「我的知识库」中选择导入方式，确认预览后保存：

| 方式 | 适合的内容 | 操作 |
| --- | --- | --- |
| 按标题拆分 | 已按章节整理的 Markdown / TXT | 导入文件或粘贴文本，生成卡片预览 |
| AI 拆分 | 需要提炼重点的学习笔记 | 填写 API 地址、模型和 Key，生成并调整卡片 |
| JSON 导入 | 已整理好的知识库，或其他工具生成的卡片 | 按标准格式导入，校验后保存 |

AI 拆分兼容 **Chat Completions API**，支持远程 HTTPS 服务及本机模型服务。点击生成时，笔记会发送到填写的服务地址，费用按该服务规则计算；Key 仅用于当前会话与请求。

[下载 JSON 模板](public/knowledge-template.json) · [JSON Schema](public/knowledge-schema.json) · [导入格式](docs/knowledge-format.md) · [文档与 AI 拆分指南](docs/document-import.md)

## Hot100 工作台

每题提供题意、样例、输入协议与三层答案：**简洁代码、中文注释、完整解析**。个人题解按题目、语言和模式分别保存，便于整理适合自己的写法。

| 操作 | 快捷键 |
| --- | --- |
| 换行并按语法缩进 | `Enter` |
| 接受补全 / 缩进 | `Tab` |
| 减少缩进 | `Shift + Tab` |
| 打开补全列表 | `Ctrl + Space` |

LeetCode 模式编写指定函数或类；ACM 模式编写完整标准输入输出程序。用内置样例或自定义输入运行代码，也可通过题目链接前往原站提交。

## 数据与升级

学习进度、题解、笔记、头像和设置保存在本机。更换电脑时，在「偏好设置」中导出完整备份，再到新设备导入。导入前会自动保存当前数据，便于恢复。

GuGuGaGa 沿用 CodeRecall 2 的学习数据。升级时先退出正在运行的旧版，再打开新版；移动程序时复制整个程序文件夹。知识库 JSON 用于合并学习内容，完整备份用于迁移全部个人数据。

## 从源码运行

准备 **Python 3.10+** 和 **Node.js 22+**，在项目根目录执行：

```powershell
npm ci
npm run build
python -m server.app
```

打开 **[http://127.0.0.1:8766](http://127.0.0.1:8766)**。Windows 也可以双击根目录的 `start.cmd`。C++ 源码运行需配置支持 C++17 的编译器。

热更新、桌面打包、测试与数据目录说明见 [开发指南](docs/development.md)。

## 参考与致谢

[LeetCode Hot100](https://leetcode.cn/studyplan/top-100-liked/) 提供题目入口，[代码随想录](https://github.com/youngyangyang04/leetcode-master) 启发专题组织，[SSP-MMC](https://github.com/maimemo/SSP-MMC) 提供间隔重复研究参考。项目使用 React、Vite、CodeMirror、Lucide 等开源工具构建。

README 的信息组织参考 [Zotero Agents](https://github.com/leike0813/zotero-agents)。
