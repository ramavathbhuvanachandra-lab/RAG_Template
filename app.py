"""Root Streamlit Application Launcher.

Provides the primary user entry point for 'streamlit run app.py'.
Configures the Streamlit page and delegates execution to the modular frontend.
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from frontend.core.config_loader import (
    get_active_tenant_id,
    load_institution_ui_config,
)

# -----------------------------------------------------------------------------
# 1. Page Configuration (Must execute before any rendering commands)
# -----------------------------------------------------------------------------
_tenant_id = get_active_tenant_id()
_ui_config = load_institution_ui_config(_tenant_id)

st.set_page_config(
    page_title=f"{_ui_config.display_name} Assistant",
    page_icon=_ui_config.logo_icon,
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# 2. Canonical Engine Import (Maintains canonical architecture contract)
# -----------------------------------------------------------------------------
from ai_platform.runtime.engine import get_app_graph as create_graph
from ai_platform.runtime.embedding import warmup_embeddings
import threading
threading.Thread(target=warmup_embeddings, daemon=True).start()

# -----------------------------------------------------------------------------
# 3. Modular Frontend Entry Point
# -----------------------------------------------------------------------------
from frontend.app import run_app

# Execute the modular frontend
run_app()