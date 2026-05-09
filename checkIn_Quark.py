import os
import re
import sys
import requests
from datetime import datetime, timezone, timedelta

# 推送函数（Server酱）
def send(title, content):
    if not os.getenv('SCKEY'):
        print("⚠️ 未配置SCKEY，跳过推送")
        return
    try:
        url = f"https://sctapi.ftqq.com/{os.getenv('SCKEY')}.send"
        data = {'title': title, 'desp': content}
        requests.post(url, data=data, timeout=10)
    except Exception as e:
        print(f"❌ 推送失败: {str(e)}")

# 获取环境变量中的Cookie
def get_env():
    cookie = os.getenv('COOKIE_QUARK')
    if not cookie:
        print("❌ 未设置COOKIE_QUARK环境变量")
        sys.exit(1)
    return [line.strip() for line in cookie.split('\n') if line.strip()]

class Quark:
    def __init__(self, user_data):
        self.user_data = user_data
        self.param = {}
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': '; '.join([f"{k}={v}" for k, v in user_data.items()])
        }
        self.extract_params()

    def extract_params(self):
        try:
            kuid = self.user_data.get('kuid', '')
            kps = self.user_data.get('kps', '')
            self.param = {'user': kuid, 'kps': kps}
        except:
            self.param = {'user': '未知用户', 'kps': ''}

    def convert_bytes(self, size):
        try:
            size = int(size)
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.2f} {unit}"
                size /= 1024.0
            return f"{size:.2f} TB"
        except:
            return "0 MB"

    def get_growth_info(self):
        try:
            url = "https://coral2.quark.cn/growth/v1/info"
            response = requests.get(url, headers=self.headers, timeout=10).json()
            return response.get("data", {}) if response.get("code") == 0 else None
        except Exception as e:
            print(f"获取成长信息失败: {str(e)}")
            return None

    def get_growth_sign(self):
        try:
            url = "https://coral2.quark.cn/growth/v1/sign"
            response = requests.post(url, headers=self.headers, timeout=10).json()
            if response.get("code") == 0:
                return True, response.get("data", {}).get("sign_reward", 0)
            return False, response.get("message", "签到失败")
        except Exception as e:
            return False, f"请求异常: {str(e)}"

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
            
            if growth_info["cap_sign"]["sign_daily"]:
                log += (
                    f"✅ 今日已签到+{self.convert_bytes(growth_info['cap_sign']['sign_daily_reward'])}\n"
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
            log += "❌ 签到异常: 获取成长信息失败（Cookie可能无效）\n"
        return log

def main():
    print("----------夸克网盘开始签到----------")
    msg = ""
    cookie_quark = get_env()
    print(f"✅ 检测到共 {len(cookie_quark)} 个夸克账号\n")

    has_error = False
    for idx, cookie in enumerate(cookie_quark, 1):
        user_data = {}
        for pair in cookie.replace(" ", "").split(';'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                user_data[k] = v
        log = f"🙍🏻‍♂️ 第{idx}个账号\n"
        msg += log
        log = Quark(user_data).do_sign()
        msg += log + "\n"
        if "❌" in log:
            has_error = True

    # 推送结果（一天一次，无重复）
    current_time = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    if has_error:
        send(f'夸克签到【{current_time}】部分异常', msg)
    else:
        send(f'夸克自动签到【{current_time}】全部成功', msg)

    print("----------夸克网盘签到完毕----------")
    return msg[:-1]

if __name__ == "__main__":
    main()