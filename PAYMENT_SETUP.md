# A股价值研投｜微信支付配置说明

当前商业化链路采用微信 Native V3：用户点击开通 -> 服务端调用微信 Native 下单 -> 返回 `code_url` -> 页面生成二维码 -> 用户扫码支付 -> 系统主动查询订单 -> 仅在微信订单状态为 `SUCCESS` 时开通专业会员。

## 需要配置的参数

在 Streamlit Community Cloud 的 App Settings / Secrets 中配置以下环境变量（不要提交到 GitHub）：

```text
VALUESTOCK_PAYMENT_PROVIDER=wechat
WECHAT_MCHID=你的微信支付商户号
WECHAT_APPID=你的微信支付相关APPID
WECHAT_API_V3_KEY=你的APIv3密钥
WECHAT_MERCHANT_SERIAL_NO=你的商户证书序列号
WECHAT_PRIVATE_KEY=你的商户API证书私钥
WECHAT_NOTIFY_URL=https://你的域名/微信支付回调地址
```

`WECHAT_PRIVATE_KEY` 如果作为单行 Secret 保存，可以把换行写成 `\\n`；程序会自动还原为真实换行。

## 当前会员价格

专业会员默认价格：`¥99/月`。

系统以“分”为单位提交订单，因此代码使用 `9900`。

## 真实联调前检查

1. 微信支付商户号已经开通 Native 支付能力。
2. APPID、商户号、API v3 Key、商户证书序列号、私钥属于同一套正式商户配置。
3. 支付回调地址使用公网 HTTPS 地址。
4. 不要把 API v3 Key、私钥、证书内容提交到 GitHub。
5. 先使用较小金额完成真实小额测试，再扩大正式推广。

## 当前实现的安全边界

- 没有使用个人微信收款二维码。
- 不允许通过前端按钮直接把用户改成 Pro。
- 会员开通以微信官方订单查询结果为依据。
- 支付订单写入 SQLite；正式商业化建议迁移到托管数据库。
- 当前仍建议后续增加微信异步通知验签、通知解密、幂等处理和订单对账。

## 本项目下一步

支付配置完成后，按以下顺序联调：

`登录账号 -> 点击微信支付 -> 创建 ¥99 订单 -> 出现二维码 -> 微信扫码付款 -> 查询支付状态 -> SUCCESS -> Pro 会员 30 天`

核心价值投资研究引擎保持冻结，不因支付功能调整计算逻辑。
