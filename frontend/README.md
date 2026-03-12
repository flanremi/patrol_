# LangGraph 前端可视化工具

基于 Nuxt 3 构建的 LangGraph 架构可视化和交互工具。

## 🚀 功能特性

### 📊 图架构可视化
- **交互式节点图**: 使用 vis-network 展示完整的 LangGraph 架构
- **节点类型区分**: 不同颜色和形状表示不同类型的节点
- **边关系展示**: 直接边和条件边的可视化区分
- **实时交互**: 点击节点查看详细信息
- **布局切换**: 支持层次化和物理布局

### 💬 智能聊天界面
- **实时对话**: 与 LangGraph 系统进行实时交互
- **消息类型支持**: 
  - 👤 用户消息
  - 🤖 AI助手消息
  - 🔧 工具调用消息
  - ℹ️ 系统消息
- **工具调用可视化**: 详细展示工具调用过程和结果
- **快捷建议**: 预设常用对话模板
- **消息历史**: 完整的对话记录和时间戳

### 🔧 工具结果展示
- **YOLO检测结果**: 图像检测结果的详细展示
- **天气查询结果**: 格式化的天气信息展示
- **通用工具结果**: 支持任意工具的结果展示
- **展开/收起**: 详细信息的动态展示

### 📋 系统监控
- **连接状态**: 实时显示与后端的连接状态
- **节点统计**: 活跃节点数量统计
- **工具统计**: 可用工具数量统计
- **详细信息**: 节点列表和工具列表的详细展示

## 🏗️ 技术栈

- **前端框架**: Nuxt 3
- **UI框架**: Tailwind CSS
- **图形可视化**: vis-network
- **图标**: Heroicons
- **HTTP客户端**: Nuxt内置的 $fetch
- **类型支持**: TypeScript

## 📁 项目结构

```
frontend/
├── components/           # 组件目录
│   ├── ChatInterface.vue       # 聊天界面组件
│   ├── GraphVisualization.vue  # 图可视化组件
│   ├── MessageBubble.vue       # 消息气泡组件
│   ├── SystemInfo.vue          # 系统信息组件
│   └── ToolResult.vue          # 工具结果组件
├── pages/               # 页面目录
│   └── index.vue              # 主页面
├── server/api/          # API路由
│   ├── chat.post.ts           # 聊天API
│   └── status.get.ts          # 状态API
├── assets/css/          # 样式文件
│   └── main.css               # 主样式文件
├── app.vue              # 应用根组件
├── nuxt.config.ts       # Nuxt配置
├── package.json         # 依赖配置
└── tailwind.config.js   # Tailwind配置
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 启动开发服务器

```bash
npm run dev
```

前端将在 http://0.0.0.0:3000 运行

### 3. 启动后端API（可选）

```bash
cd ..
pip install fastapi uvicorn
python backend_api.py
```

后端API将在 http://0.0.0.0:8000 运行

## 🔧 配置说明

### 环境变量

在项目根目录创建 `.env` 文件：

```env
# OpenAI API配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo

# API配置
API_BASE=http://0.0.0.0:8000
```

### Nuxt配置

`nuxt.config.ts` 中的主要配置：

- **modules**: Tailwind CSS模块
- **runtimeConfig**: 运行时配置
- **css**: 全局样式文件

## 📱 响应式设计

- **桌面端**: 双列布局，图可视化和聊天界面并排显示
- **移动端**: 单列布局，组件垂直堆叠
- **平板端**: 自适应布局，优化触摸交互

## 🎨 主题定制

### 颜色系统

- **主色调**: 蓝色系 (#3b82f6)
- **成功色**: 绿色系 (#10b981)
- **警告色**: 黄色系 (#f59e0b)
- **错误色**: 红色系 (#ef4444)

### 组件样式

- **消息气泡**: 圆角设计，不同类型不同颜色
- **工具调用**: 特殊边框和背景色
- **系统信息**: 卡片式布局
- **图形可视化**: 现代化节点和边样式

## 🔌 API集成

### 聊天API

```typescript
POST /api/chat
{
  "message": "用户消息内容"
}
```

### 状态API

```typescript
GET /api/status
```

## 🐛 故障排除

### 常见问题

1. **图形不显示**: 检查 vis-network 依赖是否正确安装
2. **API连接失败**: 确认后端服务是否启动
3. **样式异常**: 检查 Tailwind CSS 配置

### 调试模式

开启开发者工具查看详细日志：

```javascript
console.log('Debug info:', debugData)
```

## 📈 性能优化

- **组件懒加载**: 大型组件按需加载
- **图片优化**: 响应式图片和懒加载
- **API缓存**: 合理的请求缓存策略
- **代码分割**: 自动的路由级代码分割

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 📄 许可证

MIT License

## 🙏 致谢

- Nuxt 3 团队
- Tailwind CSS 团队  
- vis-network 项目
- OpenAI API
