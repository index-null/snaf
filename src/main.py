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

# 全局变量
email_sent_successfully = False  # 跟踪邮件发送状态，避免重复发送
in_high_frequency_mode = False  # 是否处于高频重连模式
high_frequency_start_time = None  # 高频重连模式开始时间
high_frequency_job = None  # 高频重连的调度任务对象

config = configparser.ConfigParser()
# Read config using the absolute path
if not config.read(config_path, encoding='utf-8'):
    # Use logger if available, otherwise print and exit
    try:
        logger.critical(f"错误：无法找到或读取配置文件 {config_path}")
    except NameError:
        print(f"错误：无法找到或读取配置文件 {config_path}")
    sys.exit(f"配置文件未找到: {config_path}")

# 读取配置
try:
    # 正常检查间隔 (分钟)
    interval = config.getint('schedule', 'interval', fallback=10)
    # 高频重连间隔 (秒)
    high_frequency_interval = config.getint('schedule', 'high_frequency_interval', fallback=30)
    # 高频重连持续时间 (分钟)
    high_frequency_duration = config.getint('schedule', 'high_frequency_duration', fallback=10)
except (configparser.NoSectionError, configparser.NoOptionError, ValueError) as e:
    logger.warning(f"无法从 config.ini 读取部分配置，将使用默认值。错误: {e}")
    if 'interval' not in locals():
        interval = 10
    if 'high_frequency_interval' not in locals():
        high_frequency_interval = 30
    if 'high_frequency_duration' not in locals():
        high_frequency_duration = 10
        
logger.info("主程序配置加载完成。")
logger.info(f"网络检查间隔: {interval} 分钟; 高频重连间隔: {high_frequency_interval} 秒; 高频持续时间: {high_frequency_duration} 分钟")

def start_high_frequency_mode():
    """启动高频重连模式"""
    global in_high_frequency_mode, high_frequency_start_time, high_frequency_job
    
    # 如果已经在高频模式，只更新开始时间
    if in_high_frequency_mode:
        high_frequency_start_time = time.time()
        logger.info(f"已处于高频重连模式，重置计时器。将持续 {high_frequency_duration} 分钟。")
        return
    
    # 清除所有现有的调度
    schedule.clear()
    
    # 启动高频模式
    in_high_frequency_mode = True
    high_frequency_start_time = time.time()
    logger.info(f"启动高频重连模式: 每 {high_frequency_interval} 秒尝试一次，持续 {high_frequency_duration} 分钟...")
    
    # 创建新的高频任务
    high_frequency_job = schedule.every(high_frequency_interval).seconds.do(job)

def stop_high_frequency_mode():
    """停止高频重连模式，恢复正常检查间隔"""
    global in_high_frequency_mode, high_frequency_start_time, high_frequency_job
    
    if not in_high_frequency_mode:
        return
    
    # 清除所有任务
    schedule.clear()
    in_high_frequency_mode = False
    high_frequency_start_time = None
    high_frequency_job = None
    
    logger.info(f"退出高频重连模式，恢复正常间隔: 每 {interval} 分钟检查一次。")
    
    # 创建新的正常间隔任务
    schedule.every(interval).minutes.do(job)

def check_high_frequency_timeout():
    """检查高频模式是否超时"""
    if not in_high_frequency_mode or high_frequency_start_time is None:
        return False
    
    # 计算已经过去了多少分钟
    elapsed_minutes = (time.time() - high_frequency_start_time) / 60
    if elapsed_minutes >= high_frequency_duration:
        logger.info(f"高频重连已达到最大持续时间 ({high_frequency_duration} 分钟)，切换回正常间隔。")
        stop_high_frequency_mode()
        return True
    return False

