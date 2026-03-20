# 🎯 YSkills

> 一个精心整理的 AI 技能仓库，让 AI 助手更懂你

[![GitHub](https://img.shields.io/badge/GitHub-YSkills-blue?logo=github)](https://github.com/JohnLennon6946/YSkills)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📖 简介

**YSkills** 是一个开源的 AI 技能（Skill）集合，旨在扩展 AI 助手的能力边界。每个 Skill 都是一个独立的模块，可以被 AI 助手动态加载和使用。

无论你是开发者、设计师还是普通用户，这里都有适合你的工具。

---

## 🚀 快速开始

### 安装 Skill

```bash
# 克隆仓库
git clone https://github.com/JohnLennon6946/YSkills.git

# 安装单个 Skill
# 具体安装方式取决于你使用的 AI 工具
```

### 使用 Skill

在你的 AI 助手中，只需说出 Skill 的**触发词**，即可自动激活对应功能。

---

## 📦 技能列表

| Skill | 描述 | 触发词 | 状态 |
|-------|------|--------|------|
| `weather-query` | 查询全球天气信息 | "查天气"、"天气怎么样" | 🚧 开发中 |
| `git-helper` | Git 操作辅助工具 | "git 提交"、"查看状态" | 🚧 开发中 |
| `file-manager` | 智能文件管理 | "整理文件"、"查找文档" | 🚧 开发中 |

> 🚧 表示正在开发中，✅ 表示已可用

---

## 🏗️ 项目结构

```
YSkills/
├── README.md              # 项目介绍（本文件）
├── LICENSE                # 开源协议
├── CONTRIBUTING.md        # 贡献指南
├── docs/                  # 文档目录
│   └── architecture.md    # 架构设计
├── skills/                # 技能目录
│   ├── skill-template/    # Skill 模板
│   │   ├── SKILL.md       # 技能定义文件
│   │   ├── scripts/       # 辅助脚本
│   │   └── references/    # 参考文档
│   └── ...
└── tests/                 # 测试目录
    └── test_runner.py
```

---

## 🛠️ 开发指南

### 创建新 Skill

1. **复制模板**
   ```bash
   cp -r skills/skill-template skills/your-skill-name
   ```

2. **编辑 SKILL.md**
   
   每个 Skill 必须包含一个 `SKILL.md` 文件：
   
   ```markdown
   ---
   name: your-skill-name
   description: |
     技能的简要描述
     
     触发词：关键词1、关键词2
   ---
   
   # 技能名称
   
   ## 功能
   
   描述这个技能能做什么
   
   ## 使用方法
   
   ### 基本用法
   
   ```
   用户指令示例
   ```
   
   ## 实现步骤
   
   1. 步骤1
   2. 步骤2
   ```

3. **提交代码**
   ```bash
   git add .
   git commit -m "feat: 添加 xxx skill"
   git push origin main
   ```

### Skill 最佳实践

- ✅ 使用清晰的触发词，避免与其他 Skill 冲突
- ✅ 提供详细的使用示例
- ✅ 包含错误处理和边界情况说明
- ✅ 保持 Skill 的单一职责原则
- ✅ 添加必要的注释和文档

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献

1. **Fork** 本仓库
2. **创建分支** (`git checkout -b feature/amazing-skill`)
3. **提交更改** (`git commit -m '添加某个 skill'`)
4. **推送分支** (`git push origin feature/amazing-skill`)
5. **创建 Pull Request**

### 贡献类型

- 🐛 **Bug 修复** - 修复现有 Skill 的问题
- ✨ **新 Skill** - 添加新的功能模块
- 📚 **文档改进** - 完善 README 或 SKILL.md
- 🧪 **测试覆盖** - 添加测试用例
- 🎨 **代码优化** - 提升性能和可读性

---

## 📋 路线图

### 2026 Q1
- [x] 项目初始化
- [ ] 发布第一个正式版 Skill
- [ ] 完善文档和示例

### 2026 Q2
- [ ] 支持更多 AI 工具（Claude、Codex、Kimi 等）
- [ ] 建立 Skill 测试框架
- [ ] 社区贡献指南 v1.0

### 未来展望
- [ ] Skill 市场/商店
- [ ] 可视化 Skill 编辑器
- [ ] 自动 Skill 生成器

---

## 🐛 常见问题

### Q: 如何安装 Skill 到我的 AI 助手？

A: 安装方式取决于你使用的 AI 工具：
- **OpenClaw**: 将 Skill 放入 `~/.agents/skills/` 目录
- **Claude Code**: 放入 `~/.claude/skills/` 目录
- **其他工具**: 参考对应工具的文档

### Q: Skill 之间会有冲突吗？

A: 如果两个 Skill 使用了相同的触发词，可能会产生冲突。建议：
- 使用独特的触发词
- 在 SKILL.md 中明确说明与其他 Skill 的兼容性

### Q: 可以商业使用吗？

A: 可以！本项目采用 MIT 协议，允许商业使用。但请遵守原项目的开源协议。

---

## 📄 开源协议

本项目采用 [MIT 协议](LICENSE) 开源。

```
MIT License

Copyright (c) 2026 YSkills Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 🙏 致谢

感谢以下项目和社区提供的灵感：

- [OpenClaw](https://github.com/openclaw/openclaw) - AI 助手框架
- [Claude Code](https://github.com/anthropics/claude-code) - AI 编程助手
- [MCP](https://github.com/modelcontextprotocol) - Model Context Protocol

---

## 📮 联系我们

- 🐛 **Bug 报告**: [GitHub Issues](https://github.com/JohnLennon6946/YSkills/issues)
- 💡 **功能建议**: [GitHub Discussions](https://github.com/JohnLennon6946/YSkills/discussions)
- 📧 **邮件联系**: [your-email@example.com](mailto:your-email@example.com)

---

<p align="center">
  <strong>⭐ Star 本项目，支持我们继续开发！</strong>
</p>

<p align="center">
  Made with ❤️ by <a href="https://github.com/JohnLennon6946">JohnLennon6946</a> and contributors
</p>
