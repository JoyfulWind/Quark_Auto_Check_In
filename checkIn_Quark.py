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
    with open(PUSH_FLAG_FILE, "r", encoding="utf-8") as f:
        return f.read().strip() == datetime.now().strftime("%Y-%m-%d")

# 标记：今日已完成推送（成功/失败都标记）
def mark_today_finished():
    with open(PUSH_FLAG_FILE, "w", encoding="utf-8") as f:
        f.write(datetime.now().strftime("%Y-%m-%d"))

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
            return True, response["data"]["sign_daily_reward"]
        else:
            return False, response["message"]

    def queryBalance(self):
        url = "https://coral2.quark.cn/currency/v1/queryBalance"
        querystring = {
            "moduleCode": "1f3563d38896438db994f118d4ff53cb",
            "kps": self.param.get('kps'),
        }
        response = requests.get(url=url, params=querystring, headers=headers).json()
        if response.get("data"):
            return response["data"]["balance"]
        else:
            return response["msg"]

    def do_sign(self):
        log = ""
        growth_info = self.get_growth_info()
        if growth_info:
            log += (
                f" {'88VIP' if growth_info['88VIP'] else '普通用户'} {self.param.get('user')}\n"
                f"💾 网盘总容量：{self.convert_bytes(growth_info['total_capacity'])}，"
                f"签到累计容量：")
            if "sign_reward" in growth_info['cap_composition']:
                log += f"{self.convert_bytes(growth_info['cap_composition']['sign_reward'])}\n"
            else:
                log += "0 MB\n"
            if growth_info["cap_sign"]["sign_daily"]:
                log += (
                    f"✅ 签到日志: 今日已签到+{self.convert_bytes(growth_info['cap_sign']['sign_daily_reward'])}\n"
                    f"连签进度({growth_info['cap_sign']['sign_progress']}/{growth_info['cap_sign']['sign_target']})\n"
                )
            else:
                sign, sign_return = self.get_growth_sign()
                if sign:
                    log += (
                        f"✅ 执行签到: 今日签到+{self.convert_bytes(sign_return)}\n"
                        f"连签进度({growth_info['cap_sign']['sign_progress'] + 1}/{growth_info['cap_sign']['sign_target']})\n"
                    )
                else:
                    log += f"❌ 签到异常: {sign_return}\n"
        else:
            log += "❌ 签到异常: 获取成长信息失败\n"

        return log


def main():
    # 核心：今日已推送 → 直接退出，不执行任何操作
    if is_today_finished():
        print("ℹ️ 今日已完成推送，跳过本次运行（上午失败下午会自动重试）")
        return

    msg = ""
    cookie_quark = get_env()
    print("✅ 检测到共", len(cookie_quark), "个夸克账号\n")

    i = 0
    has_error = False  # 标记是否失败
    while i < len(cookie_quark):
        user_data = {}
        for a in cookie_quark[i].replace(" ", "").split(';'):
            if not a == '':
                user_data.update({a[0:a.index('=')]: a[a.index('=') + 1:]})
        log = f"🙍🏻‍♂️ 第{i + 1}个账号"
        msg += log
        log = Quark(user_data).do_sign()
        msg += log + "\n"
        # 判断是否有失败
        if "❌" in log:
            has_error = True
        i += 1

    # 执行推送 + 标记今日完成（全天只推这一次）
    try:
        if has_error:
            send("夸克签到【失败】", "签到执行失败，请前往GitHub Actions查看详细日志！\n\n" + msg)
        else:
            send("夸克自动签到【成功】", msg)
        mark_today_finished()
    except Exception as err:
        print(f"{err}\n❌ 脚本运行错误！")
        send("夸克签到【脚本异常】", f"脚本出错：{str(err)}，请检查Actions日志")
        mark_today_finished()

    return msg[:-1]


if __name__ == "__main__":
    print("----------夸克网盘开始签到----------")
    main()
    print("----------夸克网盘签到完毕----------")
