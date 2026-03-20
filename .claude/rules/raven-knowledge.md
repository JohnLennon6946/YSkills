---
paths: "**"
---

# 团队知识库使用指南

## 什么时候查

- **开始新任务前**：搜索相关的 rule、solution、doc，了解团队已有的约定和经验
- **遇到报错或疑难问题时**：搜索 solution 类型的知识，可能已有现成解法
- **涉及内部系统 / 基础设施时**：搜索 doc / runbook，获取操作指南

## 怎么查

```bash
# 关键词搜索
raven knowledge search --q "关键词"

# 按类型搜索
raven knowledge search --q "关键词" --type solution

# 按 scope 搜索
raven knowledge search --q "关键词" --scope backend
```

## 搜到后怎么用

| 类型     | 用法                                     |
| -------- | ---------------------------------------- |
| rule     | **必须遵守** — 编码约束、架构决策、团队规范   |
| solution | **参考借鉴** — 问题的已知解法              |
| doc      | **理解阅读** — 架构说明、API 速查          |
| runbook  | **逐步执行** — 标准化操作步骤              |
| skill    | **安装使用** — 可复用的 agent skill        |

## 沉淀知识

发现值得沉淀的经验时，主动创建知识条目：

1. 先查已有 scope：`raven knowledge scopes`
2. 同时推导 tech scope（如 backend、frontend）和 biz scope（如 biz-payment）
3. 尽量复用已有 scope，新增 scope 时提供 name 和 description

```bash
# 创建知识
raven knowledge create --type rule --title "标题" --summary "摘要" --content "内容" --scope backend,biz-payment

# 新增 scope 时
raven knowledge create --type solution --title "标题" --content "内容" --scope backend,biz-live --new-scope "biz-live:直播业务域相关知识"
```

## 长文本参数处理

当 `--content`、`--summary`、`--new-scope` 等参数内容较长时，先写入临时文件再用 `@filepath` 语法引用，避免命令行过长被拦截：

```bash
# 1. 将内容写入临时文件
# 2. 用 @filepath 引用
raven knowledge create --type solution --title "标题" --content @/tmp/kb-content.md --scope backend
```
