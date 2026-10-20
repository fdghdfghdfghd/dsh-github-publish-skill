---
name: github-publish
description: 把本地项目安全地发布到 GitHub——隐私/密钥扫描、初始化、提交、推送、校验；并排查 git 在受限环境下的 TLS、凭据助手与 SSH 权限问题。当用户说"推到 GitHub""上传项目""发布代码""发之前检查隐私"时使用。
whenToUse: 用户要把本地目录变成 GitHub 仓库或更新已有仓库；或 git push 报认证/TLS/权限错误时。
---

# 发布项目到 GitHub

一套"先查隐私，再推代码"的最小流程，附带若干在受管环境里踩过的坑。

## 前置

- Windows + Git for Windows + OpenSSH（`ssh.exe` 在 PATH 里）
- Python 3.8+（只用于隐私扫描）
- GitHub 账号

## 三步流程

### 1. 隐私扫描（必做）

```powershell
python scripts/privacy_check.py "要发布的目录"
```

- 退出码 1 = 有 HIGH 级问题（私钥、token、绝对用户路径、身份证号、`.env`），**不要推**
- `[CHECK]` 的图片/Office 文件要人工看一眼：截图里常带终端路径、容器 ID、报错堆栈；docx/pdf 的元数据常带作者名
- 顺带会打印 git 提交作者——公开仓库里这个信息永远可见，建议用 `用户名@users.noreply.github.com`

### 2. 首次配置（只在没有 key 时）

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup_ssh.ps1
```

会生成 ed25519 key、写包装脚本、打印公钥、测试认证。

**公钥必须贴到 https://github.com/settings/ssh/new** 才会生效。

默认 key 目录是 `$HOME/.dsh-github`，可用 `-KeyDir` 改。

判断成功的标志：输出里有 `Hi <用户名>! You've successfully authenticated`。注意 `ssh -T` 成功时退出码也是 1，别据此判失败。

### 3. 推送

```powershell
powershell -ExecutionPolicy Bypass -File scripts/push.ps1 `
  -Path "要推送的目录" -Init -Commit -Message "first commit" `
  -Remote "git@github.com:<用户>/<仓库>.git"
```

| 参数 | 作用 |
|---|---|
| `-Path` | 仓库目录，默认当前目录 |
| `-Init` | 不是 git 仓库时自动 `git init` |
| `-Commit` | 先 `git add -A` + commit |
| `-Remote` | 设置/更新 origin |
| `-DryRun` | 只演练，不真推 |
| `-KeyDir` | key 所在目录，默认 `$HOME/.dsh-github` |
| `-Branch` | 默认 `main` |

脚本最后会跑 `git ls-remote origin`，看到远端 sha 才算真成功。

## 发布前清理清单

从**要发布的工作副本**里剔除（不是从原项目删）：

- 姓名 / 学号 / 班级 / 同学名 / 指导教师
- 终端截图（容器 ID、`/root` 路径、报错堆栈）
- `.swp`、`__pycache__`、`.pth`、训练中间图
- 课程报告 docx/pdf（元数据带作者）
- 数据集（通常有许可限制，也会撑大仓库）

`.gitignore` 至少覆盖：`data*/`、`checkpoints/`、`results/`、`__pycache__/`、`*.py[cod]`、`*.pth`、`*.swp`、`.venv/`。

## 已知坑

| 现象 | 原因 | 处理 |
|---|---|---|
| `schannel: AcquireCredentialsHandle failed` | 凭据存储不可用 | 改用 SSH，别走 HTTPS |
| `sh.exe: couldn't create signal pipe` | git 通过 shell 执行凭据助手 / `GIT_SSH_COMMAND` | 改用 `GIT_SSH` 指向 `.cmd` 包装脚本 |
| `Bad permissions ... private key` | key 的 ACL 太宽 | 确保 key 所在目录只有当前用户可读；必要时用 `icacls` 收紧 |
| `Permission denied (publickey)` | 公钥没加到 GitHub | 跑 `setup_ssh.ps1` 打印公钥并添加 |
| `remote origin already exists` | 重复 add | 用 `push.ps1 -Remote`（内部会 set-url） |

细节见 `references/troubleshooting.md`。

## 安全约定

- 不要把私钥内容打印到对话里，只用 `ssh-keygen -y` 输出公钥
- token 一律不进对话；优先 SSH
- 推送后检查：仓库页面的文件、`git log --format='%an <%ae>'` 的作者信息
