"""A股价值研投｜商业化试用限制层。

当前阶段：
- 默认 free：每个 Streamlit 会话只允许测试 1 个不同的股票代码。
- 同一只已测试股票可以重复查看，不重复消耗试用名额。
- Pro：不受该限制。

安全边界：这是“产品试用控制”而非最终商业级账号鉴权。正式收费前必须接入
服务端身份、数据库、订单/支付回调与服务端限额校验，不能依赖浏览器或 session_state。
本模块不修改任何核心研究计算逻辑。
"""

from typing import Any, Dict, Optional


SESSION_PLAN_KEY = "vs_membership_plan"
SESSION_TRIAL_STOCK_KEY = "vs_trial_stock"
SESSION_TRIAL_USED_KEY = "vs_trial_used"


def _streamlit():
    import streamlit as st
    return st


def _get_plan() -> str:
    st = _streamlit()
    value = str(st.session_state.get(SESSION_PLAN_KEY, "free") or "free").strip().lower()
    return "pro" if value == "pro" else "free"


def is_pro() -> bool:
    return _get_plan() == "pro"


def trial_status() -> Dict[str, Any]:
    st = _streamlit()
    code = st.session_state.get(SESSION_TRIAL_STOCK_KEY)
    used = bool(st.session_state.get(SESSION_TRIAL_USED_KEY, False))
    return {
        "plan": _get_plan(),
        "used": used,
        "trial_stock": code,
        "limit": 1,
        "remaining": None if is_pro() else (0 if used else 1),
    }


def check_stock_access(code: str) -> Dict[str, Any]:
    """检查当前会话是否可以研究 code。失败时只返回状态，不抛异常。"""
    code = str(code or "").strip()
    status = trial_status()
    if status["plan"] == "pro":
        return {"allowed": True, "reason": "pro", **status}

    trial_code: Optional[str] = status.get("trial_stock")
    if not status["used"]:
        return {"allowed": True, "reason": "trial_available", **status}
    if trial_code and code == trial_code:
        return {"allowed": True, "reason": "same_trial_stock", **status}
    return {"allowed": False, "reason": "trial_exhausted", **status}


def record_successful_stock(code: str) -> None:
    """仅在核心数据成功加载后记录试用股票；失败请求不会消耗试用次数。"""
    st = _streamlit()
    if is_pro():
        return
    code = str(code or "").strip()
    if not code:
        return
    if not st.session_state.get(SESSION_TRIAL_USED_KEY, False):
        st.session_state[SESSION_TRIAL_STOCK_KEY] = code
        st.session_state[SESSION_TRIAL_USED_KEY] = True


def guard_peer_research() -> bool:
    """免费版不开放同行多股票扩展研究。"""
    return is_pro()


def install_fast_data_guard() -> None:
    """在 app 导入 fast_data 函数前安装轻量商业试用保护。"""
    try:
        import fast_data
    except Exception:
        return

    if getattr(fast_data, "_commercial_guard_installed", False):
        return

    original_stock = fast_data.load_stock_data_fast
    original_peers = fast_data.load_peer_snapshots

    def guarded_stock(code):
        access = check_stock_access(code)
        if not access["allowed"]:
            return None
        data = original_stock(code)
        if data:
            record_successful_stock(code)
        return data

    def guarded_peers(codes_tuple):
        if not guard_peer_research():
            return {}
        return original_peers(codes_tuple)

    fast_data.load_stock_data_fast = guarded_stock
    fast_data.load_peer_snapshots = guarded_peers
    fast_data._commercial_guard_installed = True



def install_ui_notice() -> None:
    """安装免费试用提示；不依赖内部 Streamlit API。"""
    try:
        st = _streamlit()
        if is_pro():
            st.caption("⭐ 专业会员｜不限股票研究")
            return
        status = trial_status()
        if not status["used"]:
            st.info("🎁 免费研究体验：可完整测试 1 只股票。同一只股票可重复查看。")
        else:
            code = status.get("trial_stock") or "已使用"
            st.info(f"🎁 免费体验已使用：{code}。升级专业会员后可不限股票研究，并解锁股票池、估值提醒与专业报告。")
    except Exception:
        return
