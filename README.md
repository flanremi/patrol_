# LangGraph 智能对话系统 - 使用指南

本文档将从零开始，详细说明如何在全新的电脑上搭建和运行这个项目。

## 📋 项目概述

这是一个基于 LangGraph 的智能对话系统，采用前后端分离架构：

- **前端**：使用 Nuxt3 框架构建的现代化 Web 界面，提供图架构可视化和对话交互功能
- **后端**：基于 FastAPI 的 Python 服务器，集成 LangGraph 实现智能对话处理流程

## 🔧 环境要求

在开始之前，请确保您的电脑满足以下要求：

### 必需环境
- **Python 3.8+**（推荐 Python 3.9 或更高版本）
- **Node.js 18+**（推荐使用 LTS 版本）
- **npm**（通常随 Node.js 一起安装）或 **yarn**

### 可选工具
- **Git**（用于克隆项目，如果您是从 Git 仓库获取项目）

## 🚀 快速开始

### 第一步：获取项目代码

如果您使用的是 Git：

```bash
git clone <项目仓库地址>
cd patrol_demo_2
```

或者直接解压项目压缩包到本地目录。

### 第二步：配置 Python 后端环境

#### 2.1 安装 Python

**Windows 系统：**
1. 访问 [Python 官网](https://www.python.org/downloads/)
2. 下载最新版本的 Python（推荐 3.9 或更高峰值）
3. 运行安装程序，**务必勾选 "Add Python to PATH"**
4. 完成安装后，打开 PowerShell 或命令提示符，验证安装：
   ```bash
   python --version
   ```
   或
   ```bash
   python3 --version
   ```

**macOS 系统：**
```bash
# 使用 might 安装
brew install python3

# 或从官网下载安装包安装
```

**Linux 系统：**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip

# CentOS/RHEL
sudo yum install python3 python3-pip
```

#### 2.2 安装项目依赖

打开终端（PowerShell/CMD 在 Windows，Terminal 在 macOS/Linux），进入项目根目录：

```bash
# 确保在项目根目录
cd D:\git\patrol_demo_2  # Windows 示例路径

# 安装 Python 依赖包
pip install -r requirements.txt
```

如果使用 `pip3` 命令：
```bash
pip3 install -r requirements.txt
```

**常见问题解决：**

如果遇到权限问题（Windows）：
```bash
python -m pip install -r requirements.txt
```

如果遇到权限问题（macOS/Linux）：
```bash
pip3 install --user -r requirements.txt
```

或者使用虚拟环境（推荐）：
```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

#### 2.3 配置环境变量

在项目根目录创建 `.env` 文件（如果不存在），添加以下配置：

```env
# OpenAI API 配置
OPENAI_BASE_URL=https://api.openai.com/v1
# 或使用其他兼容的 API 服务地址，例如：
# OPENAI_BASE_URL=https://your-api-proxy.com/v1

# API Key（根据实际情况配置）
# OPENAI_API_KEY=your-api-key-here
```

**注意：**
- `.env` 文件应该放在项目根目录（与 `backend_api2.py` 同级）
- 如果使用其他 LLM 服务，请根据服务提供商的文档配置相应的 `OPENAI_BASE_URL`
- API Key 的配置方式可能因您使用的 LLM 服务而异，请参考 `langgraph_helper.py` 中的配置方式

#### 2.4 启动后端服务器

在项目根目录执行：

```bash
python backend_api2.py
```

或者：

```bash
python3 backend_api2.py
```

**成功启动的标志：**

您应该看到类似以下的输出：

```
🚀 启动LangGraph测试API服务器...
📍 API地址: http://localhost:8001
📚 API文档: http://localhost:8001/docs
🔧 状态检查: http://localhost:8001/status

✅ LangGraph初始化成功 - 使用串联结构：需求诊断智能体 -> 规划与策略智能体 -> 数据分析与洞察智能体 -> 报告生成智能体
✅ 使用 uvicorn 启动服务器...
INFO:     Started server process [xxxxx]
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

**验证后端是否正常运行：**

打开浏览器访问：
- http://localhost:8001/status - 查看系统状态
- http://localhost:8001/docs - 查看 API 文档（Swagger UI）

### 第三步：配置和启动前端

#### 3.1 安装 Node.js

**Windows 系统：**
1. 访问 [Node.js 官网](https://nodejs.org/)
2. 下载 LTS 版本（推荐）
3. 运行安装程序，按照提示完成安装
4. 打开 PowerShell 验证安装：
   ```bash
   node --version
   npm --version
   ```

**macOS 系统：**
```bash
# 使用 Homebrew
brew install node

# 或从官网下载安装包
```

**Linux 系统：**
```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# CentOS/RHEL
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs
```

#### 3.2 安装前端依赖

打开**新的终端窗口**（保持后端服务器在第一个终端运行），进入前端目录：

```bash
cd frontend
```

安装依赖包：

```bash
npm install
```

**安装过程可能需要几分钟**，请耐心等待。

**常见问题解决：**

如果网络较慢，可以使用国内镜像源：

```bash
# 使用淘宝镜像
npm install --registry=https://registry.npmmirror.com
```

如果遇到权限问题（macOS/Linux）：
```bash
sudo npm install
```

#### 3.3 启动前端开发服务器

在前端目录执行：

```bash
npm run dev
```

**成功启动的标志：**

您应该看到类似以下的输出：

```
Nuxt 3.8.0 with Nitro 2.6.4

  ➜ Local:    http://localhost:3000/
  ➜ Network:  http://192.168.x.x:3000/
  ➜ Nuxt DevTools: enabled

✔ Vite client built in xxxms
✔ Nitro built in xxxms
```

**注意：** 
- 前端默认运行在 `http://localhost:3000`
- 确保后端服务器（8001 端口）已启动，否则前端无法正常工作

## 🎯 使用项目

### 访问应用

1. 确保后端服务器正在运行（终端窗口1，端口 8001）
2. 确保前端服务器正在运行（终端窗口2，端口 3000）
3. 打开浏览器，访问：**http://localhost:3000**

### 主要功能

1. **图架构可视化**：左侧面板显示 LangGraph 的完整架构图，包括节点、边和路由关系
2. **智能对话**：右侧聊天界面支持与智能体进行对话交互
3. **工作流视图**：点击右上角"工作流视图"按钮可以查看更详细的工作流信息
4. **实时状态**：底部面板显示系统连接状态、节点数量等信息

### 测试对话

在聊天界面输入问题，例如：
- "检查3号线路K25+300区段的轨道螺栓状态"
- "分析巡逻图片中的故障"
- 其他与系统相关的查询

系统会通过 LangGraph 的四个智能体 Jane 联处理您的请求：
1. **需求诊断智能体**：理解用户需求，进行任务分解
2. **规划与策略智能体**：制定执行策略，选择工具
3. **数据分析与洞察智能体**：处理数据，生成检测结果
4. **报告生成智能体**：生成专业报告

## 📁 项目结构说明

```
patrol_demo_2/
├── backend_api2.py          # 后端 API 服务器入口
├── requirements.txt          # Python 依赖列表
├── .env                      # 环境变量配置（需自行创建）
│
├── langgraph_helper.py      # LangGraph 辅助工具
├── requirement_diagnosis_graph.py      # 需求诊断子图
├── planning_strategy_graph.py          # 规划策略子图
├── data_analysis_graph.py              # 数据分析子图
├── report_generation_graph.py          # 报告生成子图
│
├── frontend/                # 前端目录
│   ├── package.json         # 前端依赖配置
│   ├── nuxt.config.ts       # Nuxt3 配置文件
│   ├── pages/               # 页面文件
│   │   ├── index.vue        # 主页面
│   │   └── workflow.vue     # 工作流视图页面
│   ├── components/          # Vue 组件
│   ├── server/              # Nuxt 服务端 API
│   └── assets/              # 静态资源
│
└── chat_record/             # 聊天记录存储目录（自动创建）
```

## ⚠️ 常见问题排查

### 后端问题

**问题1：`ModuleNotFoundError: No module named 'xxx'`**
- **解决**：确保已安装所有依赖，运行 `pip install -r requirements.txt`

**问题2：`OPENAI_BASE_URL` 未配置**
- **解决**：在项目根目录创建 `.env` 文件，添加配置（参考第二步的 2.3 节）

**问题3：端口 8001 已被占用**
- **解决**：修改 `backend_api2.py` 最后Lady的端口号，或将占用端口的程序关闭

**问题4：LangGraph 初始化失败**
- **解决**：
  - 检查 `.env` 文件配置是否正确
  - 检查网络连接，确保可以访问 API 服务
  - 查看终端错误信息，根据具体错误进行排查

### 前端问题

**问题1：`npm install` 失败或很慢**
- **解决**：
  - 使用国内镜像源：`npm install --registry=https://registry.npmmirror.com`
  - 检查网络连接
  - 清除 npm 缓存：`npm cache clean --force`

**问题2：前端无法连接到后端**
- **解决**：
  - 确认后端服务器正在运行（访问 http://localhost:8001/status 测试）
  - 检查前端代码中的 API 地址配置（默认为 `http://localhost:8001`）
  - 检查防火墙设置

**问题3：端口 3000 已被占用**
- **解决**：Nuxt 会自动尝试其他端口，或者手动指定端口：
  ```bash
  npm run dev -- --port 3001
  ```

**问题4：页面显示空白或错误**
- **解决**：
  - 打开浏览器开发者工具（F12）查看控制台错误
  - 确认后端服务正常运行
  - 清除浏览器缓存并刷新页面

### 环境变量问题

**问题：找不到 `.env` 文件**
- **解决**：
  - 在项目根目录手动创建 `.env` 文件
  - 确保文件名为 `.env`（不是 `.env.txt` 或其他）
  - Windows 用户如果无法创建以点开头的文件，可以在命令行中创建：
    ```bash
    echo. > .env
    ```
    然后编辑文件添加配置

## 🔍 验证安装

### 检查后端

1. 访问 http://localhost:8001/status
   - 应该返回 JSON 格式的状态信息
   - `connected` 字段应为 `true`

2. 访问 http://localhost:8001/docs
   - 应该显示 Swagger API 文档界面

### 检查前端

1. 访问 http://localhost:3000
   - 应该显示模糊界面，包含图架构可视化面板和聊天界面

2. 检查浏览器控制台（F12）
   - 不应该有红色错误信息
   - 网络请求应该能成功连接到后端

## 🛠️ 开发模式说明

### 后端开发

- 后端使用 FastAPI，支持热重载
- 修改代码后，服务器会自动重启
- API 文档地址：http://localhost:8001/docs

### 前端开发

- 前端使用 Nuxt3，支持热模块替换（HMR）
- 修改代码后，浏览器会自动刷新
- Nuxt DevTools 已启用，可通过浏览器访问开发工具

## 📝 生产环境部署

### 后端部署

生产环境建议使用以下方式启动后端：

```bash
# 使用 uvicorn
uvicorn backend_api2:app --host 0.0.0.0 --port 8001 --workers 4

# 或使用 gunicorn + uvicorn workers
gunicorn backend_api2:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

### 前端部署

1. 构建生产版本：
   ```bash
   cd frontend
   npm run build
   ```

2. 预览生产构建：
   ```bash
   npm run preview
   ```

3. 部署到服务器：
   - 将 `frontend/.output` 目录部署到 Web 服务器（如 Nginx）
   - 配置反向代理，将 API 请求转发到后端服务器

## 📞 获取帮助

如果遇到问题：

1. 检查本文档的"常见问题排查"部分
2. 查看终端/控制台的错误信息
3. 检查浏览器开发者工具的控制台和网络面板
4. 确认所有依赖都已正确安装
5. 确认环境变量配置正确

## 📄 许可证

请查看项目根目录的 `LICENSE` 文件了解许可证信息。

---

**祝您使用愉快！** 🎉

请新建models文件夹，并将链接: https://pan.baidu.com/s/178UF7m2hEA4FZ436tAhiBg?pwd=w17a 提取码: w17a 中的模型文件下载至该文件夹后运行代码。
