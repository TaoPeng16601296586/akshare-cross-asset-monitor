# Windows 本地部署与启动指南

本指南用于帮助首次拿到项目代码的使用者，在一台尚未配置 Python 环境的 Windows 10 / 11 电脑上，完成 Python 安装、虚拟环境创建、项目依赖安装、Dashboard 启动及常见问题排查。

项目当前技术栈主要为：

- Python
- AKShare
- Pandas
- Streamlit

部署完成后，可以通过命令行或 BAT 文件启动项目；如使用“更新并启动”模式，还可以在打开 Dashboard 前先通过 AKShare 重新抓取最新公开市场数据。

---

## 1. 部署前准备

建议环境：

- Windows 10 / 11 64 位
- Python 3.11 或 3.12
- 可正常访问互联网
- 完整项目代码

项目目录至少应包含：

```text
akshare_cross_asset_monitor/
├─ src/
├─ dashboard/
├─ data/
├─ requirements.txt
├─ README.md
└─ start_dashboard.bat   # 如已配置
```

`.venv` 不需要从其他电脑复制，应在每台电脑本地重新创建。

---

## 2. 安装 Python

前往 Python 官方网站下载 Windows 64 位安装程序：

https://www.python.org/downloads/windows/

推荐版本：

```text
Python 3.11.x
```

或：

```text
Python 3.12.x
```

安装时务必勾选：

```text
Add python.exe to PATH
```

安装完成后，关闭原来的 CMD，重新打开一个新的 CMD 窗口。

验证：

```cmd
python --version
pip --version
```

正常情况下应返回 Python 与 pip 版本号。

---

## 3. 进入项目目录

假设项目位于：

```text
C:\Users\用户名\Desktop\akshare_cross_asset_monitor
```

在 CMD 中执行：

```cmd
cd /d "C:\Users\用户名\Desktop\akshare_cross_asset_monitor"
```

如果项目目录包含空格、中文或“副本”等字符，请保留双引号。

例如：

```cmd
cd /d "C:\Users\064540\Desktop\akshare_cross_asset_monitor - 副本"
```

进入后执行：

```cmd
dir
```

确认能够看到：

```text
src
Dashboard
requirements.txt
README.md
```

其中 Dashboard 实际目录名通常为：

```text
dashboard
```

---

## 4. 创建虚拟环境

在项目根目录执行：

```cmd
python -m venv .venv
```

创建完成后检查：

```cmd
dir .venv
```

正常应看到：

```text
Include
Lib
Scripts
pyvenv.cfg
```

---

## 5. 激活虚拟环境

CMD 中执行：

```cmd
.venv\Scripts\activate.bat
```

成功后命令行前面会出现：

```text
(.venv)
```

例如：

```text
(.venv) C:\Users\...\akshare_cross_asset_monitor>
```

---

## 6. 安装项目依赖

建议先升级 pip：

```cmd
python -m pip install --upgrade pip
```

然后安装项目依赖：

```cmd
python -m pip install -r requirements.txt
```

安装完成后，可以验证核心包：

```cmd
python -c "import akshare, pandas, streamlit; print('OK')"
```

如输出：

```text
OK
```

说明核心环境正常。

---

## 7. 首次测试 Streamlit Dashboard

先不要依赖 BAT，直接测试：

```cmd
python -m streamlit run dashboard\app.py
```

正常情况下会显示：

```text
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
```

如果浏览器未自动打开，可以手动访问命令行显示的 Local URL。

如果 8501 已被占用，Streamlit 可能自动使用：

```text
8502
8503
...
```

此时以实际显示的 Local URL 为准。

测试完成后，可在 CMD 中按：

```text
Ctrl + C
```

停止 Streamlit。

---

## 8. 测试数据更新

如果需要重新抓取最新公开数据，可执行：

```cmd
python -u src\run_all.py
```

该脚本会依次调用项目中的权益、债券、商品、外汇和宏观数据模块。

需要注意，不同数据源更新频率不同：

- A 股完整日线通常在收盘后形成；
- 外汇部分接口可以盘中更新；
- 债券和资金面部分数据在日终更稳定；
- PMI、CPI、PPI、M2、社融等宏观指标仅在官方发布新统计值时更新。

因此：

> 系统运行日期不等于数据统计日期。

项目不应为了展示效果，把所有数据强制标记为当天日期。

---

## 9. BAT 一键更新并启动 Dashboard

建议将 `start_dashboard.bat` 放在项目根目录，与 `src`、`dashboard`、`requirements.txt` 同一级。

推荐内容：

```bat
@echo off
setlocal

cd /d "%~dp0"

title AKShare Cross Asset Monitor

echo ==========================================
echo AKShare Cross Asset Monitor
echo ==========================================
echo.
echo Project path:
echo %CD%
echo.

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found.
    echo.
    echo Expected:
    echo %CD%\.venv\Scripts\python.exe
    echo.
    pause
    exit /b 1
)

echo Updating latest data...
echo.

".venv\Scripts\python.exe" -u src\run_all.py

echo.
echo Data update finished.
echo Starting Streamlit...
echo.

".venv\Scripts\python.exe" -m streamlit run dashboard\app.py

pause
```

