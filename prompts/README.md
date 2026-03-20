# Plurk Prompt 管理

本目录用于管理 Plurk 自动发帖的 AI Prompt 模板。

> ⚠️ **注意**: 此目录与 SDD 模式编程的知识库完全隔离，独立管理。

## 目录结构

```
prompts/
├── README.md           # 本文件
├── daily-post.md       # 日常发帖主 prompt
├── reply-style.md      # 回复风格 prompt
├── topics/             # 话题分类
│   ├── tech.md         # 技术话题
│   └── life.md         # 生活话题
└── templates/          # 时段模板
    ├── morning.md      # 早间模板
    └── evening.md      # 晚间模板
```

## 使用方式

### 1. 日常发帖

根据当前时间和场景，选择合适的模板：

```python
# 读取 prompt
def load_prompt(template_name, topic=None):
    base = read_file("prompts/daily-post.md")
    if template_name:
        template = read_file(f"prompts/templates/{template_name}.md")
    if topic:
        topic_prompt = read_file(f"prompts/topics/{topic}.md")
    # 组合 prompt...
```

### 2. 回复帖子

使用 `reply-style.md` 作为基础风格指南。

### 3. 动态选择

根据时间自动选择模板：
- 07:00-10:00 → morning.md
- 21:00-24:00 → evening.md
- 其他时间 → daily-post.md

## 修改指南

1. **编辑现有 prompt**: 直接修改对应的 .md 文件
2. **添加新话题**: 在 `topics/` 下创建新的 .md 文件
3. **添加新模板**: 在 `templates/` 下创建新的 .md 文件

## 变量说明

Prompt 中使用的变量：
- `{{current_time}}` - 当前时间
- `{{theme}}` - 今日主题
- `{{mood}}` - 心情指数
- `{{weather}}` - 天气情况

## 限制

- 所有 prompt 必须遵守 Plurk 的 360 字符限制
- 避免敏感话题
- 保持友善、积极的语气
