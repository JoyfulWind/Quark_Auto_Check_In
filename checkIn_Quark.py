import os
import re
import sys
import requests
from datetime import datetime

# ===================== 【定制功能】全天仅推送1次 + 失败重试 =====================
PUSH_FLAG_FILE = "/tmp/quark_sign_finish.today"

# 判断：今日是否已经完成推送（无论成功/失败，都不再推）
def is_today_finished():
    if not os.path.exists(PUSH_FLAG_FILE):
        return False
    try:
        with open(PUSH_FLAG_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() == datetime.now().strftime("%Y-%m-%d")
    except:
        return False

# 标记：今日已完成推送（成功/失败都标记）
def mark_today_finished():
    try:
        with open(PUSH_FLAG_FILE, "w", encoding="utf-8") as f:
            f.write(datetime.now().strftime("%Y-%m-%d"))
    except Exception as e:
        print(f"标记文件写入失败: {str(e)}")

# ===================== 【Server酱推送】 =====================
def server_push(title, content):
    sckey = os.getenv("SCKEY", "")
    if not sckey:
        return
    url = f"https://sctapi.ftqq.com/{sckey}.send"
    data = {"title": title, "desp": content}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("Server酱推送失败：", str(e))

# ===================== 【防风控请求头 iPhone/iPad 专属】 =====================
headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Quark/7.17.4 Mobile/15E148",
    "Referer": "https://drive-m.quark.cn/"
}

# 替代 notify 功能
def send(title, message):
    print(f"{title}: {message}")
    server_push(title, message)

# 获取环境变量
def get_env():
    if "COOKIE_QUARK" in os.environ:
        cookie_list = re.split('\n|&&', os.environ.get('COOKIE_QUARK'))
    else:
        print('❌未添加COOKIE_QUARK变量')
        send('夸克自动签到', '❌未添加COOKIE_QUARK变量')
        sys.exit(0)
    return cookie_list

class Quark:
    '''
    Quark类封装了签到、领取签到奖励的方法
    '''
    def __init__(self, user_data):
        self.param = user_data

    def convert_bytes(self, b):
        units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = 0
        while b >= 1024 and i < len(units) - 1:
            b /= 1024
            i += 1
        return f"{b:.2f} {units[i]}"

    def get_growth_info(self):
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
        querystring = {
            "pr": "ucpro",
            "fr": "iphone",
            "kps": self.param.get('kps'),
            "sign": self.param.get('sign'),
            "vcode": self.param.get('vcode')
        }
        response = requests.get(url=url, params=querystring, headers=headers).json()
        if response.get("data"):
            return response["data"]
        else:
            return False

    def get_growth_sign(self):
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
        querystring = {
            "pr": "ucpro",
            "fr": "iphone",
            "kps": self.param.get('kps'),
            "sign": self.param.get('sign'),
            "vcode": self.param.get('vcode')
        }
        data = {"sign_cyclic": True}
        response = requests.post(url=url, json=data, params=querystring, headers=headers).json()
        if response.get("data"):
            return True, response["data"]
        else:
            return False, response.get("msg", "签到失败，未知错误")

def main():
    msg = ""
    cookie_list = get_env()
    success_count = 0
    fail_count = 0
    fail_msg = ""
    
    # 先检查今日是否已经推送过（无论成功/失败）
    if is_today_finished():
        print("📌 今日已完成推送，跳过执行")
        return
    
    try:
        for idx, cookie in enumerate(cookie_list):
            if not cookie:
                continue
            user_data = {
                'kps': re.search(r'kps=([^;]+)', cookie).group(1) if re.search(r'kps=([^;]+)', cookie) else '',
                'sign': re.search(r'sign=([^;]+)', cookie).group(1) if re.search(r'sign=([^;]+)', cookie) else '',
                'vcode': re.search(r'vcode=([^;]+)', cookie).group(1) if re.search(r'vcode=([^;]+)', cookie) else ''
            }
            if not all(user_data.values()):
                fail_count += 1
                fail_msg += f"账号{idx+1}: Cookie格式错误，缺少必要参数\n"
                continue
            
            q = Quark(user_data)
            growth_info = q.get_growth_info()
            if not growth_info:
                fail_count += 1
                fail_msg += f"账号{idx+1}: 获取用户信息失败\n"
                continue
            
            is_signed = growth_info.get("is_signed", False)
            if is_signed:
                msg += f"账号{idx+1}: 今日已签到，无需重复操作\n"
                success_count += 1
                continue
            
            sign_success, sign_data = q.get_growth_sign()
            if sign_success:
                added = q.convert_bytes(sign_data.get("added", 0))
                msg += f"账号{idx+1}: 签到成功！获得{added}空间\n"
                success_count += 1
            else:
                fail_count += 1
                fail_msg += f"账号{idx+1}: 签到失败 - {sign_data}\n"
        
        # 推送结果
        if success_count > 0 and fail_count == 0:
            send("夸克自动签到【全部成功】", msg)
        elif success_count > 0 and fail_count > 0:
            send("夸克自动签到【部分成功】", f"成功{success_count}个，失败{fail_count}个\n\n成功详情：\n{msg}\n\n失败详情：\n{fail_msg}\n\n前往GitHub Actions查看详细日志！")
        elif fail_count > 0:
            send("夸克自动签到【全部失败】", f"失败{fail_count}个\n\n失败详情：\n{fail_msg}\n\n前往GitHub Actions查看详细日志！")
        
        # 标记今日已完成推送（无论成功/失败）
        mark_today_finished()
        
    except Exception as err:
        print(f"{err}\n❌ 脚本运行错误！")
        send("夸克签到【脚本异常】", f"脚本出错：{str(err)}，请检查Actions日志")
        mark_today_finished()

    return msg[:-1] if msg else ""


if __name__ == "__main__":
    print("----------夸克网盘开始签到----------")
    main()
    print("----------夸克网盘签到完毕----------")
