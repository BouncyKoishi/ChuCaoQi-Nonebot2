# 除草器Bot (NoneBot2 重构版)

[原项目 (NoneBot1)](https://github.com/BouncyKoishi/ChuCaoQi-Bot) 

这是除草器Bot 的 NoneBot2 重构版本，在保留原有功能的基础上，新增了 Web 管理界面，提供更好的用户体验。

## 项目简介

名为"除草器"的QQBot，采用Python编写，基于 NoneBot2 构建。

除草器发源于中山大学东方Project交流群，现主要运营一个模拟经营类游戏（生草系统），并为SYSU/SCUT系东方相关群聊提供特色服务。重构版本为生草系统新增了web游玩入口。

除草器的主群为：738721109，本群同时也是生草系统玩家交流/贸易用群聊。

## 功能列表

### Bot 功能

- **生草系统**：一个使用"草"作为货币的模拟经营&挂机游戏

* **对话模块**：与大模型进行对话，支持自定义角色配置（当前主要使用 Deepseek API）
* **抽奖模块**：由群友通过指令自行添加奖品，并提供抽奖功能
* **图库模块**：由群友上传图片到各个图库，支持随机获取图片
* **随机化模块**：提供各种模式的roll点、roll群友、选择、判断等指令
* **说点怪话**：基于用户发言，在过往群聊信息中随机/智能挑选一句话发送
* **算卦模块**：提供基于铜钱起卦法的在线算卦、解卦功能
* **台风查询**：查询当前正在活跃的台风信息（目前仅限西tai'p'y）
* **雷达回波**：查询中国境内部分雷达站的最新雷达回波图
* **图片搜索**：通过聚合搜图引擎搜索图片来源
* **音乐搜索**：根据名字从网易云音乐搜索相关音乐信息

### Web 管理界面

- 用户登录（Token认证）
- 仓库查看（草、草之精华、财产、道具）
- 生草功能（种植、收获）
- 商店系统（购买物品）
- G市查看与交易
- 能力系统（查看和使用生草能力）
- 抽奖系统（参与抽奖活动）
- 统计系统（查看生草统计数据）

## 项目结构

```
ChuCaoQi-Web/
├── backend/              # Web 后端 (FastAPI)
│   ├── middleware/       # 中间件（限流、认证等）
│   ├── routers/          # API 路由
│   ├── common.py         # 共享配置
│   ├── main.py           # FastAPI 入口
│   └── websocket_manager.py  # WebSocket 管理
├── bot/                  # Bot 主目录 (NoneBot2)
│   ├── config/           # 配置文件
│   ├── dbConnection/     # 数据库连接与模型
│   ├── plugins/          # 插件目录
│   ├── services/         # 服务层（业务逻辑）
│   ├── text/             # 文本资源
│   ├── bot.py            # Bot 入口
│   └── config.py         # NoneBot2 配置
├── src/                  # Web 前端 (Vue 3 + TypeScript)
│   ├── api/              # API 接口封装
│   ├── router/           # 路由配置
│   ├── stores/           # Pinia 状态管理
│   ├── types/            # TypeScript 类型定义
│   ├── views/            # 页面组件
│   └── main.ts           # 入口文件
├── package.json          # 前端依赖
├── vite.config.ts        # Vite 配置
└── tsconfig.json         # TypeScript 配置
```

<br />

## 安装与运行

### 前置要求

- Node.js 16+
- Python 3.8+
- NapCatQQ（用于连接QQ）

### 配置文件

1. **Bot 配置文件**

   复制示例配置并修改：
   ```bash
   cp bot/config/plugin_config.example.yaml bot/config/plugin_config.yaml
   ```
   编辑 `bot/config/plugin_config.yaml`，填入必要的配置：
   - QQ号、群号等基础信息
   - 各API密钥（OpenAI、Deepseek、Gemini等，按需填写）
   - 代理设置（如需要）
2. **数据库初始化**

   在 `bot/database/` 目录下创建 SQLite 数据库：
   ```bash
   # 创建数据库目录
   mkdir -p bot/database

   # 导入初始化数据
   sqlite3 bot/database/chuchu.sqlite < bot/config/initialize.sql
   ```

### 安装依赖

**Bot 端依赖：**

```bash
cd bot
pip install -r requirements.txt
```

**Web 后端依赖：**

```bash
cd backend
npm install
```

**Web 前端依赖：**

```bash
npm install
```

### 运行服务

**启动 Bot：**

```bash
cd bot
python bot.py
# 或使用虚拟环境
.\venv\Scripts\python.exe bot.py
```

**启动 Web 后端：**

```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

**启动 Web 前端：**

```bash
npm run dev
```

**一键启动（Windows）：**

```bash
./start.bat
```

### 访问地址

- Web 前端：`http://localhost:5173`（开发模式）
- Web 后端 API：`http://localhost:8000`
- API 文档：`http://localhost:8000/docs`

## Web 端登录

Web 端使用 Token 认证，获取方式：

1. 在 Bot 中私聊发送 `!生成token`
2. Bot 会返回一个 Token
3. 在 Web 登录页面输入 QQ号 和 Token 即可登录

## 注意事项

1. **数据库共享**：Web 端与 Bot 端共享同一个数据库，所有操作会实时同步
2. **端口占用**：确保以下端口未被占用
   - 5173（前端开发服务器）
   - 8000（后端 API）
   - 8080（NoneBot2 默认端口）

## 声明

本项目仅供学习交流使用，不得用于非法用途。

## 支持开发

[爱发电](https://afdian.com/a/chu-chu)
