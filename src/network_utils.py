import requests
import subprocess
import platform
import configparser
import urllib.parse
import re
import os
import sys
from logger_config import logger

# --- Determine base path and config path (Windows Only) ---
if getattr(sys, 'frozen', False):
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(base_path, 'config.ini')
# --- Determine base path and config path --- END

config = configparser.ConfigParser()
if not config.read(config_path, encoding='utf-8'):
    logger.critical(f"错误：无法找到或读取配置文件 {config_path}") # Use critical
    sys.exit(f"配置文件未找到: {config_path}")

# --- Configuration Loading ---
LOGIN_URL = config.get('Network', 'login_url')
CHECK_URL = config.get('Network', 'check_url')
USERNAME = config.get('Credentials', 'username')
PASSWORD = config.get('Credentials', 'password')
logger.info("配置加载完成。")
# --- Configuration Loading End ---

def check_internet_connection(url=CHECK_URL, timeout=5):
    """通过访问指定URL检查网络连接 (Windows)。"""
    logger.info(f"开始检查网络连接 -> {url}")
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            logger.info(f"网络连接正常，成功访问 {url}")
            return True
        else:
            logger.warning(f"访问 {url} 状态码异常: {response.status_code}")
            return False
    except requests.ConnectionError:
        logger.warning(f"无法连接到 {url}，网络可能未连接。")
        return False
    except requests.Timeout:
        logger.warning(f"访问 {url} 超时。")
        return False
    except Exception as e:
        logger.error(f"检查网络连接时发生未知错误: {e}", exc_info=True)
        return False

def get_ip_address():
    """获取 Windows ipconfig 命令的完整输出。"""
    logger.debug("准备执行 'ipconfig' 获取网络信息...")
    output = None
    cmd = ['ipconfig']
    encoding = 'gbk' # Windows 命令行通常使用 GBK

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding=encoding, check=True, creationflags=subprocess.CREATE_NO_WINDOW) # Hide console window
        output = result.stdout
        logger.debug(f"成功获取 'ipconfig' 输出。")
    except FileNotFoundError:
        logger.error(f"'{cmd[0]}' 命令未找到，请确保 ipconfig 在系统 PATH 中。")
    except subprocess.CalledProcessError as e:
        logger.error(f"执行 '{cmd[0]}' 命令失败: {e}")
    except Exception as e:
        logger.error(f"获取ipconfig输出时发生未知错误: {e}", exc_info=True)

    if output is None:
        logger.error("未能获取到 ipconfig 命令输出。")

    return output

