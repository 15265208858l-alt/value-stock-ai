import fast_data
import streamlit as st

from commercial_guard import install_fast_data_guard
from watchlist import render_watchlist

install_fast_data_guard()

# The current app already calls st.divider() once at the end of the research flow.
# Hook that existing UI boundary so the commercial watchlist stays isolated from the frozen core engine.
_original_divider = st.divider


def _divider_with_watchlist(*args, **kwargs):
    result = _original_divider(*args, **kwargs)
    render_watchlist()
    return result


st.divider = _divider_with_watchlist
