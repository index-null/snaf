# Snaf (SZU Network Auto Fixer)

![SZU Logo](https://www.szu.edu.cn/images/logo_03.png) <!-- 你可以替换为更合适的 Logo URL -->

**一个专为深圳大学校园网设计的自动登录与连接保持工具 (Windows 平台)**

----

## 简介

Snaf (SZU Network Auto Fixer) 是一个后台运行的小工具，旨在解决深圳大学校园网（基于 Portal 认证）连接不稳定、容易掉线的问题。它会自动检测网络连接状态，在断开连接时尝试使用你在配置文件中提供的账号密码重新登录校园网，并通过邮件通知你连接状态。

## 主要功能

*   **自动检测**: 定时（默认每 10 分钟）检查网络是否能访问外网。
*   **自动重连**: 当检测到网络断开时，自动执行校园网登录流程。
*   **状态保持**: 帮助维持校园网的在线状态，减少手动登录的麻烦。
*   **邮件通知**: 在首次连接成功、断开后自动重连成功或失败时，发送邮件到你指定的邮箱，让你及时了解网络状态。
    *   重连成功邮件包含简洁的断开时间、重连时间和当前 IP。
    *   其他情况（首次成功、失败）邮件包含详细的网络诊断信息 (`ipconfig /all`)。
*   **后台运行**: 以命令行窗口形式在后台安静运行。
*   **配置灵活**: 账号、密码、邮箱、检查间隔、日志级别均可通过 `config.ini` 文件配置。
*   **日志记录**: 将详细的操作过程记录到 `logs/app.log` 文件中，方便排查问题。

## 运行环境

*   **操作系统**: Windows 7 / 8 / 10 / 11
*   **网络环境**: 深圳大学校园网 (连接需要 Portal 认证的网络)

## 使用方法

**无需安装 Python 环境！** Snaf 提供的是已打包的可执行文件 (`.exe`)。

**1. 下载**

   从发布页面 (Releases) 下载最新版本的 `Snaf-vx.x.x.zip` (或类似名称的压缩包)。

**2. 解压**

   将下载的压缩包解压到一个你方便访问的位置，例如 `D:\Snaf`。

**3. 配置 `config.ini` 文件**

   解压后，你会看到一个 `config.ini` 文件。**这是最关键的一步！** 请用记事本或其他文本编辑器打开它，并根据里面的注释修改以下内容：

   *   **`[Credentials]` 部分:**
        *   `username`: 填入你的 **校园网登录账号**。
        *   `password`: 填入你的 **校园网登录密码**。

   *   **`[Email]` 部分 (用于接收通知):**
        *   `sender_email`: 填入你 **用来发送通知的 QQ 邮箱地址** (例如 `123456789@qq.com`)。
        *   `sender_password`: **极其重要！** 这里需要填入的是你在 QQ 邮箱设置中获取的 **SMTP 服务授权码**，**而不是你的 QQ 邮箱登录密码！** 获取方法如下：
            1.  使用电脑浏览器登录你的 QQ 邮箱 ([mail.qq.com](https://mail.qq.com))。
            2.  点击顶部的 **"设置"**。
            3.  切换到 **"账户"** 选项卡。
            4.  向下滚动找到 **"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"** 部分。
            5.  确保 **"SMTP服务"** 是 **"已开启"** 状态。如果未开启，请点击开启，并可能需要通过短信验证。
            6.  开启后，点击 **"生成授权码"** 或 **"管理服务"->"生成授权码"**。按提示操作（通常是短信验证），你会得到一串类似 `abcdefghijklmnop` 的 **16 位授权码**。
            7.  将这串 **授权码** 完整地复制并粘贴到 `config.ini` 的 `sender_password` 字段。
        *   `receiver_email`: 填入你 **希望接收通知邮件的邮箱地址** (可以是 QQ 邮箱，也可以是其他任何邮箱)。

   *   **`[dev]` 和 `[schedule]` 部分 (可选修改):**
        *   `log_level`: 日志记录的详细程度，默认为 `INFO`。如果需要排查问题，可以改为 `DEBUG` 获取更详细的日志。
        *   `interval`: 检查网络状态的频率，单位是分钟，默认为 `10`。

   **修改完成后，请务必保存 `config.ini` 文件。**

**4. 运行 Snaf**

   双击解压目录中的 `Snaf.exe` (或你打包时指定的名字，例如 `szu-network-auto-fixer.exe`)。

   程序会启动一个命令行窗口，开始输出日志信息。它会首先进行一次网络检查和可能的登录尝试，然后按照你设定的 `interval` 定时执行。

   **请保持这个命令行窗口开启**，最小化即可。关闭窗口会终止程序运行。

**5. 查看日志**

   程序运行过程中，所有的操作和状态信息都会记录在程序目录下的 `logs/app.log` 文件中。如果遇到问题，可以查看此文件获取详细信息。

## 常见问题 (Troubleshooting)

*   **运行提示"无法找到或读取配置文件"**: 请确保 `config.ini` 文件与 `.exe` 文件在同一个目录下，并且你已经正确保存了修改。
*   **邮件发送失败，日志提示"SMTP认证失败"**: 最常见的原因是 `sender_password` 填写的不是 QQ 邮箱的 **授权码**，而是登录密码。请务必按照上述步骤获取并填写正确的 **16 位授权码**。也可能是授权码已过期，需要重新生成。
*   **登录失败，日志提示"校园网登录失败"**: 
    *   检查 `config.ini` 中的校园网 `username` 和 `password` 是否填写正确。
    *   尝试手动登录校园网，确认账号密码是否有效，以及当前网络环境是否正常。
    *   查看日志中服务器返回的具体错误信息，可能有助于判断原因。
*   **日志提示"未能从 ipconfig 输出中解析出校园网 IPv4 地址"**: 可能是你的电脑网络配置比较特殊，或者没有连接到校园网的有线/无线网络。确保你连接的是需要 Portal 认证的校园网。
*   **程序窗口闪退**: 可能是启动时发生了严重错误。尝试在 CMD 或 PowerShell 中手动运行 `.exe` 文件 (`cd`到程序目录，然后输入 `Snaf.exe` 并回车)，查看是否有错误信息输出在窗口中。

## 技术栈

*   使用 Python 编写。
*   依赖 `requests` 库发送 HTTP 请求。
*   依赖 `schedule` 库处理定时任务。
*   使用 `smtplib` 处理邮件发送。
*   使用 `configparser` 读取配置。
*   使用 `PyInstaller` 打包为 Windows 可执行文件。

## 贡献与反馈

如果你发现任何 Bug 或有改进建议，欢迎提出 Issue 或联系作者。

----

*祝你上网愉快！* 