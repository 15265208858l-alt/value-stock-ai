"""ValueStock AI UI bootstrap.

This module is intentionally defensive: if Streamlit changes its internals,
any styling failure must never block the investment analysis app.
"""


def _install_ui():
    try:
        import streamlit as st
        original_set_page_config = st.set_page_config
        original_markdown = st.markdown
        state = {"installed": False}

        css = r'''
        <style>
        :root {
          --vs-navy: #14233b;
          --vs-blue: #284b73;
          --vs-gold: #b8872d;
          --vs-bg: #eef2f6;
          --vs-card: #ffffff;
          --vs-border: #d7dee8;
        }
        .stApp { background: var(--vs-bg); }
        [data-testid="stAppViewContainer"] { background: var(--vs-bg); }
        [data-testid="stHeader"] { background: rgba(238,242,246,.92); }
        .block-container { max-width: 1280px; padding-top: 2rem; padding-bottom: 4rem; }
        h1, h2, h3 { color: var(--vs-navy) !important; letter-spacing: .2px; }
        h1 { font-size: 2.15rem !important; margin-bottom: .15rem !important; }
        h2 { margin-top: 1.7rem !important; padding-top: .35rem; border-bottom: 1px solid var(--vs-border); padding-bottom: .45rem; }
        h3 { margin-top: 1rem !important; }
        [data-testid="stMetric"] { background: var(--vs-card); border: 1px solid var(--vs-border); border-radius: 16px; padding: 14px 16px; box-shadow: 0 4px 16px rgba(20,35,59,.05); }
        [data-testid="stMetricLabel"] { color: #66758a !important; }
        [data-testid="stMetricValue"] { color: var(--vs-navy) !important; font-weight: 750; }
        div[data-testid="stDataFrame"] { border: 1px solid var(--vs-border); border-radius: 14px; overflow: hidden; background: white; }
        .stTextInput > div > div, .stSelectbox > div > div { border-radius: 12px; }
        .stTextInput input { border-radius: 12px !important; }
        button[kind="primary"] { border-radius: 12px !important; font-weight: 700 !important; padding: .65rem 1.25rem !important; box-shadow: 0 6px 18px rgba(184,135,45,.20); }
        div[role="alert"] { border-radius: 12px; }
        .vs-hero { background: linear-gradient(135deg,#14233b 0%,#284b73 70%,#b8872d 100%); color:#fff; border-radius:22px; padding:26px 28px; margin:0 0 22px 0; box-shadow:0 10px 28px rgba(20,35,59,.16); }
        .vs-brand { font-size:2rem; font-weight:800; line-height:1.15; }
        .vs-product { font-size:1.02rem; opacity:.92; margin-top:6px; }
        .vs-slogan { margin-top:14px; font-size:1.08rem; opacity:.96; }
        .vs-chip { display:inline-block; margin-top:16px; padding:6px 11px; border:1px solid rgba(255,255,255,.25); border-radius:999px; font-size:.82rem; background:rgba(255,255,255,.08); }
        .vs-section { background:#fff; border:1px solid var(--vs-border); border-radius:16px; padding:18px 20px; margin:12px 0; box-shadow:0 4px 14px rgba(20,35,59,.04); }
        </style>
        '''

        hero = '''
        <div class="vs-hero">
          <div class="vs-brand">A股价值研投</div>
          <div class="vs-product">ValueStock AI · AI驱动的A股长期价值投资研究平台</div>
          <div class="vs-slogan">用AI研究价值，而不是追逐情绪。</div>
          <span class="vs-chip">财务 · 估值 · 现金流 · 同行 · 风险</span>
        </div>
        '''

        try:
            from commercial_guard import install_fast_data_guard
            install_fast_data_guard()
        except Exception:
            pass

        def patched_set_page_config(*args, **kwargs):
            result = original_set_page_config(*args, **kwargs)
            if not state["installed"]:
                state["installed"] = True
                original_markdown(css, unsafe_allow_html=True)
                original_markdown(hero, unsafe_allow_html=True)
                try:
                    from commercial_guard import install_ui_notice
                    install_ui_notice()
                except Exception:
                    pass
                try:
                    from commercial_ui import render_membership_entry
                    render_membership_entry()
                except Exception:
                    pass
            return result

        st.set_page_config = patched_set_page_config
    except Exception:
        return


_install_ui()
