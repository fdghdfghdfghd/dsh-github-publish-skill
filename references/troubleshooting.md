# 故障排查

## 1. HTTPS 推送失败

现象：

```
fatal: could not read Username for 'https://github.com'
error: failed to execute prompt script (exit code 66)
sh.exe: *** fatal error - couldn't create signal pipe, Win32 error 5
```

原因链：

1. 配了 `credential.helper=manager`（Git Credential Manager）
2. GCM 是 shell 脚本，git 用 `sh.exe` 执行它
3. 受限环境禁止子进程创建命名管道，`sh.exe` 启动即崩

`GIT_SSH_COMMAND` 同样会被 `sh -c` 执行，所以也不能用。

**可行做法**：`GIT_SSH` 指向一个 `.cmd` 包装脚本，git 直接 CreateProcess，不经过 shell。`push.ps1` 每次运行会自动生成这个脚本。

## 2. schannel 凭据错误

```
schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS (0x8009030e)
```

`curl`、`Invoke-RestMethod` 默认走 schannel，某些环境拿不到凭据句柄。

- `git -c http.sslBackend=openssl` 可以让**网络层**通过（`git ls-remote` 能成功）
- 但推送还需要认证，认证又回到第 1 节
- Node/Python 用 OpenSSL，不受影响

## 3. 私钥 ACL 太宽

```
@@@ WARNING: UNPROTECTED PRIVATE KEY FILE! @@@
Permissions for '...id_ed25519' are too open.
```

OpenSSH 在 Windows 上也会检查私钥 ACL。如果目录继承了 `Authenticated Users` / `Users` 的权限，ssh 会拒绝加载。

处理：

```powershell
icacls "$HOME\.dsh-github\id_ed25519" /inheritance:r
icacls "$HOME\.dsh-github\id_ed25519" /grant:r "$env:USERDOMAIN\$env:USERNAME:F"
```

注意：**文件复制不保留 ACL**。把 key 从 A 目录复制到 B 目录，B 里的副本会继承 B 的权限。要么原地生成（`setup_ssh.ps1` 就是这么做的），要么复制后重新收紧。

## 4. 认证成功但退出码是 1

```
Hi <user>! You've successfully authenticated, but GitHub does not provide shell access.
```

`ssh -T` 在认证成功时也返回 1（因为没有 shell）。**看输出文字，别看退出码**。

## 5. 空仓库的 ls-remote

对空仓库执行 `git ls-remote origin` 会**没有任何输出且退出码 0**。这不是失败。

要判断推送是否成功，对比：

```powershell
git ls-remote origin refs/heads/main
git rev-parse HEAD
```
