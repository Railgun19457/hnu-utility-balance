# HNU 水电费查询

![:hnu-utility-balance](https://count.getloli.com/@railgun19457_hnu-utility-balance?name=railgun19457_hnu-utility-balance&theme=miku&padding=7&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

一个简单的 Python 脚本，用来从「海大售电」小程序接口查询海南大学宿舍水、电、热水余额。

## 功能特性

- 一键查询宿舍照明、空调、冷水、热水余额
- 自动汇总当前可统计资产总额
- 首次通过 mitmproxy 抓取 `openId`，之后可直接本地查询
- 支持命令行直接传入 `openId`
- 输出姓名、楼栋、房间等基础信息

## 运行环境

- Python 3.7+
- Windows（`extract_openid.py` 依赖系统代理与 `certutil`）
- 依赖：`requests`、`urllib3`、`mitmproxy`（仅首次抓取 `openId` 时需要）

## 安装

```bash
pip install requests urllib3 mitmproxy
```

## 使用方法

### 1. 首次配置（提取 openId）

```bash
python extract_openid.py
```

脚本会自动完成：

1. 安装 mitmproxy 证书
2. 启动本地代理（端口 `18889`）
3. 设置系统代理

随后请：

1. 完全关闭并重新打开微信
2. 进入「海大售电 / 海南大学水电费」小程序
3. 等待程序自动抓取 `openId` 并写入 `hnu_config.json`

此步骤通常只需执行一次，`openId` 长期有效。

### 2. 日常查询

```bash
python hnu_query.py
```

也可以直接传入 `openId`：

```bash
python hnu_query.py ofDET4_xxxx你的openId
```

输出示例：

```text
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
  水表:       xxx 吨 /  xxx 元   [202x-xx-xx]
  ────────────────────────────────────────────
  资产总计:   xxx 元
```

## 原理说明

### 签名算法

部分接口需要签名：

```text
sign = MD5(appid + timestamp + appSecret)
```

### 接口列表

| 接口 | 用途 | 鉴权 |
| --- | --- | --- |
| `/applet/getWxUser` | 用户信息、房间、热水余额 | `openId` + `sign` |
| `/weixinEle/getEleInfo?type=1` | 照明 + 插座剩余电量 / 金额 | `openId` |
| `/weixinEle/getEleInfo?type=2` | 空调剩余电量 / 金额 | `openId` |
| `/weixinEle/getWaterInfo` | 冷水剩余吨数 / 金额 | `openId` |

Base URL：

```text
https://sdxt.hainanu.edu.cn/scanQRWaterCtrl_redis_hndx1/service
```

### openId 获取方式

微信小程序请求会在参数中携带 `openId`。  
`extract_openid.py` 通过 mitmproxy 拦截 `sdxt.hainanu.edu.cn` 的 HTTPS 请求，提取后保存到本地配置文件。

## 注意事项

- PC 微信默认可能绕过系统代理。如抓不到 `openId`，请先完全退出微信，再重新打开小程序。
- 首次运行 `extract_openid.py` 时会尝试安装 mitmproxy 根证书到当前用户信任区。
- 程序退出时会自动恢复系统代理，并关闭 mitmproxy。
- `hnu_config.json` 含个人 `openId`，请勿提交到公开仓库。

## 相关项目

- [astrbot_plugin_hun_utility_balance](https://github.com/Railgun19457/astrbot_plugin_hun_utility_balance)：AstrBot 插件版，支持指令查询与低余额提醒

## 免责声明

本工具仅供学习交流使用。使用本工具即表示你同意：

1. 仅查询已绑定到自己微信账号的水电费数据，不涉及越权访问。
2. 中间人代理仅用于拦截本人设备上的网络请求，请勿用于非法用途。
3. 使用者应遵守相关法律法规和学校规定，并自行承担使用风险。
4. 开发者不对因使用本工具造成的任何损失或纠纷承担责任。
