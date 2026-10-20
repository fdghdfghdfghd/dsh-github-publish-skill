# dsh-github-publish-skill

一个给 [DeepSeek Harness](https://github.com/deepseek-ai/deepseek-harness)（DSH）用的 skill：**先把隐私扫干净，再把本地项目推到 GitHub**。

不依赖任何第三方包，也不需要安装 GitHub CLI。核心就是 `git` + `ssh` + 一个 Python 脚本。

## 它能做什么

1. **隐私扫描**：在推送前扫出私钥、token、绝对用户路径、身份证号、手机号、`.env` 之类的泄密项，并把图片/Office 文件单独标出来让人工确认
2. **一键推送**：初始化仓库、提交、设置 remote、推送、校验远端 ref
3. **排查常见坑**：HTTPS 凭据失败、`sh.exe` 管道错误、私钥 ACL 太宽、公钥没登记

## 安装

把整个目录放到 DSH 的 skills 目录下：

```powershell
Copy-Item -Recurse -Force . "$env:DSH_HOME\skills\github-publish"
# 或者手动复制到 <DSH_HOME>/skills/github-publish
```

装好后在会话里说"把这个推到 GitHub"，skill 就会被触发。不装也能用——直接调 `scripts/` 下的脚本。

## 快速开始

```powershell
# 1. 扫描（有问题会返回退出码 1）
python scripts/privacy_check.py "D:\projects\my-app"

# 2. 首次配置：生成 key 并打印公钥
powershell -ExecutionPolicy Bypass -File scripts/setup_ssh.ps1

#    把打印出来的公钥贴到 https://github.com/settings/ssh/new

# 3. 推送
powershell -ExecutionPolicy Bypass -File scripts/push.ps1 `
  -Path "D:\projects\my-app" -Init -Commit -Message "init" `
  -Remote "git@github.com:<你的用户名>/my-app.git"
```

## 目录

```
.
├── SKILL.md                     触发词与完整流程（DSH 读取这个）
├── scripts/
│   ├── privacy_check.py         隐私与密钥扫描
│   ├── setup_ssh.ps1            生成 key、写包装脚本、测试认证
│   └── push.ps1                 提交与推送
└── references/
    └── troubleshooting.md       各类失败的原因与处理
```

## 为什么不是 `git push` 一把梭

在受管/沙箱环境里，git 的默认路径经常走不通：

- **HTTPS 走不过去**：凭据助手是 shell 脚本，受限环境下会被拦
- **`GIT_SSH_COMMAND` 也不行**：git 会用 `sh -c` 执行它
- **能用的只有 `GIT_SSH` + `.cmd` 包装脚本**：git 直接 exec，不经过 shell

`push.ps1` 做的就是这件事，顺便把 key 路径、known_hosts、参数都固定好。

## 安全提醒

- 私钥默认放 `$HOME/.dsh-github/id_ed25519`，**不要提交到任何仓库**
- 推送前先跑 `privacy_check.py`，它会把私钥、token 之类直接标成 HIGH 并返回 1
- 提交作者默认用 `用户名@users.noreply.github.com`，避免暴露真实邮箱。想让提交绑定到账号，需要用 GitHub 提供的 `<ID>+<用户名>@users.noreply.github.com`

## License

MIT
