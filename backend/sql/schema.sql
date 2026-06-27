-- Agnes AI Platform SQLite Schema
-- 数据库: aimodel.db

-- 对话表
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '新对话',
    model TEXT NOT NULL DEFAULT 'agnes-2.0-flash',
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- 消息表
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('system', 'user', 'assistant')),
    content TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    model TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);

-- 图片生成任务表
CREATE TABLE IF NOT EXISTS image_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL,
    mode TEXT NOT NULL CHECK(mode IN ('text2img', 'img2img', 'multi_img')),
    prompt TEXT NOT NULL,
    size TEXT NOT NULL,
    input_images TEXT,
    output_url TEXT,
    qiniu_url TEXT,
    revised_prompt TEXT,
    duration_ms INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT,
    request_params TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_image_tasks_status ON image_tasks(status);
CREATE INDEX IF NOT EXISTS idx_image_tasks_created_at ON image_tasks(created_at DESC);

-- 视频生成任务表
CREATE TABLE IF NOT EXISTS video_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model TEXT NOT NULL DEFAULT 'agnes-video-v2.0',
    mode TEXT NOT NULL CHECK(mode IN ('text2video', 'img2video', 'multi_img', 'keyframes')),
    prompt TEXT NOT NULL,
    negative_prompt TEXT,
    task_id TEXT,
    video_id TEXT,
    width INTEGER DEFAULT 1152,
    height INTEGER DEFAULT 768,
    num_frames INTEGER DEFAULT 121,
    frame_rate REAL DEFAULT 24,
    num_inference_steps INTEGER,
    seed INTEGER,
    input_images TEXT,
    output_url TEXT,
    qiniu_url TEXT,
    status TEXT NOT NULL DEFAULT 'queued' CHECK(status IN ('submitting', 'queued', 'in_progress', 'completed', 'failed')),
    progress INTEGER DEFAULT 0,
    seconds TEXT,
    size TEXT,
    duration_ms INTEGER DEFAULT 0,
    error_message TEXT,
    request_params TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_video_tasks_status ON video_tasks(status);
CREATE INDEX IF NOT EXISTS idx_video_tasks_video_id ON video_tasks(video_id);
CREATE INDEX IF NOT EXISTS idx_video_tasks_created_at ON video_tasks(created_at DESC);

-- 应用配置（键值对）
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

-- Agnes AI API Key 配置表
CREATE TABLE IF NOT EXISTS api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    api_key TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0 CHECK(is_active IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);

-- 上传文件记录表
CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    original_name TEXT,
    qiniu_key TEXT NOT NULL,
    qiniu_url TEXT NOT NULL,
    file_type TEXT NOT NULL CHECK(file_type IN ('img', 'video', 'document', 'other')),
    size_bytes INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);