关键语句：

```bat
cd /d "%~dp0"
```

表示自动进入 BAT 文件所在目录，因此无需写死：

```text
C:\...
D:\...
F:\...
```

项目移动到其他目录后，BAT 仍可继续使用。

---

## 10. 建议额外保留“仅启动 Dashboard”版本

为了现场演示稳定，建议保留：

```text
start_dashboard_only.bat
```

内容：

```bat
@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Python virtual environment not found.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m streamlit run dashboard\app.py

pause
```

两个 BAT 的使用区别：

| 文件 | 功能 | 推荐场景 |
|---|---|---|
| `start_dashboard.bat` | 更新数据 + 启动 Dashboard | 日常使用、展示前更新 |
| `start_dashboard_only.bat` | 直接读取本地已有数据 | 现场网络不稳定、仅展示 |

现场汇报建议提前完成一次数据更新，并确认页面正常；正式汇报时如网络条件一般，可直接启动已有 Dashboard。

---

## 11. 常见问题

### 11.1 系统找不到指定的驱动器

原因：BAT 中写死了不存在的盘符，例如：

```bat
cd /d F:\akshare_cross_asset_monitor
```

处理：改成：

```bat
cd /d "%~dp0"
```

---

### 11.2 Python virtual environment not found

说明当前项目目录不存在：

```text
.venv\Scripts\python.exe
```

处理：

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

---

### 11.3 python 不是内部或外部命令

通常说明：

- Python 尚未安装；或
- 安装 Python 时没有加入 PATH。

重新安装 Python，并勾选：

```text
Add python.exe to PATH
```

安装完成后重新打开 CMD。

---

### 11.4 Streamlit 使用 8502 / 8503

说明默认 8501 已被其他进程占用。

这并不代表项目异常，直接使用命令行显示的：

```text
Local URL
```

即可。

---

### 11.5 BAT 出现乱码或奇怪命令

例如：

```text
'nitor' 不是内部或外部命令
```

通常是 BAT 文件编码或复制格式异常。

建议：

- BAT 尽量使用纯英文提示文本；
- 确认文件后缀是真正的 `.bat`，不是 `.bat.txt`；
- 使用记事本或 VS Code 保存。

---

### 11.6 部分 AKShare 接口报错

AKShare 是对公开数据源的接口封装，上游网页或接口偶尔可能暂时不可用。

建议：

1. 检查其他模块是否正常完成；
2. 查看运行日志；
3. 单独运行对应模块；
4. 稍后重新尝试；
5. 不要人为填造缺失数据。

例如：

```cmd
python -u src\equity.py
python -u src\fixed_income.py
python -u src\commodity.py
python -u src\fx.py
python -u src\macro.py
```

---

## 12. 推荐部署完成检查清单

完成以下项目即可认为本地部署成功：

- [ ] `python --version` 正常返回版本号
- [ ] `.venv\Scripts\python.exe` 存在
- [ ] `requirements.txt` 安装完成
- [ ] `akshare`、`pandas`、`streamlit` 可以正常 import
- [ ] `python -m streamlit run dashboard\app.py` 可以正常打开页面
- [ ] `python -u src\run_all.py` 可以运行主要数据模块
- [ ] 双击 `start_dashboard.bat` 可以完成更新并打开 Dashboard

---

## 13. GitHub 与本地环境的关系

GitHub 主要保存：

- Python 源代码
- Dashboard 代码
- README / 部署文档
- requirements.txt
- 数据口径和质量检查逻辑

不建议上传：

```text
.venv/
.env
*.key
*.log
data/raw/ 大量 CSV
data/processed/ 大量 CSV
```

这些内容应通过 `.gitignore` 排除。

在一台新的电脑上部署时，标准流程应始终是：

```text
获取 GitHub 项目代码
        ↓
安装 Python
        ↓
创建本地 .venv
        ↓
安装 requirements.txt
        ↓
运行数据更新
        ↓
启动 Streamlit Dashboard
```

这样可以保证项目具有较好的可迁移性和可维护性。

---

## 14. 项目当前阶段说明

本项目当前仍处于数据基座建设阶段，重点是：

- 数据来源明确
- 日期正确
- 单位清晰
- 统计口径可解释
- Raw / Processed 可追溯
- Dashboard 可稳定运行

当前阶段不以模型预测或自动投资建议为核心。

未来将在稳定的数据基座之上进一步扩展：

- 债券资金面与机构行为
- 票据、ABS、REITs 等另类固收数据
- 政策与新闻文本
- 雪球、东方财富股吧等社交媒体热度与情绪数据
- AI Agent 市场状态分析与另类固收投资判断辅助

项目原则：

> 数据质量优先于模型复杂度，客观事实层与投资判断层严格分离。
