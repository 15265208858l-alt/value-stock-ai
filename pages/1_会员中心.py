import streamlit as st

st.set_page_config(page_title="会员中心 | A股价值研投", page_icon="💎", layout="wide")

st.markdown("""
<style>
.vs-hero{background:linear-gradient(135deg,#16243A 0%,#243A59 100%);color:#fff;border-radius:18px;padding:22px 20px;margin-bottom:18px}
.vs-hero h1{margin:0 0 8px 0;font-size:1.7rem}.vs-hero p{margin:0;color:#DCE5F0;font-size:.92rem}
.vs-plan{border:1px solid #D7DEE8;border-radius:16px;padding:18px 16px;background:#fff;min-height:280px}
.vs-plan-hot{border:2px solid #B8872D;box-shadow:0 5px 20px rgba(184,135,45,.12)}
.vs-price{font-size:1.8rem;font-weight:900;color:#16243A}.vs-note{font-size:.8rem;color:#66758A}
.vs-feature{padding:5px 0;color:#42536A;font-size:.88rem}
@media(max-width:768px){.block-container{padding:.6rem .75rem 2rem!important}.vs-hero h1{font-size:1.35rem}.vs-plan{min-height:auto;margin-bottom:12px}.vs-price{font-size:1.55rem}}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="vs-hero"><h1>💎 A股价值研投 · 会员中心</h1><p>把复杂的财务数据，变成一份清晰、可执行的长期价值投资研究报告。</p></div>', unsafe_allow_html=True)

st.subheader("为什么成为会员？")
cols = st.columns(3)
features = [
    ("🔎 深度研究", "完整查看企业质量、财务排雷、估值、安全边际与投资决策"),
    ("💰 专业估值", "正常化EPS、PE/PB、历史估值与情景压力测试"),
    ("⚡ 高效使用", "减少重复研究，把重点放在真正值得跟踪的公司")
]
for c,(title,desc) in zip(cols,features):
    c.markdown(f'<div class="vs-plan"><h3>{title}</h3><div class="vs-feature">{desc}</div></div>', unsafe_allow_html=True)

st.subheader("会员方案")
plans = [
    ("免费版", "¥0", ["基础A股公司研究", "核心行情与财务指标", "基础投资结论"], False),
    ("专业版", "¥29.9/月", ["完整10步价值研究", "完整估值与安全边际", "历史估值与同行比较", "优先使用新功能"], True),
    ("年度版", "¥299/年", ["专业版全部权益", "全年持续使用", "年度价格更优惠", "适合长期投资者"], False),
]
cols = st.columns(3)
for c,(name,price,items,hot) in zip(cols,plans):
    box = 'vs-plan vs-plan-hot' if hot else 'vs-plan'
    badge = '<div style="color:#B8872D;font-weight:800;margin-bottom:6px">⭐ 推荐</div>' if hot else ''
    html = f'<div class="{box}">{badge}<h3>{name}</h3><div class="vs-price">{price}</div><div class="vs-note">适合{name.replace("版","")}用户</div>'
    html += ''.join([f'<div class="vs-feature">✅ {x}</div>' for x in items])
    html += '</div>'
    c.markdown(html, unsafe_allow_html=True)
    if name == "免费版": c.button("当前方案", key="free", use_container_width=True, disabled=True)
    else: c.button("立即开通", key=name, use_container_width=True, type="primary")

st.info("🔒 支付接口将在商业化阶段接入微信/支付宝等正式支付渠道。当前页面先完成会员产品结构与用户界面，不产生实际扣款。")

st.subheader("会员权益对比")
st.table({
    "功能": ["基础公司研究", "完整10步分析", "正常化EPS估值", "历史PE", "同行比较", "安全边际", "会员专属功能"],
    "免费版": ["✅", "部分", "部分", "部分", "部分", "部分", "—"],
    "专业版": ["✅", "✅", "✅", "✅", "✅", "✅", "✅"],
})

st.caption("A股价值研投｜ValueStock AI · 研究工具仅用于信息分析，不构成投资建议。")
