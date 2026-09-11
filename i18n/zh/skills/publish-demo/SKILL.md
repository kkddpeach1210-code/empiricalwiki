---
description: 把当前工作区 wiki 同步到 demo 分支并推送，让已连接 Vercel（或其他静态托管）的只读预览网站更新到最新内容
---

# /publish-demo

> 把当前工作区 `wiki/` 的最新内容同步进 `demo` 分支并推送到远程。`demo` 分支是仓库里唯一把 wiki 内容作为跟踪文件的分支（`main` 上 wiki 内容被 gitignore），供 `tools/view.sh` 本地预览之外的另一种查看方式：部署到 Vercel/Netlify/GitHub Pages 等静态托管，随时随地（包括 iPad）用浏览器打开。

## Trigger

手动：用户说"更新一下 demo"、"同步到网站"、"发布 wiki"、"push 一下 demo" 或类似意思时触发。

## Inputs

不需要任何参数。

## Outputs

- 更新后的本地 `demo` 分支（`tools/update_demo.sh` 生成的新 commit）
- 已推送到 `origin/demo`
- 若已连接自动部署的静态托管（如 Vercel），对方会据此自动重新构建

## Wiki Interaction

### Reads
- 当前工作区 `wiki/*`（作为 `demo` 分支新 commit 的内容来源）

### Writes
- 不写工作区任何文件——`tools/update_demo.sh` 用 plumbing 命令直接操作 `demo` 分支的 git 对象，绝不 `git switch`、绝不触碰当前 checkout

## Workflow

### Step 1：确认工作区是最新想要发布的状态

如果用户刚做了会影响 wiki 的操作（`/ingest`、`/init` 等），确认这些已经完成、当前 `wiki/` 目录就是想发布的版本。不需要用户手动 commit——`wiki/` 在 `main` 上本来就不被 git 跟踪，`update_demo.sh` 直接从磁盘读取。

### Step 2：生成 demo commit

```bash
bash tools/update_demo.sh
```

- 若与上次相比没有变化，脚本会打印 `demo is already up to date.` 并以 0 退出——如实告知用户，不必再执行 Step 3。
- 否则脚本打印新 commit 的短 SHA。

### Step 3：推送

```bash
git push origin demo
```

### Step 4：报告

告诉用户：
- 是否有实际更新（或"已是最新，无需推送"）
- 如果推送了：网站会在（通常）1-2 分钟内自动重新构建；如果他们还没连接 Vercel/等静态托管，提醒一下需要先完成那一次性设置

## Constraints

- **绝不 `git switch demo` 或 `git checkout demo`**：`wiki/` 内容在 `main` 上被 gitignore、在 `demo` 上被跟踪，切分支会导致 git 删除当前工作区的 wiki 文件。本 skill 全程只用 `tools/update_demo.sh`（plumbing 实现）与 `git push origin demo`，不做任何 checkout。
- **不修改 `wiki/` 内容本身**：这是纯发布步骤，不是编辑步骤；内容改动交给 `/ingest`、`/edit` 等其他 skill。
- **`demo` 分支只由这个 skill（或用户手动运行 `tools/update_demo.sh`）更新**：不要让其他 skill 顺手调用它。

## Error Handling

- **`tools/update_demo.sh` 报错**（例如不在 git 仓库根目录、`main` 分支不存在）：把错误原样展示给用户，不要重试或猜测修复。
- **`git push origin demo` 失败**（网络、权限）：报告错误；不要改用 `--force` 之类手段掩盖失败原因。
- **`origin` 上不存在 `demo` 分支**（第一次发布）：`git push origin demo` 会自动创建，属于正常情况，不是错误。

## Dependencies

### Tools（via Bash）
- `bash tools/update_demo.sh ["commit message"]` — 生成/更新本地 `demo` 分支（plumbing，不切换 checkout）
- `git push origin demo`

### 不调用其他 skill、不访问 wiki 之外的文件、不需要任何 API key