def job():
    """定时执行的任务：检查网络，如果断开则尝试重连并发送邮件通知。"""
    global email_sent_successfully, in_high_frequency_mode
    logger.info(f"---------- 网络状态检查开始{' (高频模式)' if in_high_frequency_mode else ''} ----------")
    
    # 检查高频模式是否超时
    check_high_frequency_timeout()
    
    # 保存当前时间，用于记录断开时间
    current_time = time.strftime('%Y-%m-%d %H:%M:%S')
    
    if check_internet_connection():
        logger.info("网络连接当前状态：正常。")
        
        # 如果网络恢复正常且处于高频模式，退出高频模式
        if in_high_frequency_mode:
            logger.info("网络已恢复正常，退出高频重连模式。")
            stop_high_frequency_mode()
        
        # 发送首次成功连接邮件
        if not email_sent_successfully:
            logger.info("首次检测到网络连接成功，尝试发送通知邮件...")
            # 尝试发送邮件 (网络正常，可以发送)
            if send_notification_email("校园网连接通知: 连接成功", "设备当前已连接到校园网并通过互联网检查。"):
                email_sent_successfully = True
                logger.info("首次成功通知邮件已发送。")
            else:
                logger.error("发送首次成功通知邮件失败。")
        else:
            logger.info("网络状态稳定，无需操作。")
    else:
        logger.warning("网络连接当前状态：断开或无法访问互联网。")
        disconnect_time = current_time
        email_sent_successfully = False  # 网络断开，重置邮件标志
        
        # 启动高频重连模式
        if not in_high_frequency_mode:
            start_high_frequency_mode()
        
        logger.info("尝试自动重新登录校园网...")
        user_ip = login_to_network()  # 返回 user_ip 或 None
        
        if user_ip:
            logger.info(f"自动登录成功或设备已在线 (IP: {user_ip})。等待 5 秒后再次检查网络...")
            time.sleep(5)  # 等待网络稳定
            
            if check_internet_connection():
                reconnect_time = time.strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"再次检查确认网络已恢复连接 (重连时间: {reconnect_time})。")
                
                # 网络恢复正常，退出高频模式
                if in_high_frequency_mode:
                    stop_high_frequency_mode()
                
                # 发送重连成功邮件 (网络已恢复，可以发送)
                logger.info("尝试发送重连成功通知邮件...")
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
                # 网络仍有问题，继续高频模式
                
                # 不发送邮件，因为网络连接有问题
                logger.warning("网络仍有问题，无法发送通知邮件。将继续尝试高频重连。")
        else:
            logger.error("自动重新登录校园网失败。")
            
            # 不发送邮件，因为原始问题是网络断开
            logger.warning("网络断开，登录失败，无法发送邮件通知。将继续尝试高频重连。")
    
    logger.info("---------- 网络状态检查结束 ----------\n")

if __name__ == '__main__':
    logger.info("==================================================")
    logger.info("====   校园网自动登录/保活程序 (Windows)  ====")
    logger.info("==================================================")

    # Configuration reminder
    logger.info("程序启动，请确保 config.ini 配置正确:")
    logger.info(" - [Credentials] username, password")
    logger.info(" - [Email] sender_email, sender_password (QQ授权码), receiver_email")
    logger.info(" - [dev] log_level (e.g., INFO, DEBUG)")
    logger.info(" - [schedule] interval, high_frequency_interval, high_frequency_duration")
    logger.info("--------------------------------------------------")

    # Run job once immediately on startup
    logger.info("首次运行，立即执行一次检查...")
    job()
    logger.info("首次检查执行完毕。")
    logger.info("--------------------------------------------------")

    # Schedule the job with normal interval (will be adjusted if needed by high-frequency logic)
    schedule.every(interval).minutes.do(job)
    logger.info(f"定时任务已设置，默认每 {interval} 分钟检查一次网络状态。")
    logger.info(f"如果检测到网络问题，将启动高频重连 (每 {high_frequency_interval} 秒一次，持续 {high_frequency_duration} 分钟)。")
    logger.info("程序正在后台运行，请保持此窗口开启。日志将记录在 logs/app.log")
    logger.info("==================================================")

    while True:
        schedule.run_pending()
        time.sleep(1) 