import os 
import re 
import sys 
import requests

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

# 日志+推送统一入口
def send(title, message):
    print(f"{title}: {message}")
    server_push(title, message)

# 读取Cookie环境变量
def get_env(): 
    if "COOKIE_QUARK" in os.environ: 
        cookie_list = re.split('\n|&&', os.environ.get('COOKIE_QUARK')) 
    else: 
        print('❌未添加COOKIE_QUARK变量') 
        send('夸克自动签到', '❌未添加COOKIE_QUARK变量') 
        sys.exit(0) 
    return cookie_list 

# ===================== iPhone防风控请求头（完全保留你的配置） =====================
headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Quark/7.17.4 Mobile/15E148",
    "Referer": "https://drive-m.quark.cn/"
}

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
            return response.get("data", False)
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
                err_msg = response.get("message", response.get("msg", "签到失败"))
                return False, err_msg
        except Exception as e:
            return False, f"签到请求异常: {str(e)}"

    # 签到主逻辑（仅保留接口自带的已签到判断，无任何本地缓存）
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
            
            # 仅判断夸克官方接口返回的已签到状态（必须保留，否则重复签到报错）
            if growth_info["cap_sign"]["sign_daily"]:
                log += (
                    f"✅ 今日已签到+{self.convert_bytes(growth_info['cap_sign']['sign_daily_reward'])}\n"
                    f"连签进度({growth_info['cap_sign']['sign_progress']}/{growth_info['cap_sign']['sign_target']})\n"
                )
            else:
                sign, sign_return = self.get_growth_sign()
                if sign:
                    log += (
                        f"✅ 签到成功: +{self.convert_bytes(sign_return)}\n"
                        f"连签进度({growth_info['cap_sign']['sign_progress'] + 1}/{growth_info['cap_sign']['sign_target']})\n"
                    )
                else:
                    log += f"❌ 签到异常: {sign_return}\n"
        else:
            log += "❌ 签到异常: 获取成长信息失败（Cookie可能无效）\n"
        return log


def main():
    msg = ""
    cookie_quark = get_env()
    print("✅ 检测到共", len(cookie_quark), "个夸克账号\n")

    has_error = False
    for i, cookie in enumerate(cookie_quark, 1):
        user_data = {}
        for a in cookie.replace(" ", "").split(';'):
            if not a == '' and '=' in a:
                k, v = a.split('=', 1)
                user_data[k] = v
        log = f"🙍🏻‍♂️ 第{i}个账号\n"
        msg += log
        log = Quark(user_data).do_sign()
        msg += log + "\n"
        # 仅将真正的错误标记为异常（重复签到/已签到不算错误）
        if "❌" in log and "重复" not in log and "已签到" not in log:
            has_error = True

    # 推送结果
    if has_error:
        send('夸克签到【部分异常】', msg)
    else:
        send('夸克签到【正常完成】', msg)

if __name__ == "__main__":
    print("----------夸克网盘开始签到----------")
    main()
    print("----------夸克网盘签到完毕----------")