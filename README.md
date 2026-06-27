# Agnes AI Creator

基于 [Agnes AI](https://agnes-ai.com/) 的自托管多模态 Web 客户端，支持 **AI 对话**、**文生图 / 图生图**、**文生视频 / 图生视频**，生成结果自动上传至七牛云对象存储。

> 免费使用 Agnes AI 模型 · Vue 3 + FastAPI 全栈 · 毛玻璃现代 UI

## 功能特性

| 模块 | 能力 |
|------|------|
| **文本对话** | 新建 / 切换对话、流式输出、Thinking 模式、Token 与耗时统计 |
| **图片生成** | 文生图、单图编辑、多图合成；支持 `agnes-image-2.0-flash` / `agnes-image-2.1-flash` |
| **视频生成** | 文生视频、图生视频、多图视频、关键帧动画；后台异步轮询任务状态 |
| **媒体存储** | 图片 / 视频生成结果自动转存七牛云，持久化历史记录 |

### 支持的模型

| 类型 | 模型 |
|------|------|
| 文本 | `agnes-2.0-flash` |
| 图片 | `agnes-image-2.0-flash`、`agnes-image-2.1-flash` |
| 视频 | `agnes-video-v2.0` |

## 技术栈

- **前端**: Vue 3 · Vite · Vue Router · Tailwind CSS
- **后端**: Python 3 · FastAPI · httpx · APScheduler
- **数据库**: SQLite（零配置，首次启动自动建表）
- **对象存储**: 七牛云
- **AI 接口**: [Agnes AI OpenAI 兼容 API](https://agnes-ai.com/doc/overview)

## 环境要求

- Python 3.10+
- Node.js 18+
- [Agnes AI API Key](https://platform.agnes-ai.com/)（免费申请）
- 七牛云对象存储（用于保存生成结果，可选但推荐）

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/<your-username>/agnes-ai-creator.git
cd agnes-ai-creator
```

### 2. 配置环境变量

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`：

| 变量 | 说明 |
|------|------|
| `AGNES_API_KEY` | Agnes AI API Key（必填） |
| `AGNES_BASE_URL` | API 地址，默认 `https://apihub.agnes-ai.com` |
| `QINIU_ACCESS_KEY` | 七牛云 Access Key |
| `QINIU_SECRET_KEY` | 七牛云 Secret Key |
| `QINIU_BUCKET` | 存储桶名称 |
| `QINIU_DOMAIN` | CDN 访问域名，如 `https://xxx.example.com` |
| `QINIU_REGION` | 存储区域，如华东 `z0` |
| `DATABASE_PATH` | SQLite 路径，默认 `./database/aimodel.db` |

### 3. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 [http://localhost:5173](http://localhost:5173)

前端开发服务器会将 `/api` 请求代理至 `http://127.0.0.1:8000`。

## 生产部署

```bash
# 构建前端静态资源
cd frontend && npm run build

# 后端以生产模式运行（示例）
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

将 `frontend/dist` 交由 Nginx 等静态服务器托管，并将 `/api` 反向代理到 FastAPI 服务即可。

## API 文档

后端启动后访问 [http://localhost:8000/docs](http://localhost:8000/docs) 查看 Swagger 文档。

## 数据库

- 建表 SQL：`backend/sql/schema.sql`
- 默认数据库文件：`backend/database/aimodel.db`
- 首次启动时自动初始化，包含对话、消息、图片任务、视频任务、上传记录等表

## 七牛云存储路径

| 类型 | 路径 |
|------|------|
| 图片 | `data/img/` |
| 视频 | `data/video/` |
| 文档 | `data/document/` |
| 其他 | `data/other/` |

## 项目结构

```
agnes-ai-creator/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口 & 定时任务
│   │   ├── config.py            # 环境变量与模型配置
│   │   ├── database.py          # SQLite 连接与初始化
│   │   ├── schemas.py           # 请求 / 响应模型
│   │   ├── routers/             # chat / images / videos 路由
│   │   └── services/            # Agnes API、七牛云、视频轮询
│   ├── sql/schema.sql           # 数据库建表 SQL
│   ├── database/                # SQLite 数据库文件（gitignore）
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── views/               # 对话、图片、视频页面
│       ├── api/                 # API 客户端
│       └── components/          # 通用 UI 组件
└── _needs/                      # 需求与设计说明
```

## 相关链接

- [Agnes AI 官网](https://agnes-ai.com/)
- [Agnes AI 开发者文档](https://agnes-ai.com/doc/overview)
- [Agnes AI 平台（获取 API Key）](https://platform.agnes-ai.com/)
