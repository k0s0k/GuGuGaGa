# 开发指南

[返回 README](../README.md)

## 环境与启动

| 组件 | 要求 |
| --- | --- |
| Python | 3.10+，后端使用标准库 |
| Node.js | 推荐 22+，用于前端安装与构建 |
| C++ 编译器 | 支持 C++17 的 g++ 或 clang++ |
| 桌面窗口 | Windows WebView2；启动器也支持浏览器界面 |

Windows 双击 `start.cmd` 可检查环境、按需构建并启动。PowerShell 支持指定端口与数据库：

```powershell
.\start.ps1 -Rebuild
.\start.ps1 -Port 8877 -Data ".local\my-progress.db"
```

前端热更新使用两个终端：

```powershell
# 终端 1：后端
python -m server.app
```

```powershell
# 终端 2：前端
npm ci
npm run dev -- --port 5173 --strictPort
```

开发页面为 `http://127.0.0.1:5173`，Vite 将 `/api` 代理到后端 `8766`。服务监听本机地址，校验 Host、Origin 与会话令牌。后端重启后刷新页面以更新会话。

## C++ 工具链

便携工具链安装到项目的 `.local/toolchains/w64devkit`，应用会自动识别：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-cpp.ps1
```

也可通过环境变量指定已有编译器：

```powershell
$env:CODERECALL_CXX = "C:\msys64\ucrt64\bin\g++.exe"
python -m server.app
```

变量值为编译器可执行文件的完整路径。运行器使用 `-std=c++17 -O2`，提供时间、输出大小和并发限制。代码以当前系统账户权限在本机运行，请运行自己理解并信任的代码。

## 构建与测试

```powershell
# TypeScript 校验及生产构建
npm run build

# 后端、调度、导入与本地接口测试
python -m unittest discover -s tests -v

# 浏览器交互测试
npm run test:ui

# 参考答案回归：Python / C++ × LeetCode / ACM
python scripts/verify_content.py --styles brief annotated

# 按语言与题号检查
python scripts/verify_content.py --languages python --ids 4 94 208
```

答案回归通过实际运行器执行，报告默认保存到 `.local/content-verification.json`；可用 `--report` 指定输出路径。C++ 全量回归会进行逐题编译。

Windows 桌面打包：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup-cpp.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build-desktop.ps1
```

构建脚本在 `.local/package-env` 准备桌面依赖，校验嵌入式 Python，输出 `release/GuGuGaGa-v2.2.0/`。`-SkipInstall` 复用打包依赖，`-SkipFrontend` 复用前端构建。发行目录包含运行环境、快捷方式脚本、知识库模板与第三方许可证。

## 数据、备份与兼容

| 场景 | 数据库 |
| --- | --- |
| GuGuGaGa / CodeRecall 2 桌面版 | `%LOCALAPPDATA%\CodeRecall-v2\coderecall.db` |
| 当前源码运行 | `.local/coderecall-v2.db` |
| CodeRecall 1 桌面版 | `%LOCALAPPDATA%\CodeRecall\coderecall.db` |

桌面版使用持续兼容的数据目录与单实例协议。首次建立新版数据库时，会查找同项目源码数据和旧版数据，用 SQLite 一致性备份复制，再升级副本。原有数据和 Git 标签可用于历史版本回溯。

完整备份使用版本 2 JSON，支持恢复版本 1 与版本 2 备份。导入先校验，并将当前状态备份到数据库目录的 `before-import-时间-标识.json`，再用事务写入；恢复时可重新导入该文件。知识库交换文件使用独立的 `coderecall.knowledge` 协议，详见 [知识库导入格式](knowledge-format.md)。

指定数据位置：

```powershell
python -m server.app --data "D:\GuGuGaGaData\progress.db"
```

Git 保存源码和构建说明；本机数据、运行环境与生成产物由 `.gitignore` 管理。

## 复习与时间规则

调度器结合记忆稳定性与四档反馈安排间隔，估计保留率为 `R(t) = 0.9^(t/S)`。首次「有点模糊 / 记住了 / 很熟练」对应初始稳定性 0.5 / 1 / 4 天；选择「忘记了」安排 10 分钟后重学。按天间隔为 1–365 天，更高目标保留率会缩短后续间隔。

到期时间按带时区的 ISO 时间存储并以 UTC 计算；日历和打卡按后端所在电脑的本地日期记录。同一内容当天计入一个完成名额，每次反馈分别更新复习进度，事件 ID 用于去重。

## 项目结构

```text
content/       Hot100 题意、样例与 Python / C++ 参考答案
server/        本地 API、运行器、复习调度、SQLite 与知识导入
src/           React + TypeScript 界面
public/        图标、知识库模板与 JSON Schema
docs/          使用与开发文档
tests/         后端及浏览器测试
scripts/       工具链安装、答案回归与桌面构建
packaging/     Windows 打包配置与资源
desktop.py     桌面窗口、本地服务与单实例入口
start.cmd      Windows 源码启动入口
```
