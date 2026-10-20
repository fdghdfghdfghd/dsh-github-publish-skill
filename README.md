# dsh-github-publish-skill

![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20PowerShell-blue)
![DSH](https://img.shields.io/badge/DeepSeek%20Harness-skill-4B6EF5)

**先把隐私扫干净，再把项目推到 GitHub。** 给 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（DSH）用的 skill，也可以脱离 DSH 直接当脚本用。

A privacy-first GitHub publish skill: scan for secrets, then push over SSH. Works as a DSH skill or plain PowerShell scripts.

---

## 为什么需要它

`git push` 看似一条命令，实际有三类坑：

| 坑 | 表现 |
|---|---|
| **泄密** | 姓名、学号、终端截图里的容器 ID、`.env`、私钥被打包进仓库 |
| **认证** | 受限环境里 HTTPS 凭据助手起不来（`sh.exe` 建不了管道），`GIT_SSH_COMMAND` 同样走 shell 也不行 |
| **权限** | 复制出去的私钥继承了宽松 ACL，OpenSSH 直接拒收（`Bad permissions`） |

这个 skill 把三件事都处理了：扫描 → 用 `.cmd` 包装脚本绕过 shell → 固定 key 位置与 ACL。

## 特性

- **隐私扫描**：私钥、token（`ghp_` / `github_pat_`）、`sk-`、绝对用户路径、身份证号、手机号、IP、容器 ID、`.env`
- **人工复核提示**：图片和 Office 文件单独列出（截图与文档元数据是最常见的泄露源）
- **零依赖**：只要 `git` + OpenSSH + Python 3.8
- **可脱离 DSH**：脚本独立可用，不装 skill 也能跑
- **幂等**：重复运行只会更新 remote，不会重复添加

## 安装

```powershell
# 方式一：装成 DSH skill（推荐）
Copy-Item -Recurse -Force . "$env:DSH_HOME\skills\github-publish"

# 方式二：不装，直接用脚本
python scripts/privacy_check.py "D:\projects\my-app"
```

装成 skill 后，在会话里说"把这个推到 GitHub"就会自动触发。

## 快速开始

```powershell
# 1. 推送前扫描（有问题返回退出码 1）
python scripts/privacy_check.py "D:\projects\my-app"

# 2. 首次配置：生成 key，打印公钥
powershell -ExecutionPolicy Bypass -File scripts/setup_ssh.ps1
#    把公钥贴到 https://github.com/settings/ssh/new

# 3. 推送
powershell -ExecutionPolicy Bypass -File scripts/push.ps1 `
  -Path "D:\projects\my-app" -Init -Commit -Message "init" `
  -Remote "git@github.com:<你的用户名>/my-app.git"
```

默认 key 目录是 `$HOME/.dsh-github`，用 `-KeyDir` 可以改。

## push.ps1 参数

| 参数 | 作用 |
|---|---|
| `-Path` | 仓库目录，默认当前目录 |
| `-Init` | 不是 git 仓库时自动 `git init` |
| `-Commit` | 先 `git add -A` + commit |
| `-Remote` | 设置/更新 origin |
| `-DryRun` | 只演练，不真推 |
| `-KeyDir` | key 所在目录 |
| `-Branch` | 默认 `main` |

## 工作原理

git 在 Windows 上执行 `GIT_SSH_COMMAND` 时会套一层 `sh -c`。在受限环境里 `sh.exe` 可能直接起不来：

```
sh.exe: *** fatal error - couldn't create signal pipe, Win32 error 5
```

`push.ps1` 的做法是生成一个 `.cmd` 包装脚本并赋给 `GIT_SSH`——git 会直接 `CreateProcess`，不经过 shell：

```batch
@echo off
ssh.exe -i "<key>" -o IdentitiesOnly=yes -o UserKnownHostsFile="<known_hosts>" -o StrictHostKeyChecking=accept-new %*
```

## 常见问题

**Q：`ssh -T` 报错但明明连上了？**
`ssh -T` 认证成功时退出码也是 1（GitHub 不提供 shell）。看输出里有没有 `Hi <user>!`。

**Q：`ls-remote` 没有任何输出？**
空仓库正常如此，退出码 0。用 `git ls-remote origin refs/heads/main` 对比 `git rev-parse HEAD` 判断。

**Q：私钥复制到别处就用不了？**
Windows 上复制文件不保留 ACL，副本会继承目标目录权限，ssh 判定"太宽"而拒收。要么原地生成，要么复制后 `icacls` 收紧。

**Q：token 能代替 SSH 吗？**
能，但 token 会进 shell 历史或配置文件；SSH key 不需要在对话里传递任何秘密。

## 安全约定

- 私钥只放本地默认目录，`.gitignore` 已排除 `id_ed25519`、`known_hosts`、`*.pem`
- 提交作者默认 `用户名@users.noreply.github.com`（建议在 GitHub 设置里开启 "Keep my email addresses private"）
- 扫描器对自身源码里的规则字符串做了跳过，避免误报

## License

MIT
