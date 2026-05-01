import os 
import re 
import sys 
import requests
from datetime import datetime

# ===================== 【新增】一天仅推送1次 =====================
PUSH_FLAG_FILE = "/tmp/quark_sign_push.today"

def is_today_pushed():
    if not os.path.exists(PUSH_FLAG_FILE):
        return False
    try:
        with open(PUSH_FLAG_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() == datetime.now().strftime("%Y-%m-%d")
    except:
        return False

def mark_today_pushed():
    try:
        with open(PUSH_FLAG_FILE, "w", encoding="utf-8") as f:
            f.write(datetime.now().strftime("%Y-%m-%d"))
    except:
        pass

# ===================== 【新增】Server酱推送 =====================
def server_push(title, content):
    sckey = os.getenv("SCKEY", "")
    if not sckey:
        return
    url = f"https://sctapi.ftqq.com/{sckey}.send"
    data = {"title": title, "desp": content}
    try:
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print("推送失败：", str(e))

# ===================== 【新增】iPhone防风控请求头 =====================
headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Quark/7.17.4 Mobile/15E148",
    "Referer": "https://drive-m.quark.cn/"
}

# 替代 notify 功能（原作者代码，仅加推送）
def send(title, message):
    print(f"{title}: {message}")
    if not is_today_pushed():
        server_push(title, message)
        mark_today_pushed()

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
                    f"✅ 签到日志: 今日已签到+{self.convert_bytes(growth_info['cap_sign']['sign_daily_reward'])}，"
                    f"连签进度({growth_info['cap_sign']['sign_progress']}/{growth_info['cap_sign']['sign_target']})\n"
                )
            else:
                sign, sign_return = self.get_growth_sign()
                if sign:
                    log += (
                        f"✅ 执行签到: 今日签到+{self.convert_bytes(sign_return)}，"
                        f"连签进度({growth_info['cap_sign']['sign_progress'] + 1}/{growth_info['cap_sign']['sign_target']})\n"
                    )
                else:
                    log += f"❌ 签到异常: {sign_return}\n"
        else:
            raise Exception("❌ 签到异常: 获取成长信息失败")

        return log


def main():
    msg = ""
    cookie_quark = get_env()

    print("✅ 检测到共", len(cookie_quark), "个夸克账号\n")

    i = 0
    while i < len(cookie_quark):
        user_data = {}
        for a in cookie_quark[i].replace(" ", "").split(';'):
            if not a == '':
                user_data.update({a[0:a.index('=')]: a[a.index('=') + 1:]})
        log = f"🙍🏻‍♂️ 第{i + 1}个账号"
        msg += log
        log = Quark(user_data).do_sign()
        msg += log + "\n"

        i += 1

    try:
        send('夸克自动签到', msg)
    except Exception as err:
        print('%s\n❌ 错误，请查看运行日志！' % err)
        send('夸克签到【异常】', f'脚本出错：{str(err)}')

    return msg[:-1]


if __name__ == "__main__":
    print("----------夸克网盘开始签到----------")
    main()
    print("----------夸克网盘签到完毕----------")
