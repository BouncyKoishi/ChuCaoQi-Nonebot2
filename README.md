# 生草系统 Web 项目

这是一个用于复刻除草器Bot生草系统功能的Web项目，可以在除草器被封号时临时访问生草系统并进行基础操作。

## 项目结构

```
ChuCaoQi-Web/
├── backend/              # 后端API服务
│   ├── backup_old_api/   # 旧API备份
│   ├── bot_api_gateway.py  # API网关
│   ├── bot_api_server.py   # FastAPI主程序
│   └── config.json        # 配置文件
├── bot/                  # 除草器Bot核心代码
│   ├── config/           # 配置文件
│   ├── database/         # 数据库文件
│   ├── dbConnection/      # 数据库连接
│   ├── plugins/           # 插件系统
│   ├── services/          # 业务逻辑服务
│   ├── bot.py             # Bot主程序
│   ├── config.py          # 配置文件
│   ├── kusa_base.py       # 生草系统基础
│   └── requirements.txt   # Bot依赖配置
├── src/                  # 前端Vue项目
│   ├── api/              # API接口封装
│   ├── router/           # 路由配置
│   ├── stores/           # Pinia状态管理
│   ├── types/            # TypeScript类型定义
│   ├── views/            # 页面组件
│   ├── App.vue           # 根组件
│   └── main.ts           # 入口文件
├── dist/                 # 前端构建输出
├── package.json          # 前端依赖配置
├── requirements.txt      # 后端依赖配置
├── vite.config.ts        # Vite配置
├── start.bat             # 启动脚本
├── stop.bat              # 停止脚本
└── README.md            # 项目说明
```

## 功能特性

- ✅ 用户登录（使用QQ号）
- ✅ 仓库查看（草、草之精华、财产、道具）
- ✅ 生草功能（种植、收获）
- ✅ 商店系统（购买物品）
- ✅ G市查看（查看G值、交易）
- ✅ 数据库共享（与除草器Bot使用同一数据库）
- ✅ 能力系统（查看和使用能力）
- ✅ 抽奖系统（参与抽奖活动）
- ✅ 统计系统（查看生草统计数据）

## 技术栈

### 前端
- Vue 3 + TypeScript
- Vite
- Element Plus UI
- Pinia (状态管理)
- Vue Router
- Axios

### 后端
- FastAPI
- SQLite (共享除草器Bot数据库)
- 除草器Bot核心模块

## 安装与运行

### 前置要求

- Node.js 16+
- Python 3.8+

### 前端安装

```bash
# 进入项目目录
cd ChuCaoQi-Web

# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build
```

前端开发服务器默认运行在 `http://localhost:3000`

### 后端安装

```bash
# 进入项目目录
cd ChuCaoQi-Web

# 安装依赖
pip install -r requirements.txt

# 运行后端服务
python backend/bot_api_server.py
```

后端API服务默认运行在 `http://localhost:8000`

### 一键启动

项目提供了一键启动脚本：

```bash
# 启动前端和后端服务
./start.bat

# 停止服务
./stop.bat
```

## 数据库配置

后端会自动连接到除草器Bot的SQLite数据库：
- 路径：`bot/database/chuchu.sqlite`

确保数据库文件存在且可访问。

## API接口说明

### 认证接口

- `POST /api/auth/login` - 用户登录
  - 参数：`{ "qq": "QQ号" }`
  - 返回：用户信息

### 用户接口

- `GET /api/user/info?qq=QQ号` - 获取用户信息

### 仓库接口

- `GET /api/warehouse?qq=QQ号` - 获取仓库信息

### 生草接口

- `GET /api/farm?qq=QQ号` - 获取生草地信息
- `POST /api/farm/plant?qq=QQ号` - 开始生草
  - 参数：`{ "kusaType": "草种类型" }`
- `POST /api/farm/harvest?qq=QQ号` - 收获草

### 商店接口

- `GET /api/shop/items` - 获取商店物品列表
- `POST /api/shop/buy?qq=QQ号` - 购买物品
  - 参数：`{ "itemName": "物品名称", "amount": 数量, "useAdvKusa": false }`

### G市接口

- `GET /api/gmarket` - 获取G市信息
- `POST /api/gmarket/buy?qq=QQ号` - 买入G
  - 参数：`{ "gType": "G类型", "amount": 数量 }`
- `POST /api/gmarket/sell?qq=QQ号` - 卖出G
  - 参数：`{ "gType": "G类型", "amount": 数量 }`

### 能力接口

- `GET /api/ability?qq=QQ号` - 获取能力信息

### 抽奖接口

- `GET /api/lottery?qq=QQ号` - 获取抽奖信息
- `POST /api/lottery/draw?qq=QQ号` - 参与抽奖
  - 参数：`{ "times": 抽奖次数 }`

### 统计接口

- `GET /api/statistics?qq=QQ号` - 获取生草统计数据

## 注意事项

1. **数据库共享**：本项目与除草器Bot共享同一个数据库，所有操作都会直接影响除草器Bot的数据，请谨慎操作。

2. **路径要求**：项目默认使用相对路径连接数据库，确保项目结构完整。

3. **依赖要求**：后端需要导入除草器Bot的模块，确保Bot代码完整且可访问。

4. **端口占用**：确保3000端口（前端）和8000端口（后端）没有被占用。

5. **生草时间**：生草时间根据草种类型而定，具体时间请参考生草页面说明。

6. **权限控制**：当前版本使用QQ号作为唯一标识，没有额外的密码验证。在生产环境中建议添加身份验证机制。

## 开发说明

该项目为除草器Bot的Web界面复刻版本，主要用于在Bot被封号时提供临时访问。所有操作都会直接修改除草器Bot的数据库，因此请谨慎操作。

### 前端开发

前端使用Vue 3 + TypeScript开发，使用Element Plus作为UI框架。主要页面包括：

- **登录页**：用户使用QQ号登录
- **仓库页**：查看用户的草、草之精华、财产和道具
- **生草页**：进行生草操作（种植、收获）
- **商店页**：购买各种物品
- **G市页**：查看G值并进行G交易
- **能力页**：查看和使用能力
- **抽奖页**：参与抽奖活动
- **统计页**：查看生草统计数据

### 后端开发

后端使用FastAPI开发，直接调用除草器Bot的核心模块进行业务逻辑处理。主要功能包括：

- 用户认证和管理
- 仓库信息查询
- 生草操作（种植、收获）
- 商店物品购买
- G市交易
- 能力系统
- 抽奖系统
- 统计系统

## 常见问题

### Q: 后端启动失败，提示找不到模块？

A: 确保所有依赖都已安装，并且Bot代码结构完整。

### Q: 前端无法连接后端？

A: 检查后端服务是否正常运行在8000端口，前端配置中的代理设置是否正确。

### Q: 数据库连接失败？

A: 确保数据库文件存在于`bot/database/chuchu.sqlite`路径，并且有读取权限。

### Q: 生草操作失败？

A: 检查是否有足够的承载力和草地，以及当前是否有草正在生长。

### Q: 抽奖失败？

A: 检查是否有足够的抽奖次数或道具。

## 许可证

本项目遵循除草器Bot的许可证。