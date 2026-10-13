# 数据库结构

- `knowledge_cards`：正式及候选知识卡的全部标准字段和版本。
- `learning_states`：学习状态、收藏、复习日期、浏览次数。
- `notes`、`relationships`：个人笔记和跨课程关系。
- `review_items`：网络、AI、导入和图像说明的隔离审核队列。
- `policies`、`university_programs`、`source_records`：考研政策、院校专业和来源版本。
- `ai_conversations`、`ai_messages`、`ai_usage`：多轮上下文、持久消息和费用审计。
- `user_accounts`、`auth_sessions`：Argon2id 密码哈希和到期会话。
- `media_assets`：本地媒体路径、许可证、来源和 OCR 文字；不存图片二进制。
- `app_settings`：非秘密运行设置。API Key 不进入数据库。

SQLite 固定路径为 `userdata/database/main.sqlite3`，启用外键、WAL 和 busy timeout。

