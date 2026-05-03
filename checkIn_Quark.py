import os 
import re 
import sys 
import requests
from datetime import datetime

# ===================== 一天仅推送1次（防重复推送） =====================
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

# ===================== Server酱微信推送 =====================
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

# ===================== iPhone防风控请求头 =====================
headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Quark/7.17.4 Mobile/15E148",
    "Referer": "https://drive-m.quark.cn/"
}

# 日志+推送统一入口
def send(title, message):
    print(f"{title}: {message}")
    if not is_today_pushed():
        server_push(title, message)
        mark_today_pushed()

# 读取Cookie环境变量
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

    # 字节单位转换
    def convert_bytes(self, b):
        units = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = 0
        while b >= 1024 and i < len(units) - 1:
            b /= 1024
            i += 1
        return f"{b:.2f} {units[i]}"

    # 获取用户签到信息
    def get_growth_info(self):
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
        querystring = {
            "pr": "ucpro",
            "fr": "iphone",
            "kps": self.param.get('kps'),
            "sign": self.param.get('sign'),
            "vcode": self.param.get('vcode')
        }
        try:
            response = requests.get(url=url, params=querystring, headers=headers, timeout=10).json()
            if response.get("data"):
                return response["data"]
            else:
                return False
        except Exception as e:
            print(f"获取用户信息失败: {str(e)}")
            return False

    # 执行签到请求
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
        try:
            response = requests.post(url=url, json=data, params=querystring, headers=headers, timeout=10).json()
            if response.get("data"):
                return True, response["data"]["sign_daily_reward"]
            else:
                # 兼容接口返回的错误字段
                err_msg = response.get("message", response.get("msg", "签到失败，未知错误"))
                return False, err_msg
        except Exception as e:
            return False, f"签到请求异常: {str(e)}"

    # 查询余额（保留原作者函数，不影响主逻辑）
    def queryBalance(self):
        url = "https://coral2.quark.cn/currency/v1/queryBalance"
        querystring = {
            "moduleCode": "1f3563d38896438db994f118d4ff53cb",
            "kps": self.param.get('kps'),
        }
        try:
            response = requests.get(url=url, params=querystring, headers=headers, timeout=10).json()
            if response.get("data"):
                return response["data"]["balance"]
            else:
                return response.get("msg", "查询失败")
        except Exception as e:
            return f"查询异常: {str(e)}"

    # 签到主逻辑
    def do_sign(self):
        log = ""
        growth_info = self.get_growth_info()
        if growth_info:
            log += (
                f" {'88VIP' if growth_info['88VIP'] else '普通用户'} {self.param.get('user', '')}\n"
                f"💾 网盘总容量：{self.convert_bytes(growth_info['total_capacity'])}\n"
                f"签到累计容量："
            )
            if "sign_reward" in growth_info['cap_composition']:
                log += f"{self.convert_bytes(growth_info['cap_composition']['sign_reward'])}\n"
            else:
                log += "0 MB\n"
            
            # 今日已签到
            if growth_info["cap_sign"]["sign_daily"]:
                log += (
                    f"✅ 签到日志: 今日已签到+{self.convert_bytes(growth_info['cap_sign']['sign_daily_reward'])}\n"
                    f"连签进度({growth_info['cap_sign']['sign_progress']}/{growth_info['cap_sign']['sign_target']})\n"
                )
            # 今日未签到，执行签到
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
            # 🔥 核心修复：把raise改成日志，不中断脚本，保证任务成功
            log += "❌ 签到异常: 获取成长信息失败（Cookie无效/接口波动）\n"

        return log


def main():
    msg = ""
    cookie_quark = get_env()
    print("✅ 检测到共", len(cookie_quark), "个夸克账号\n")

    i = 0
    has_error = False
    while i < len(cookie_quark):
        user_data = {}
        for a in cookie_quark[i].replace(" ", "").split(';'):
            if not a == '':
                user_data.update({a[0:a.index('=')]: a[a.index('=') + 1:]})
        log = f"🙍🏻‍♂️ 第{i + 1}个账号\n"
        msg += log
        log = Quark(user_data).do_sign()
        msg += log + "\n"
        if "❌" in log:
            has_error = True
        i += 1

    # 推送结果
    try:
        if has_error:
            send('夸克签到【部分异常】', msg)
        else:
            send('夸克自动签到【全部成功】', msg)
    except Exception as err:
        print('%s\n❌ 错误，请查看运行日志！' % err)
        send('夸克签到【脚本异常】', f'脚本出错：{str(err)}')

    return msg[:-1]


if __name__ == "__main__":
    print("----------夸克网盘开始签到----------")
    main()
    print("----------夸克网盘签到完毕----------")