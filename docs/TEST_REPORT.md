# 测试报告

执行日期：2026-08-07；核心状态：通过。真实 DeepSeek / OpenAI 调用因未提供真实密钥而保持“待用户配置后验收”，未伪造通过结果。

## 自动化结果

- `pytest program/tests -q`：21 passed，0 failed。
- 内容：406 个去重知识主题全部完成通俗正文导入；594 个旧 ID 别名完整；同学科重复标题 0；重复正文 0；缺来源 0；1000 个旧 ID 覆盖率 100%。
- 前端：TypeScript 严格检查通过；Vite 7.1.3 production build 通过；830 modules transformed。
- 亮色主题：在正式 `8765` 服务上用 Edge 实际渲染“今日认识、知识详情、设置、学习统计”4页；计算样式确认正文为深色、侧栏/顶栏/内容面板为浅色，页面底色为白色到 `#eaf9ec` 渐变；4页无控制台错误或页面异常。
- 滚动性能：同一组4页的所有已渲染元素中 `backdrop-filter` 数量为0；4K主背景 `animation-name` 为 `none`；水面动画层 `display` 为 `none`。亮色卡片、淡背景和桌面云层仍正常显示。
- 路由回归：删除关系图与站内 AI 问答入口后，直接访问和同一 SPA 会话连续切换回归通过；模拟 `window.scrollTo` 返回非函数对象后连续切换仍通过；无空根节点、控制台错误或页面异常。
- 全量内容渲染：从16个学科各取1个正式主题，用无头 Chromium 实际打开详情页；16/16通过，Markdown、LaTeX和文章正文均正常，未出现“等待通俗内容重写”或前端异常。
- 本机动态背景：仅将用户自行提供的第三方画面纹理保存到 `userdata`；前端使用 CSS 呈现轻量背景效果，素材不进入发布包，并要求登记原页面、作者和使用范围。
- API：真实 SQLite 读写、8 卡本地换批、状态/笔记重启持久化、搜索、收藏筛选、审核接受、上传类型限制通过。
- AI 请求结构：Responses 固定 `store:false`；“极高”映射为 `xhigh`；PNG/JPEG/WebP 实际转为后端 data URL 并进入图片请求体；一次最多4张且进行目录、大小和图像有效性校验。
- AI 联网：Responses 原生 `web_search` 仅在独立能力测试通过后启用；Chat Completions/DeepSeek 不虚报原生联网，改由本站后端低频检索公开网页并把标题、URL、摘要和联网模式返回界面。
- 第三方兼容：Provider请求头仅允许 `x-openai-actor-authorization` 白名单，不能覆盖Authorization或Cookie；HTTP 502 HTML网关错误归类为 `test_failed` 并显示中文原因，不再误报 `verified_unsupported`。
- 安全：本机免登录通过；模拟局域网客户端未登录返回 401、登录后 200；Argon2 密码哈希通过；Provider API 不回传密钥。
- 备份：ZIP manifest SHA-256 校验通过；备份不含 secrets；自动清理只作用于 `backups/automatic`；媒体/来源/模板/配置使用项目根相对路径并经过恢复白名单校验。
- 导入导出：JSON Schema 版本校验、重复 ID 不覆盖、新内容进入待审核、导出不含密钥通过。

## 运行组件

- 正式安装：在 `D:\CommunicationKnowledgeHub` 实际运行最终版 `setup.bat`，退出码 0；重复安装自动执行迁移前备份且不覆盖用户数据。
- HTTP 冒烟：启动器仅在端口就绪后发布状态；`/api/health` 返回 `ok` 和 406 个正式主题，`/api/cards?limit=8` 返回 8 卡，生产首页返回 200；运行 `stop.bat` 后状态文件清除，启动器与服务进程均退出。
- Windows 进程回归：修复虚拟环境重定向器导致状态 PID 与实际 Uvicorn 监听 PID 不一致的问题；最终状态为 `pid == server_pid == netstat 监听 PID`，只监听 `127.0.0.1:8765`，8766 已关闭；再次 stop/start 后仍保持单实例。
- 重复启动与缓存：再次启动会复用现有健康实例。PWA 缓存升级为 `ckh-v1.1.3-shell`，激活时删除旧缓存；React 根节点具备中文错误边界。
- Edge 路由修复：页面路径副作用不再把 `scrollTo` 的返回值交给 React 作为清理函数；刷新后正常但点击任意侧边栏出现 `ce is not a function` 的复现条件已纳入自动测试。
- OCR：PaddleOCR 3.1.0 + PaddleX 3.1.0 + PaddlePaddle 3.1.1 + LangChain 0.3 兼容锁；英文路径首次下载识别出 `Communication 2028 / 信号与系统`；`HF_HUB_OFFLINE=1` 复测通过。
- Playwright：Chromium 140 / build 1187 下载到 `runtime/browsers`；无界面本地页面测试输出 `CKH 网络回退`。
- 依赖：`pip check` 为 `No broken requirements found`；npm lock 文件已生成。
- 内容迁移演练：在正式数据库副本上完成 Alembic 0002；结果为 406 个正式主题、594 个合并记录和 594 个旧 ID 别名，原有 10 条学习状态保留，5 条首次来源基线退出待审核列表。
- 恢复实测：手动备份验证结果 `(True, [])`，恢复前自动备份成功；内容迁移也会在改库前自动创建备份。

## 受外部配置阻塞的验收项

- DeepSeek 文本真实调用、GPT 文本/视觉/原生联网真实调用、模型列表同步、各第三方接口能力测试：需要用户自己的 API Key、模型 ID 和价格配置。
- 2028 招生目录尚未发布，院校动态字段按产品规则显示“未找到或待核实”。

上述项目在网页配置向导中提供逐项测试，不影响知识库、OCR、网络检查、笔记、复习、备份和离线浏览。
