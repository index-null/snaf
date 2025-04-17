import schedule
import time
import configparser
import os
import sys
from network_utils import check_internet_connection, login_to_network
from email_utils import send_notification_email
from logger_config import logger

# --- Determine base path and config path --- START
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_path, 'config.ini')
# --- Determine base path and config path --- END

# 全局变量，用于跟踪邮件发送状态，避免重复发送
email_sent_successfully = False
config = configparser.ConfigParser()
# Read config using the absolute path
if not config.read(config_path, encoding='utf-8'):
    # Use logger if available, otherwise print and exit
    try:
        logger.critical(f"错误：无法找到或读取配置文件 {config_path}")
    except NameError:
        print(f"错误：无法找到或读取配置文件 {config_path}")
    sys.exit(f"配置文件未找到: {config_path}")

try:
    interval = config.getint('schedule', 'interval')
except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
    logger.warning(f"无法从 config.ini 读取 schedule interval，将使用默认值 10 分钟。错误: {e}")
    interval = 10
logger.info("主程序配置加载完成。")

def job():
    """定义定时执行的任务：检查网络，如果断开则尝试重连并发送邮件通知。"""
    global email_sent_successfully
    logger.info(f"---------- 定时任务开始 (每 {interval} 分钟) ----------")

    if check_internet_connection():
        logger.info("网络连接当前状态：正常。")
        # Send initial success email only if it hasn't been sent before
        if not email_sent_successfully:
            logger.info("首次检测到网络连接成功，尝试发送通知邮件...")
            # Send email with full diagnostics for initial success
            if send_notification_email("校园网连接通知: 连接成功", "设备当前已连接到校园网并通过互联网检查。"):
                email_sent_successfully = True
                logger.info("首次成功通知邮件已发送。")
            else:
                logger.error("发送首次成功通知邮件失败。")
        else:
            logger.info("网络状态稳定，无需操作。")

    else:
        logger.warning("网络连接当前状态：断开或无法访问互联网。")
        disconnect_time = time.strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"检测到断开时间: {disconnect_time}")
        email_sent_successfully = False # Reset flag as connection is lost

        logger.info("开始尝试自动重新登录校园网...")
        user_ip = login_to_network() # Now returns user_ip on success, None on failure

        if user_ip:
            logger.info(f"自动登录成功或设备已在线 (IP: {user_ip})。等待 5 秒后再次检查网络...")
            time.sleep(5)
            if check_internet_connection():
                reconnect_time = time.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"再次检查确认网络已恢复连接 (重连时间: {reconnect_time})。")
                logger.info("尝试发送重连成功通知邮件...")
                # Send concise email for successful reconnection
                email_body = f"检测到校园网连接中断，已于 {reconnect_time} 自动重新连接成功。"
                if send_notification_email(
                    "校园网重连通知: 自动重连成功",
                    email_body,
                    user_ip=user_ip,
                    disconnect_time=disconnect_time,
                    reconnect_time=reconnect_time
                ):
                    email_sent_successfully = True
                    logger.info("重连成功通知邮件已发送。")
                else:
                    logger.error("发送重连成功通知邮件失败。")
            else:
                logger.warning("登录成功后网络仍然无法访问。可能存在其他问题 (如 IP 冲突或网关故障)。")
                # Send failure email with full diagnostics
                send_notification_email("校园网重连警告: 登录后网络仍不通",
                                        f"尝试自动重新登录校园网成功 (获取 IP: {user_ip})，但登录后仍无法访问互联网。请检查网络环境。")
        else:
            logger.error("自动重新登录校园网失败。")
            # Send failure email with full diagnostics
            send_notification_email("校园网重连失败通知",
                                    f"尝试自动登录校园网失败 (断开时间: {disconnect_time})。请检查配置、密码或网络环境。")

    logger.info("---------- 本次定时任务结束 ----------\n")

if __name__ == '__main__':
    logger.info("==================================================")
    logger.info("====   校园网自动登录/保活程序 (Windows)  ====")
    logger.info("==================================================")

    # Configuration reminder
    logger.info("程序启动，请确保 config.ini 配置正确:")
    logger.info(" - [Credentials] username, password")
    logger.info(" - [Email] sender_email, sender_password (QQ授权码), receiver_email")
    logger.info(" - [dev] log_level (e.g., INFO, DEBUG)")
    logger.info(" - [schedule] interval (检查间隔分钟数)")
    logger.info("--------------------------------------------------")

    # Run job once immediately on startup
    logger.info("首次运行，立即执行一次检查...")
    job()
    logger.info("首次检查执行完毕。")
    logger.info("--------------------------------------------------")

    # Schedule the job
    schedule.every(interval).minutes.do(job)
    logger.info(f"定时任务已设置，将每 {interval} 分钟检查一次网络状态。")
    logger.info("程序正在后台运行，请保持此窗口开启。日志将记录在 logs/app.log")
    logger.info("==================================================")

    while True:
        schedule.run_pending()
        time.sleep(1) 