import smtplib
import ssl
import configparser
import subprocess
import platform
import os
import sys
import time # Import time for formatting
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from logger_config import logger

# --- Determine base path and config path (Windows Only) ---
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_path, 'config.ini')
# --- Determine base path and config path --- END

config = configparser.ConfigParser()
# Read config using the absolute path
if not config.read(config_path, encoding='utf-8'):
    logger.critical(f"错误：无法找到或读取配置文件 {config_path}")
    sys.exit(f"配置文件未找到: {config_path}")

# --- Email Configuration Loading ---
SENDER_EMAIL = config.get('Email', 'sender_email')
SENDER_PASSWORD = config.get('Email', 'sender_password') # QQ邮箱通常是授权码
RECEIVER_EMAIL = config.get('Email', 'receiver_email')
SMTP_SERVER = config.get('Email', 'smtp_server')
SMTP_PORT = config.getint('Email', 'smtp_port', fallback=587) # Read as int, fallback 587
logger.info("邮件配置加载完成。")
# --- Email Configuration Loading End ---

def get_ipconfig_output():
    """获取 Windows ipconfig /all 命令的完整输出，用于诊断邮件。"""
    logger.debug("准备执行 'ipconfig /all' 获取详细网络信息...")
    output = "无法获取 Windows 的网络配置信息。"
    cmd = ['ipconfig', '/all']
    encoding = 'gbk'

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding=encoding, errors='replace', check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        output = result.stdout
        logger.debug(f"成功获取 'ipconfig /all' 输出。")
    except FileNotFoundError:
        logger.error(f"'{cmd[0]}' 命令未找到。")
        output = f"'{cmd[0]}' 命令未找到。"
    except subprocess.CalledProcessError as e:
        logger.error(f"执行 '{' '.join(cmd)}' 命令失败: {e}")
        output = f"执行 '{' '.join(cmd)}' 命令失败: {e}"
    except Exception as e:
        logger.error(f"获取ipconfig /all 输出时发生错误: {e}", exc_info=True)
        output = f"获取ipconfig /all 输出时发生错误: {e}"
    return output

def send_notification_email(subject, body, user_ip=None, disconnect_time=None, reconnect_time=None):
    """发送邮件通知。

    Args:
        subject (str): 邮件主题。
        body (str): 邮件正文基础内容。
        user_ip (str, optional): 重连成功时的用户IP。如果提供，邮件内容会更简洁。
        disconnect_time (str, optional): 检测到断开连接的时间。
        reconnect_time (str, optional): 重连成功的时间。

    Returns:
        bool: 发送成功返回 True，否则 False。
    """
    logger.info(f"准备发送邮件: 主题 '{subject}'")
    final_body = body

    # 如果是重连成功邮件，构建简洁正文
    if user_ip and disconnect_time and reconnect_time:
        final_body += f"\n\n详细信息:\n"
        final_body += f" - 检测到断开时间: {disconnect_time}\n"
        final_body += f" - 自动重连时间: {reconnect_time}\n"
        final_body += f" - 当前获取IP地址: {user_ip}\n"
        logger.info("邮件内容已格式化为简洁重连成功信息。")
    else:
        # 对于其他情况（初始连接成功、失败），附加完整的ipconfig /all信息
        logger.info("邮件将附加详细的 ipconfig /all 输出用于诊断。")
        final_body += "\n\n--- 网络诊断信息 (ipconfig /all) ---\n"
        final_body += get_ipconfig_output()

    message = MIMEText(final_body, 'plain', 'utf-8')
    message['From'] = SENDER_EMAIL
    message['To'] = Header(f"管理员 <{RECEIVER_EMAIL}>", 'utf-8')
    message['Subject'] = Header(subject, 'utf-8')

    try:
        logger.info(f"连接到 SMTP 服务器: {SMTP_SERVER}:{SMTP_PORT}...")
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20) as server: # Increased timeout
            logger.info("连接成功，尝试启动 TLS 加密 (STARTTLS)...")
            server.starttls(context=context)
            logger.info("TLS 加密已启动，尝试登录...")
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            logger.info(f"SMTP 登录成功 ({SENDER_EMAIL})，尝试发送邮件...")
            server.sendmail(SENDER_EMAIL, [RECEIVER_EMAIL], message.as_bytes())
            logger.info(f"邮件已成功发送至 {RECEIVER_EMAIL}")
            try:
                logger.debug("尝试发送 QUIT 命令...")
                server.quit()
                logger.debug("SMTP 连接已正常关闭。")
            except Exception as quit_err:
                logger.warning(f"发送 QUIT 命令时出现异常 (邮件可能已发送): {quit_err}")
            return True

    except smtplib.SMTPAuthenticationError:
        logger.critical(f"SMTP 认证失败! 请检查发件人邮箱 {SENDER_EMAIL} 的授权码是否正确或已过期。")
        return False
    except smtplib.SMTPConnectError as e:
        logger.error(f"无法连接到 SMTP 服务器 {SMTP_SERVER}:{SMTP_PORT}。错误: {e}")
        return False
    except smtplib.SMTPServerDisconnected as e:
        logger.error(f"SMTP 服务器意外断开连接。错误: {e}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"发生 SMTP 错误: {e}", exc_info=True)
        return False
    except OSError as e:
        logger.error(f"发送邮件时发生网络或系统错误: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"发送邮件时发生未知错误: {e}", exc_info=True)
        return False

# Removed __main__ test block 