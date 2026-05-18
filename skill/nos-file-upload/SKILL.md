---
name: nos-file-upload
description: |
  将本地 txt 文件上传至 NOS 获取 nosKey（crowdPacketUrl）。

  使用场景：
  - wechat-push-create 模式 A 中用户提供了 txt 文件而非 nosKey
  - 需要将人群包 txt 文件上传到 NOS 存储

  本 Skill 由 wechat-push-create 内部调用。P1 阶段实现，P0 阶段该 Skill 返回不可用提示。

  触发词：上传文件、上传到NOS
---

# nos-file-upload

将用户提供的本地 txt 文件上传至 NOS，返回 nosKey 作为 crowdPacketUrl。

## 前置条件

1. NOS 上传能力已就绪（P1 阶段实现）
2. 用户提供的文件路径在数字员工可访问的范围内

## 输入参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| filePath | string | 是 | txt 文件的本地路径 |

## 执行步骤

### 步骤 1：文件校验

1. 检查文件是否存在：`test -f "{filePath}"`
2. 检查文件扩展名是否为 `.txt`
3. 检查文件是否非空：`test -s "{filePath}"`

校验不通过时返回对应错误信息：
- 文件不存在："文件不存在，请检查路径：{filePath}"
- 非 txt 格式："仅支持 .txt 格式文件，当前文件：{filePath}"
- 文件为空："文件内容为空，请检查文件：{filePath}"

### 步骤 2：上传至 NOS

> **P0 阶段**：NOS 上传能力尚未就绪，直接返回提示：
> "NOS 上传能力暂未就绪，请直接提供 nosKey（crowdPacketUrl）。"

> **P1 阶段**：调用 NOS 上传接口（mws 新增接口或平台内置能力），获取 nosKey。
> 上传失败时自动重试，最多 3 次，间隔 2 秒。

### 步骤 3：返回结果

- 成功：返回 nosKey 字符串（如 `jdmosi-common/obj/.../xxx.txt`）
- 失败：返回错误信息

## 错误处理

| 错误场景 | 处理方式 |
|---------|---------|
| 文件不存在 | 返回路径错误提示 |
| 非 .txt 文件 | 返回格式错误提示 |
| 文件内容为空 | 返回空文件提示 |
| 上传失败 | 重试最多 3 次，仍失败返回错误信息 |
| NOS 服务不可用 | 提示用户稍后重试或直接提供 nosKey |
