# 海南大学水电费查询工具

Python 命令行工具，查询海南大学学生宿舍水、电、热水余额。

## 使用方法

### 首次配置（提取 openId）

```bash
pip install mitmproxy requests urllib3
python extract_openid.py
```

按提示操作：
1. 自动安装 mitmproxy 证书 （自动进行）
2. 启动本地代理（端口 18889）（自动进行）
3. 设置系统代理 （自动进行）
4. 打开微信，进入「海南大学水电费」小程序
5. 等待程序自动抓取 openId 并保存到 `hnu_config.json`

此步骤只需执行一次，openId 长期有效。

### 日常查询

```bash
python hnu_query.py
```

输出示例：

```
  ============================================
   海南大学水电费查询
  ============================================
   姓名: 张三
   学校: 海南大学
   楼栋: xxx
   房间: xxx
   热水余额: xx 元 (赠送: 0 元)
  ────────────────────────────────────────────
  照明+插座:  xxx 度 /  xxx 元   [202x-xx-xx]
  空调:       xxx 度 /  xxx 元   [202x-xx-xx]
  水表:        xxx 吨 /  xxx 元  [202x-xx-xx]
  ────────────────────────────────────────────
  资产总计:   xxx 元
```

也可直接传入 openId 查询：

```bash
python hnu_query.py ofDET4_xxxx你的openId
```

## 原理

### 签名算法

API 请求需要签名验证，算法为：

```
sign = MD5(appid + timestamp + appSecret)
```

其中 `appid = sz@cgdz#2021$11`，`appSecret = &szcgdz`，签名字段长期未变。

### API 接口

| 接口                           | 用途                         | 鉴权          |
| ------------------------------ | ---------------------------- | ------------- |
| `/applet/getWxUser`            | 获取用户信息、房间、热水余额 | openId + sign |
| `/weixinEle/getEleInfo?type=1` | 照明+插座剩余电量/金额       | openId        |
| `/weixinEle/getEleInfo?type=2` | 空调剩余电量/金额            | openId        |
| `/weixinEle/getWaterInfo`      | 冷水剩余吨数/金额            | openId        |

Base URL: `https://sdxt.hainanu.edu.cn/scanQRWaterCtrl_redis_hndx1/service`

### openId 获取原理

微信小程序在向服务器发起请求时，会在请求参数中携带 `openId`。通过 mitmproxy 中间人代理拦截对应域名的 HTTPS 请求，从中提取 openId。此 openId 永久有效，保存后可反复使用。

## 注意事项

- **微信关闭代理检测**：PC 微信会绕过系统代理设置。需先完全关闭微信，清除 MMKV 缓存，再重新打开微信，小程序才会走系统代理。
- **证书信任**：首次运行 `extract_openid.py` 时会自动安装 mitmproxy 根证书到系统信任区（当前用户）。
- **代理清理**：程序退出时会自动恢复系统代理设置并关闭 mitmproxy。
- **Python 版本**：需要 Python 3.7+。

## 免责声明

本工具仅供学习交流使用。使用本工具即表示您同意：

1. 本工具仅查询已绑定到自己微信账号的水电费数据，不涉及任何越权访问。
2. 中间人代理技术仅用于拦截用户本人设备上的网络请求，请勿用于非法用途。
3. 使用者应遵守相关法律法规和学校规定，自行承担使用本工具的一切风险和后果。
4. 开发者不对因使用本工具导致的任何损失或纠纷承担责任。