def login_to_network():
    """执行校园网登录 (Windows 专用)，成功返回 user_ip，失败返回 None。"""
    logger.info("==================== 开始尝试校园网登录 ====================")

    # 1. 获取 ipconfig 输出
    logger.info("步骤 1: 获取本地 IP 地址...")
    user_ip_output = get_ip_address()
    if not user_ip_output:
        logger.error("无法获取 ipconfig 输出，登录中止。")
        return None # Return None on failure
    logger.debug(f"获取到的 ipconfig 原始输出:\n{user_ip_output}")

    # 2. 从 ipconfig 输出中解析校园网 IP 地址 (172.30.x.x)
    user_ip = None
    try:
        logger.debug("正在解析 Windows ipconfig 输出...")
        lines = user_ip_output.split('\n')
        for i, line in enumerate(lines):
            if "IPv4 地址" in line or "IPv4 Address" in line:
                ip_line = line.strip()
                found_ip = ip_line.split(':')[-1].strip()
                if found_ip and found_ip.startswith('172.30.'):
                    user_ip = found_ip
                    logger.info(f"步骤 1 完成: 成功解析到校园网 IP 地址 -> {user_ip}")
                    break
                elif found_ip and not found_ip.startswith('169.254'):
                    logger.debug(f"找到非 172.30. 的 IP 地址: {found_ip} (已忽略)")
                else:
                    logger.debug(f"忽略无效或APIPA IP: {found_ip}")

        if not user_ip:
            logger.error("步骤 1 失败: 未能在 ipconfig 输出中找到 172.30.x.x 格式的校园网 IPv4 地址。")
            return None # Return None on failure

    except Exception as e:
        logger.error(f"解析 IP 地址时出错: {e}", exc_info=True)
        return None # Return None on failure

    # 3. 准备登录参数
    logger.info("步骤 2: 准备登录参数...")
    formatted_username = f",1,{USERNAME}" # 根据观察到的格式
    logger.debug(f"使用账号: {formatted_username}, IP: {user_ip}")

    params = {
        'callback': 'dr1003',
        'login_method': '1',
        'user_account': formatted_username,
        'user_password': PASSWORD,
        'wlan_user_ip': user_ip,
        'wlan_user_ipv6': '',
        'wlan_user_mac': '000000000000',
        'wlan_ac_ip': '172.30.255.41', # 通常固定
        'wlan_ac_name': '',
        'jsVersion': '4.1.3',
        'terminal_type': '2',
        'lang': 'zh-cn',
        'v': '795',
    }
    logger.debug(f"请求参数 (params): {params}")

    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.9", # Simplified a bit
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "http://172.30.255.42/" # Assuming this is the portal page
    }
    logger.debug(f"请求头 (headers): {headers}")
    logger.info("步骤 2 完成: 登录参数准备完毕。")

    # 4. 发送登录请求
    logger.info(f"步骤 3: 发送登录请求 -> {LOGIN_URL}")
    try:
        req = requests.Request('GET', LOGIN_URL, params=params, headers=headers)
        prepared_req = req.prepare()
        final_url = prepared_req.url
        logger.debug(f"最终请求 URL: {final_url}")

        response = requests.get(LOGIN_URL, params=params, headers=headers, timeout=15)

        logger.info(f"收到响应状态码: {response.status_code}")
        logger.debug(f"原始响应内容:\n{response.text}")

        response_text = response.text
        if response.status_code == 200 and '"result":1' in response_text and ('Portal协议认证成功' in response_text or '认证成功' in response_text):
            logger.info("步骤 3 成功: 校园网登录成功！")
            logger.info("==================== 校园网登录流程结束 ====================")
            return user_ip # Return user_ip on success
        else:
            error_msg = "未知错误或无法解析响应"
            try:
                # Try parsing JSONP style response first
                if response_text.startswith('dr1003(') and response_text.endswith(')'):
                    json_str = response_text[len('dr1003('):-1]
                    import json
                    result_json = json.loads(json_str)
                    error_msg = result_json.get('msg', f"Result: {result_json.get('result', '?')}")
                # Then check specific messages for already online
                elif '已经在线' in response_text:
                    error_msg = "设备已经在线"
                    logger.warning(f"步骤 3 注意: {error_msg} (IP: {user_ip})，视为部分成功。")
                    logger.info("==================== 校园网登录流程结束 ====================")
                    return user_ip # Also return IP if already online
                elif response.status_code != 200:
                    error_msg = f"HTTP {response.status_code} {response.reason}"

            except Exception as parse_err:
                logger.warning(f"解析登录响应时发生异常: {parse_err}", exc_info=True)

            logger.error(f"步骤 3 失败: 校园网登录失败。服务器响应: {error_msg}")
            if response.status_code == 502:
                logger.error("提示: 收到 502 Bad Gateway 错误，通常表示网关服务器问题。请检查 IP 是否正确或稍后再试。")
            logger.info("==================== 校园网登录流程结束 ====================")
            return None # Return None on failure

    except requests.exceptions.Timeout:
        logger.error(f"步骤 3 失败: 登录请求超时 ({LOGIN_URL})。请检查网络或目标服务器状态。")
        logger.info("==================== 校园网登录流程结束 ====================")
        return None # Return None on failure
    except requests.exceptions.RequestException as e:
        logger.error(f"步骤 3 失败: 登录请求时发生网络错误: {e}", exc_info=True)
        logger.info("==================== 校园网登录流程结束 ====================")
        return None # Return None on failure
    except Exception as e:
        logger.error(f"步骤 3 失败: 登录过程中发生未知错误: {e}", exc_info=True)
        logger.info("==================== 校园网登录流程结束 ====================")
        return None # Return None on failure

# Remove the __main__ test block for production
# if __name__ == '__main__':
#     logger.info("开始测试网络工具...")
#     if check_internet_connection():
#         logger.info("网络连接测试通过")
#     else:
#         logger.warning("网络连接测试失败，尝试登录...")
#         login_to_network() 