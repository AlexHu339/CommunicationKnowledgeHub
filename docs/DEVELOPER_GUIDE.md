# 开发者指南

前端为 React 19 + TypeScript + Vite，后端为 FastAPI + SQLAlchemy 2 + SQLite。`CKH_ROOT` 决定数据根目录，默认由代码位置推导。

```powershell
runtime\python\Scripts\python.exe program\scripts\seed_database.py
powershell -ExecutionPolicy Bypass -File program\scripts\run_tests.ps1
```

API 文档在运行后的 `/api/docs`。新字段通过 Alembic revision 迁移，迁移前必须调用 `app.backup.create_backup('automatic', '数据库迁移前')`。不得把用户数据迁入 `program`。

公开的 AI Provider 默认配置位于 `config/ai_providers.yaml`；网页保存的本机配置写入被 Git 忽略的 `private/ai_providers.yaml`。模型 ID 和能力是数据，不得写死到业务代码。未知能力保持 `untested`，不得按名称猜测。

