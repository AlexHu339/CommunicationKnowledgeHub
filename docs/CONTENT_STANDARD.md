# 内容标准

每张知识卡先给一句简短概括，再用连续、通俗、信息完整的正文解释。只有内容确实需要时才增加“背景、生活类比、用途、例子、易错点、继续学习”等可选小节；不得强迫所有概念套用输入、输出或存在理由模板。考研常识优先使用自然段完整说明。

种子源在 `program/shared/seeds/knowledge_cards.json`，旧卡 ID 别名在 `knowledge_card_aliases.json`，Schema 在 `program/shared/knowledge_card.schema.json`。

旧版 1000 张卡中有 594 张是同一概念的机械拆分，现合并为 406 个真实知识主题。`validate_content.py` 检查字段、唯一 ID、同学科标题重复、来源、通俗正文进度和别名映射。AI 生成内容永远以 `pending` 进入 `review_items`，人工确认后才成为正式卡。
