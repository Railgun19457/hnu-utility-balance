# HNU 水电费查询

![:hnu-utility-balance](https://count.getloli.com/@railgun19457_hnu-utility-balance?name=railgun19457_hnu-utility-balance&theme=miku&padding=7&offset=0&align=top&scale=1&pixelated=1&darkmode=auto)

一个 Python 库（同步 / 异步），封装「海大售电」小程序后端的全部公开接口：宿舍照明、空调、水表、热水余额，充值 / 消费记录，校区 / 楼栋 / 房间列表，以及房间绑定 / 解绑。

仓库同时保留 `extract_openid.py`（首次抓取 openId）和 `examples/` 目录下的完整调用示例。

## 功能特性

- 同步 + 异步双客户端，同一套 API
- 覆盖全部只读查询接口与房间绑定 / 解绑
- 强类型数据模型（`User`、`EleInfo`、`BuyRecord`……），保留原始字典
- 自动签名（`MD5(appid + timestamp + appSecret)`）、超时 / 重试 / TLS 配置
- `raw_request()` 逃生通道，可调用未封装的接口
- 其余程序可直接以本库为依赖调用

## 安装

```bash
git clone https://github.com/Railgun19457/hnu-utility-balance.git
cd hnu-utility-balance
pip install -e .
```

也可以只装依赖 `httpx` 后，把 `hnu_utility/` 目录直接放进你的项目。

运行测试：

```bash
pip install -e ".[dev]"
pytest
```

## 快速开始

### 同步

```python
from hnu_utility import HnuUtilityClient, EleType, ConsumeType

with HnuUtilityClient("ofDET4_xxxx你的openId") as client:
    wx_user = client.get_wx_user()
    print(wx_user.user.real_name, wx_user.user.total_money)

    light = client.get_ele_info(EleType.LIGHT)   # 照明
    air   = client.get_ele_info(EleType.AIR)     # 空调
    water = client.get_water_info()
    print(light.left_ele, air.left_ele, water.left_water)

    records = client.get_personal_buy_info(ConsumeType.ELECTRICITY)
    for r in records.records[:3]:
        print(r.create_time, r.room_name, r.pay_money)
```

### 异步

```python
import asyncio
from hnu_utility import AsyncHnuUtilityClient, EleType

async def main():
    async with AsyncHnuUtilityClient("ofDET4_xxxx你的openId") as client:
        wx_user = await client.get_wx_user()
        light = await client.get_ele_info(EleType.LIGHT)
        print(wx_user.user.real_name, light.left_ele)

asyncio.run(main())
```

### 读取 hnu_config.json

```python
from hnu_utility import HnuUtilityClient, load_open_id

with HnuUtilityClient(load_open_id("hnu_config.json")) as client:
    ...
```

## openId 获取

首次使用先运行 `extract_openid.py`（依赖 mitmproxy）：

```bash
pip install mitmproxy
python extract_openid.py
```

脚本会安装 mitmproxy 证书、启动本地代理并设置系统代理，随后：

1. 完全关闭并重新打开微信
2. 进入「海大售电 / 海南大学水电费」小程序
3. 程序自动抓取 `openId` 并写入 `hnu_config.json`

此步骤通常只需一次，`openId` 长期有效。

## 接口支持

### 用户与余额

| 方法 | 接口 | 说明 |
| --- | --- | --- |
| `get_wx_user()` | `/applet/getWxUser` | 用户信息、房间绑定、热水余额（需签名） |
| `get_user()` | `/applet/getUser` | 完整用户实体（原始字段见 `.raw`） |
| `get_left_money()` | `/applet/getLeftMoney` | 热水账户（需签名） |
| `get_ele_info(ele_type)` | `/weixinEle/getEleInfo` | 照明 / 空调剩余电量与金额 |
| `get_water_info()` | `/weixinEle/getWaterInfo` | 水表剩余吨数与金额 |

### 记录查询

| 方法 | 接口 | 说明 |
| --- | --- | --- |
| `get_personal_buy_info(consume_type)` | `/weixinEle/getPersonalBuyInfo` | 个人充值记录（电 / 水） |
| `get_room_buy_info(consume_type, room_type)` | `/weixinEle/getRoomBuyInfo` | 房间充值记录（照明 / 空调 / 水表） |
| `get_buy_orders(school_name)` | `/applet/getBuyInfo` | 水控充值订单 |
| `get_consume_records(school_name)` | `/applet/getConsumeInfo` | 水控消费记录 |
| `get_last_consume()` | `/applet/getLastConsume` | 最近一次扫码 / 蓝牙用水 |
| `get_ele_used_info()` | `/weixinEle/getEleUsedInfo` | 电表用量（部分部署无数据，会抛 `HnuApiError`） |

### 校区 / 楼栋 / 房间

| 方法 | 接口 | 说明 |
| --- | --- | --- |
| `get_schools()` / `get_water_schools()` | `schoolList` / `waterSchoolList` | 校区列表 |
| `get_buildings(...)` / `get_water_buildings(...)` | `school_louDongList` / `waterSchool_louDongList` | 楼栋列表 |
| `get_rooms(lou_dong_id)` / `get_water_rooms(lou_dong_id)` | `louDong_roomList` / `waterLouDong_roomList` | 房间列表 |

### 房间绑定（写操作）

| 方法 | 接口 | 说明 |
| --- | --- | --- |
| `save_room_info(...)` | `/weixinEle/saveRoomInfo` | 绑定照明 + 空调房间 |
| `save_water_room_info(...)` | `/weixinEle/saveWaterRoomInfo` | 绑定水表房间 |
| `clear_light_room()` | `/weixinEle/clearZmRoom` | 解绑照明（调用即生效） |
| `clear_air_room()` | `/weixinEle/clearKtRoom` | 解绑空调（调用即生效） |

### 其他

| 方法 | 接口 | 说明 |
| --- | --- | --- |
| `get_info_url(school_name)` | `/applet/getInfoUrl` | 使用说明页地址 |
| `exchange_code(code)` | `/applet/getOpenId` | 微信登录 code 换 openId |
| `raw_request(path, params)` | 任意 | 逃生通道，可调用未封装接口 |

## 数据模型

所有模型都是 dataclass，数字字段（`amount`、`left_ele`、`pay_money` 等）已转成 `float | None`，并用 `raw` 字段保留原始字典。

| 模型 | 来源 |
| --- | --- |
| `WxUser` / `User` | `get_wx_user` / `get_user` / `get_left_money` |
| `EleInfo` / `WaterInfo` | `get_ele_info` / `get_water_info` |
| `PersonalBuyInfo` / `BuyRecord` | `get_personal_buy_info` |
| `RoomBuyInfo` / `RoomBuyRecord` | `get_room_buy_info` |
| `BuyOrder` | `get_buy_orders` |
| `ConsumeRecord` | `get_consume_records` / `get_last_consume` |
| `NamedItem` | 校区 / 楼栋 / 房间列表 |
| `UsedEleInfo` | `get_ele_used_info` |

## 高级用法

### 异常处理

```python
from hnu_utility import HnuApiError, HnuError

try:
    client.get_ele_used_info()
except HnuApiError as exc:
    print(exc.code, exc.message)   # 业务错误码与消息
except HnuError as exc:
    print("其他错误", exc)
```

异常体系：`HnuError` → `HnuApiError`（业务码非 200）/ `HnuNetworkError`（网络）/ `HnuResponseError`（HTTP / JSON 异常）。

### 调用未封装的接口

```python
# 带签名的接口
client.raw_request("/applet/getOpenSendData", {"deviceName": "xxx"}, signed=True)
# 只带 openId 的接口
client.raw_request("/applet/getFuzzyLocation", {"latitude": 20.05, "longitude": 110.32})
```

### 其他部署 / 测试

```python
import httpx
from hnu_utility import HnuUtilityClient

# 其他学校的同款部署
client = HnuUtilityClient(open_id, base_url="https://example.edu.cn/xxx/service")

# 单元测试注入 MockTransport
client = HnuUtilityClient(open_id, transport=httpx.MockTransport(handler))
```

`timeout`、`retries`、`verify`、`headers` 等均可通过构造参数配置。

## 未封装的接口

以下接口刻意没有封装：

- **支付**（`payMoney` / `payMoneySuccess`）：返回的是微信小程序 JSAPI 支付参数（`timeStamp` / `nonceStr` / `package` / `paySign`），只能在小程序内通过 `wx.requestPayment()` 使用，无法生成外部可用的支付链接，因此库不提供。
- **蓝牙控水 / 设备类**（`getOpenSendData`、`getPwdData`、`getMacOrUuid`、`getTemperatureSetData`、`saveTemperatureSetData`、`saveWhiteList`、`consLogListOffline`）：需要真实水控器交互，不适合作为纯 HTTP 库封装。
- **上传 / 报修**（`upload`、`maintainUpload`）与 **一卡通登录**（`/qyweixin/loginCardId`）。

如有需要，可用 `raw_request()` 自行调用。

## 示例（examples/）

所有示例都支持两种方式提供 openId：位置参数，或缺省读取 `hnu_config.json`。

| 示例 | 说明 |
| --- | --- |
| `examples/balance.py` | 同步查询全部余额并汇总 |
| `examples/async_balance.py` | 异步并发查询余额 |
| `examples/records.py` | 充值 / 消费记录 |
| `examples/browse_rooms.py` | 校区 → 楼栋 → 房间列表浏览 |
| `examples/bind_room.py` | 查看当前绑定；`--confirm` 时按当前绑定原样重存（幂等） |

```bash
python examples/balance.py            # 读取 hnu_config.json
python examples/balance.py <openId>   # 手动指定
python examples/async_balance.py
python examples/records.py
python examples/browse_rooms.py
python examples/bind_room.py --confirm
```

输出示例：

```text
  ============================================
   海南大学水电费查询
  ============================================
   姓名: 张三
   学校: 海南大学
   楼栋: 紫荆3公寓
   房间: 紫荆3公寓660照明
   热水余额: 0.52 元 (赠送: 0 元)
  ────────────────────────────────────────────
  照明+插座:  136.71 度 /  83.32 元   [2026-09-26 01:26:23]
  空调:        36.55 度 /  22.28 元   [2026-09-26 01:26:25]
  水表:        20.13 吨 /  63.21 元   [2026-09-26 01:26:12]
  ────────────────────────────────────────────
  资产总计:   169.33 元
```

## 注意事项

- PC 微信默认可能绕过系统代理。如抓不到 `openId`，请先完全退出微信，再重新打开小程序。
- `hnu_config.json` 含个人 `openId`，请勿提交到公开仓库（已在 `.gitignore` 中）。
- 绑定 / 解绑属于写操作，会影响账号当前绑定的房间，调用前请确认参数无误。

## 相关项目

- [astrbot_plugin_hun_utility_balance](https://github.com/Railgun19457/astrbot_plugin_hun_utility_balance)：AstrBot 插件版，支持指令查询与低余额提醒

## 免责声明

本工具仅供学习交流使用。使用本工具即表示你同意：

1. 仅查询已绑定到自己微信账号的水电费数据，不涉及越权访问。
2. 中间人代理仅用于拦截本人设备上的网络请求，请勿用于非法用途。
3. 使用者应遵守相关法律法规和学校规定，并自行承担使用风险。
4. 开发者不对因使用本工具造成的任何损失或纠纷承担责任。
