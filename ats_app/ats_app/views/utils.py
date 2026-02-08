"""
Premium UI Component Library for Agentic ATS
Enterprise-grade Streamlit components with glass-morphism dark theme

PERFORMANCE OPTIMIZATIONS:
- CSS is cached at module level (only built once per session)
- Reduces overhead from ~25KB CSS rebuild on every page load
"""
from html import escape as html_escape


def safe(value):
    """HTML-escape a value for safe insertion into HTML markup."""
    if value is None:
        return ''
    return html_escape(str(value))


def _clean_html(html: str) -> str:
    """Remove blank lines from HTML to prevent Markdown code-block misinterpretation.

    In Markdown, a blank line inside an HTML block ends the block. Subsequent
    indented content then becomes a code block, showing raw tags as text.
    This helper strips blank lines so the HTML stays in a single block.
    """
    lines = html.split('\n')
    return '\n'.join(line for line in lines if line.strip())


def get_stage_color(stage: str) -> str:
    """Stage colors using Southwest Airlines brand palette"""
    colors = {
        'Resume Screen': '#304CB2',
        'Phone Screen': '#5C6BC0',
        'Technical Interview': '#F9B612',
        'Behavioral Interview': '#FF8F00',
        'Offer': '#C8102E',
        'Hired': '#2EA043',
        'Rejected': '#F85149'
    }
    return colors.get(stage, '#304CB2')


def get_stage_icon(stage: str) -> str:
    """Get icon for each pipeline stage"""
    icons = {
        'Resume Screen': '&#128196;',  # document
        'Phone Screen': '&#128222;',   # phone
        'Technical Interview': '&#128187;',  # laptop
        'Behavioral Interview': '&#128101;',  # people
        'Offer': '&#9989;',           # check
        'Hired': '&#127881;',         # party
        'Rejected': '&#10060;'        # cross
    }
    return icons.get(stage, '&#9679;')


# Module-level cache for CSS to build only once
_CACHED_CSS = None

def premium_css() -> str:
    """
    Returns the complete premium CSS stylesheet as a <style> block.
    This CSS handles ALL premium styling for the entire ATS application.
    Includes design tokens, component styles, Streamlit overrides, and animations.

    CSS is cached at module level and only built once for performance.
    """
    global _CACHED_CSS
    if _CACHED_CSS is not None:
        return _CACHED_CSS

    _CACHED_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    /* ============================================ */
    /* DESIGN TOKENS (CSS Variables)               */
    /* ============================================ */
    :root {
        /* Background Colors */
        --bg-primary: #0F1419;
        --bg-surface: #1A2332;
        --bg-surface-hover: #243044;
        --bg-elevated: #2D3B4F;

        /* Border Colors */
        --border-subtle: rgba(255, 255, 255, 0.06);
        --border-default: rgba(255, 255, 255, 0.12);
        --border-emphasis: rgba(255, 255, 255, 0.2);

        /* Text Colors */
        --text-primary: #F0F6FC;
        --text-secondary: #8B949E;
        --text-muted: #6E7681;
        --text-inverse: #0F1419;

        /* Accent Colors */
        --accent-blue: #304CB2;
        --accent-blue-hover: #3D5FCC;
        --accent-red: #C8102E;
        --accent-red-hover: #E01236;
        --accent-gold: #F9B612;
        --accent-gold-hover: #FFD54F;
        --accent-green: #2EA043;
        --accent-green-hover: #3FB950;
        --accent-orange: #FF8F00;
        --accent-orange-hover: #FFB300;
        --accent-purple: #8B5CF6;
        --accent-purple-hover: #A78BFA;

        /* Shadows */
        --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
        --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.25);
        --shadow-lg: 0 8px 32px rgba(0, 0, 0, 0.35);
        --shadow-glow-blue: 0 0 20px rgba(48, 76, 178, 0.3);
        --shadow-glow-gold: 0 0 20px rgba(249, 182, 18, 0.3);
        --shadow-glow-red: 0 0 20px rgba(200, 16, 46, 0.3);

        /* Border Radius */
        --radius-sm: 6px;
        --radius-md: 10px;
        --radius-lg: 16px;
        --radius-full: 9999px;

        /* Transitions */
        --transition-fast: 0.15s ease;
        --transition-normal: 0.25s ease;
        --transition-slow: 0.4s ease;

        /* Fonts */
        --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        --font-mono: 'SF Mono', 'Fira Code', Consolas, monospace;
    }

    /* ============================================ */
    /* GLOBAL RESETS & BASE STYLES                 */
    /* ============================================ */
    /* Apply Inter font to content elements, but NOT to Streamlit's internal icon spans */
    body, p, div, span, a, li, ul, ol, h1, h2, h3, h4, h5, h6,
    input, textarea, select, button, label, th, td,
    .stMarkdown, .stText, .stButton, .stTextInput, .stSelectbox,
    .stMultiSelect, .stTextArea, .stMetric, .stAlert,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] button,
    [data-testid="stSidebar"] label {
        font-family: var(--font-sans);
    }

    .stApp,
    [data-testid="stAppViewContainer"],
    .stMain,
    [data-testid="stMain"],
    [data-testid="stHeader"] {
        background-color: var(--bg-primary) !important;
    }

    /* Remove default Streamlit branding (keep sidebar collapse/expand controls) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    [data-testid="stHeader"] {
        background: transparent !important;
    }
    /* Keep the sidebar expand button visible when sidebar is collapsed */
    [data-testid="collapsedControl"] {
        visibility: visible !important;
    }

    /* ============================================ */
    /* SIDEBAR STYLING                             */
    /* ============================================ */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg,
            rgba(48, 76, 178, 0.95) 0%,
            rgba(26, 45, 107, 0.95) 100%
        );
        backdrop-filter: blur(20px);
        border-right: 1px solid var(--border-default);
    }

    [data-testid="stSidebar"] * {
        color: white !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        background-color: rgba(255, 255, 255, 0.1) !important;
        border: 1px solid rgba(255, 255, 255, 0.2) !important;
        border-radius: var(--radius-md) !important;
        transition: all var(--transition-normal) !important;
        font-weight: 500 !important;
        padding: 0.625rem 1rem !important;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        background-color: var(--accent-gold) !important;
        color: var(--accent-blue) !important;
        border-color: var(--accent-gold) !important;
        box-shadow: 0 0 20px rgba(249, 182, 18, 0.4) !important;
        transform: translateY(-1px);
    }

    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.15) !important;
    }

    /* Sidebar collapse button */
    [data-testid="collapsedControl"] {
        color: var(--text-secondary) !important;
    }

    /* ============================================ */
    /* TYPOGRAPHY                                  */
    /* ============================================ */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em !important;
    }

    h1 {
        background: linear-gradient(135deg, var(--accent-blue) 0%, var(--accent-gold) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    /* Apply text color to main content text only - not component internals */
    .stMarkdown p:not(.metric-label):not(.metric-value):not(.kpi-label):not(.kpi-value),
    .stText {
        color: var(--text-secondary) !important;
    }

    /* Ensure component text keeps proper colors */
    .metric-value,
    .kpi-value,
    .section-header-title,
    .avatar-name,
    .empty-state-message,
    .progress-label-right {
        color: var(--text-primary) !important;
    }

    .metric-label,
    .kpi-label,
    .section-header-subtitle,
    .avatar-subtitle,
    .empty-state-submessage,
    .progress-label-left {
        color: var(--text-secondary) !important;
    }

    /* ============================================ */
    /* PREMIUM COMPONENT STYLES                    */
    /* ============================================ */

    /* Glass Card */
    .glass-card {
        background: linear-gradient(
            135deg,
            rgba(26, 35, 50, 0.85) 0%,
            rgba(45, 59, 79, 0.85) 100%
        );
        backdrop-filter: blur(20px) saturate(180%);
        border: 1px solid var(--border-default);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        box-shadow: var(--shadow-md);
        transition: all var(--transition-normal);
    }

    .glass-card:hover {
        border-color: var(--border-emphasis);
        box-shadow: var(--shadow-lg);
        transform: translateY(-2px);
    }

    /* Premium Metric Card */
    .metric-card-premium {
        background: linear-gradient(
            135deg,
            rgba(26, 35, 50, 0.9) 0%,
            rgba(45, 59, 79, 0.9) 100%
        );
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-default);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        position: relative;
        overflow: hidden;
        transition: all var(--transition-normal);
        box-shadow: var(--shadow-md);
    }

    .metric-card-premium::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, var(--metric-color, var(--accent-blue)) 0%, transparent 100%);
    }

    .metric-card-premium:hover {
        border-color: var(--metric-color, var(--accent-blue));
        box-shadow: 0 0 24px rgba(48, 76, 178, 0.25);
        transform: translateY(-2px);
    }

    .metric-label {
        color: var(--text-secondary);
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.5rem;
    }

    .metric-value {
        color: var(--text-primary);
        font-size: 2.25rem;
        font-weight: 700;
        line-height: 1.2;
        margin-bottom: 0.5rem;
    }

    .metric-icon {
        position: absolute;
        top: 1.5rem;
        right: 1.5rem;
        font-size: 2rem;
        opacity: 0.25;
    }

    .metric-delta {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        font-size: 0.875rem;
        font-weight: 600;
        padding: 0.25rem 0.5rem;
        border-radius: var(--radius-sm);
    }

    .metric-delta.positive {
        color: var(--accent-green);
        background: rgba(46, 160, 67, 0.1);
    }

    .metric-delta.negative {
        color: var(--accent-red);
        background: rgba(200, 16, 46, 0.1);
    }

    /* Status Badge */
    .status-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.375rem 0.875rem;
        border-radius: var(--radius-full);
        font-size: 0.8125rem;
        font-weight: 600;
        letter-spacing: 0.02em;
        transition: all var(--transition-fast);
        white-space: nowrap;
    }

    .status-badge.filled {
        background: var(--badge-color, var(--accent-blue));
        color: white;
        border: 1px solid transparent;
    }

    .status-badge.outline {
        background: transparent;
        color: var(--badge-color, var(--accent-blue));
        border: 1.5px solid var(--badge-color, var(--accent-blue));
    }

    .status-badge.subtle {
        background: rgba(var(--badge-color-rgb, 48, 76, 178), 0.15);
        color: var(--badge-color, var(--accent-blue));
        border: 1px solid rgba(var(--badge-color-rgb, 48, 76, 178), 0.3);
    }

    .status-badge:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }

    /* Stage Badges */
    .stage-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 0.375rem;
        padding: 0.375rem 0.875rem;
        min-width: 160px;
        min-height: 32px;
        border-radius: var(--radius-full);
        font-size: 0.8125rem;
        font-weight: 600;
        background: var(--stage-color, var(--accent-blue));
        color: white;
        border: 1px solid rgba(255, 255, 255, 0.2);
        transition: all var(--transition-fast);
        white-space: nowrap;
        box-sizing: border-box;
    }

    .stage-badge:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    /* Section Header */
    .section-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid transparent;
        border-image: linear-gradient(90deg, var(--accent-blue) 0%, transparent 100%) 1;
    }

    .section-header-title {
        color: var(--text-primary);
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
    }

    .section-header-subtitle {
        color: var(--text-muted);
        font-size: 0.875rem;
        margin-top: 0.25rem;
    }

    .section-header-action {
        color: var(--accent-blue);
        font-size: 0.875rem;
        font-weight: 500;
        cursor: pointer;
        transition: color var(--transition-fast);
    }

    .section-header-action:hover {
        color: var(--accent-blue-hover);
    }

    /* Pipeline Tracker */
    .pipeline-tracker {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 2rem 1rem;
        position: relative;
    }

    .pipeline-stage {
        display: flex;
        flex-direction: column;
        align-items: center;
        position: relative;
        flex: 1;
        z-index: 1;
    }

    .pipeline-dot {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.25rem;
        transition: all var(--transition-normal);
        margin-bottom: 0.75rem;
        position: relative;
    }

    .pipeline-dot.completed {
        background: var(--stage-color, var(--accent-blue));
        border: 2px solid var(--stage-color, var(--accent-blue));
        color: white;
        box-shadow: 0 4px 12px rgba(48, 76, 178, 0.3);
    }

    .pipeline-dot.current {
        background: var(--stage-color, var(--accent-gold));
        border: 3px solid var(--stage-color, var(--accent-gold));
        color: white;
        box-shadow: 0 0 24px rgba(249, 182, 18, 0.5);
        animation: pulse 2s ease-in-out infinite;
        transform: scale(1.15);
    }

    .pipeline-dot.upcoming {
        background: var(--bg-surface);
        border: 2px solid var(--border-default);
        color: var(--text-muted);
    }

    .pipeline-label {
        color: var(--text-secondary);
        font-size: 0.75rem;
        font-weight: 500;
        text-align: center;
        max-width: 100px;
    }

    .pipeline-label.current {
        color: var(--accent-gold);
        font-weight: 700;
    }

    .pipeline-line {
        position: absolute;
        top: 24px;
        left: 0;
        right: 0;
        height: 2px;
        background: var(--border-default);
        z-index: 0;
    }

    .pipeline-line-progress {
        position: absolute;
        top: 0;
        left: 0;
        height: 100%;
        background: linear-gradient(90deg, var(--accent-blue) 0%, var(--accent-gold) 100%);
        transition: width var(--transition-slow);
    }

    /* Empty State */
    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 4rem 2rem;
        text-align: center;
    }

    .empty-state-icon {
        font-size: 4rem;
        opacity: 0.25;
        margin-bottom: 1.5rem;
    }

    .empty-state-message {
        color: var(--text-primary);
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
    }

    .empty-state-submessage {
        color: var(--text-muted);
        font-size: 0.875rem;
    }

    /* Avatar Badge */
    .avatar-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.75rem;
    }

    .avatar-circle {
        width: var(--avatar-size, 48px);
        height: var(--avatar-size, 48px);
        border-radius: 50%;
        background: var(--avatar-gradient);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: calc(var(--avatar-size, 48px) * 0.4);
        border: 2px solid var(--border-emphasis);
        flex-shrink: 0;
    }

    .avatar-text {
        display: flex;
        flex-direction: column;
    }

    .avatar-name {
        color: var(--text-primary);
        font-size: 1rem;
        font-weight: 600;
        line-height: 1.3;
    }

    .avatar-subtitle {
        color: var(--text-muted);
        font-size: 0.8125rem;
        line-height: 1.3;
    }

    /* KPI Row */
    .kpi-row {
        background: linear-gradient(135deg, rgba(26, 35, 50, 0.9) 0%, rgba(45, 59, 79, 0.9) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-default);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        display: flex;
        gap: 2rem;
        box-shadow: var(--shadow-md);
    }

    .kpi-item {
        flex: 1;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 1rem;
        position: relative;
    }

    .kpi-item:not(:last-child)::after {
        content: '';
        position: absolute;
        right: -1rem;
        top: 50%;
        transform: translateY(-50%);
        width: 1px;
        height: 60%;
        background: var(--border-default);
    }

    .kpi-icon {
        font-size: 2rem;
        margin-bottom: 0.75rem;
        /* No fixed filter - color is set inline per KPI */
    }

    .kpi-value {
        color: var(--text-primary);
        font-size: 1.75rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }

    .kpi-label {
        color: var(--text-secondary);
        font-size: 0.875rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Progress Bar */
    .progress-bar-container {
        width: 100%;
        background: var(--bg-surface);
        border-radius: var(--radius-full);
        overflow: hidden;
        position: relative;
        margin: 0.5rem 0;
    }

    .progress-bar-fill {
        height: var(--progress-height, 8px);
        background: linear-gradient(90deg, var(--progress-color, var(--accent-blue)) 0%, var(--progress-color-end, var(--accent-gold)) 100%);
        border-radius: var(--radius-full);
        transition: width var(--transition-slow);
        box-shadow: 0 0 12px rgba(48, 76, 178, 0.4);
    }

    .progress-label {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 0.5rem;
        font-size: 0.75rem;
    }

    .progress-label-left {
        color: var(--text-secondary);
        font-weight: 500;
    }

    .progress-label-right {
        color: var(--text-primary);
        font-weight: 700;
    }

    /* Card Grid */
    .card-grid {
        display: grid;
        grid-template-columns: repeat(var(--grid-columns, 3), 1fr);
        gap: 1.5rem;
        margin: 1.5rem 0;
    }

    @media (max-width: 1200px) {
        .card-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }

    @media (max-width: 768px) {
        .card-grid {
            grid-template-columns: 1fr;
        }
    }

    /* ============================================ */
    /* STREAMLIT COMPONENT OVERRIDES               */
    /* ============================================ */

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
        border-bottom: 2px solid var(--border-default);
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 1.5rem;
        background: transparent;
        border-radius: var(--radius-md) var(--radius-md) 0 0;
        color: var(--text-secondary);
        font-weight: 600;
        transition: all var(--transition-fast);
    }

    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(255, 255, 255, 0.05);
        color: var(--text-primary);
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: var(--accent-blue);
        background: rgba(48, 76, 178, 0.1);
    }

    .stTabs [data-baseweb="tab-highlight"] {
        background-color: var(--accent-blue) !important;
        height: 3px;
    }

    /* Buttons */
    .stButton > button {
        background: var(--bg-surface);
        border: 1px solid var(--border-default);
        border-radius: var(--radius-md);
        color: var(--text-primary);
        font-weight: 600;
        padding: 0.625rem 1.25rem;
        transition: all var(--transition-normal);
    }

    .stButton > button:hover {
        background: var(--bg-surface-hover);
        border-color: var(--border-emphasis);
        box-shadow: var(--shadow-md);
        transform: translateY(-1px);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent-red) 0%, var(--accent-red-hover) 100%);
        border-color: var(--accent-red);
        color: white;
        box-shadow: 0 4px 12px rgba(200, 16, 46, 0.3);
    }

    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, var(--accent-red-hover) 0%, var(--accent-red) 100%);
        box-shadow: 0 6px 20px rgba(200, 16, 46, 0.4);
        transform: translateY(-2px);
    }

    .stButton > button[kind="secondary"] {
        background: transparent;
        border: 1.5px solid var(--accent-blue);
        color: var(--accent-blue);
    }

    .stButton > button[kind="secondary"]:hover {
        background: rgba(48, 76, 178, 0.1);
        box-shadow: 0 0 20px rgba(48, 76, 178, 0.2);
    }

    /* Text Inputs */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > div,
    .stMultiSelect > div > div > div {
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
        transition: all var(--transition-fast) !important;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > div:focus,
    .stMultiSelect > div > div > div:focus {
        border-color: var(--accent-blue) !important;
        box-shadow: 0 0 0 3px rgba(48, 76, 178, 0.1) !important;
    }

    /* Metrics */
    .stMetric {
        background: linear-gradient(135deg, rgba(26, 35, 50, 0.9) 0%, rgba(45, 59, 79, 0.9) 100%);
        backdrop-filter: blur(20px);
        border: 1px solid var(--border-default);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        box-shadow: var(--shadow-md);
    }

    .stMetric label {
        color: var(--text-secondary) !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .stMetric [data-testid="stMetricValue"] {
        color: var(--text-primary) !important;
        font-size: 2rem !important;
        font-weight: 700 !important;
    }

    .stMetric [data-testid="stMetricDelta"] {
        font-weight: 600 !important;
    }

    /* DataFrames/Tables */
    .stDataFrame,
    [data-testid="stDataFrame"] {
        background: var(--bg-surface);
        border: 1px solid var(--border-default);
        border-radius: var(--radius-lg);
        overflow: hidden;
    }

    .stDataFrame table,
    [data-testid="stDataFrame"] table {
        background: transparent !important;
    }

    .stDataFrame thead tr,
    [data-testid="stDataFrame"] thead tr {
        background: rgba(48, 76, 178, 0.1) !important;
        border-bottom: 2px solid var(--accent-blue) !important;
    }

    .stDataFrame th,
    [data-testid="stDataFrame"] th {
        color: var(--text-primary) !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.75rem !important;
        padding: 1rem !important;
    }

    .stDataFrame td,
    [data-testid="stDataFrame"] td {
        color: var(--text-secondary) !important;
        padding: 0.875rem 1rem !important;
        border-bottom: 1px solid var(--border-subtle) !important;
    }

    .stDataFrame tbody tr:hover,
    [data-testid="stDataFrame"] tbody tr:hover {
        background: rgba(255, 255, 255, 0.03) !important;
    }

    /* ============================================ */
    /* EXPANDER STYLING & ICON FIX                 */
    /* ============================================ */

    /* Expander header styling */
    .streamlit-expanderHeader,
    [data-testid="stExpander"] summary {
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-default) !important;
        border-radius: var(--radius-md) !important;
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        transition: all var(--transition-fast) !important;
        padding-left: 2.5rem !important;
        position: relative !important;
        min-height: 2.75rem !important;
        display: flex !important;
        align-items: center !important;
    }

    .streamlit-expanderHeader:hover,
    [data-testid="stExpander"] summary:hover {
        background: var(--bg-surface-hover) !important;
        border-color: var(--border-emphasis) !important;
    }

    /* Expander content styling */
    .streamlit-expanderContent,
    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-default) !important;
        border-top: none !important;
        border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
    }

    /* Hide browser default details marker */
    details summary::-webkit-details-marker,
    details summary::marker {
        display: none !important;
    }

    /* Hide Streamlit's broken icon elements (Material Icons text showing as "arrow_right", etc) */
    [data-testid="stExpander"] summary svg,
    [data-testid="stExpander"] summary [data-testid*="icon"],
    [data-testid="stExpander"] summary [class*="icon"],
    [data-testid="stExpander"] summary > div:first-child,
    [data-testid="stExpander"] summary > span:first-of-type:empty,
    .streamlit-expanderHeader svg,
    .streamlit-expanderHeader [class*="icon"],
    .streamlit-expanderHeader > div:first-child,
    .streamlit-expanderHeader > span:first-of-type:empty {
        display: none !important;
        visibility: hidden !important;
        position: absolute !important;
        left: -9999px !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        font-size: 0 !important;
        line-height: 0 !important;
        opacity: 0 !important;
    }

    /* Add custom CSS arrow icon to replace broken Material Icons */
    .streamlit-expanderHeader::before,
    [data-testid="stExpander"] summary::before {
        content: '▶' !important;
        position: absolute !important;
        left: 1rem !important;
        top: 50% !important;
        transform: translateY(-50%) !important;
        font-size: 0.875rem !important;
        color: var(--text-secondary) !important;
        transition: transform var(--transition-fast) !important;
        display: inline-block !important;
        line-height: 1 !important;
        z-index: 10 !important;
    }

    /* Rotate arrow when expander is open */
    details[open] .streamlit-expanderHeader::before,
    details[open] > summary::before,
    [data-testid="stExpander"][open] summary::before {
        transform: translateY(-50%) rotate(90deg) !important;
    }

    /* Ensure expander label text remains visible */
    .streamlit-expanderHeader p,
    .streamlit-expanderHeader strong,
    .streamlit-expanderHeader span:not(:first-of-type),
    .streamlit-expanderHeader div:not(:first-child),
    [data-testid="stExpander"] summary p,
    [data-testid="stExpander"] summary strong,
    [data-testid="stExpander"] summary span:not(:first-of-type),
    [data-testid="stExpander"] summary div:not(:first-child) {
        visibility: visible !important;
        opacity: 1 !important;
        font-size: inherit !important;
        position: relative !important;
        display: inline !important;
        line-height: inherit !important;
    }

    /* Alerts */
    .stAlert {
        background: var(--bg-surface) !important;
        border: 1px solid var(--border-default) !important;
        border-left: 4px solid var(--accent-blue) !important;
        border-radius: var(--radius-md) !important;
        backdrop-filter: blur(20px);
    }

    .stAlert[data-baseweb="notification"][kind="info"] {
        border-left-color: var(--accent-blue) !important;
        background: rgba(48, 76, 178, 0.1) !important;
    }

    .stAlert[data-baseweb="notification"][kind="success"] {
        border-left-color: var(--accent-green) !important;
        background: rgba(46, 160, 67, 0.1) !important;
    }

    .stAlert[data-baseweb="notification"][kind="warning"] {
        border-left-color: var(--accent-gold) !important;
        background: rgba(249, 182, 18, 0.1) !important;
    }

    .stAlert[data-baseweb="notification"][kind="error"] {
        border-left-color: var(--accent-red) !important;
        background: rgba(200, 16, 46, 0.1) !important;
    }

    /* File Uploader */
    .stFileUploader {
        background: var(--bg-surface) !important;
        border: 2px dashed var(--border-default) !important;
        border-radius: var(--radius-lg) !important;
        transition: all var(--transition-fast) !important;
    }

    .stFileUploader:hover {
        border-color: var(--accent-blue) !important;
        background: rgba(48, 76, 178, 0.05) !important;
    }

    /* Spinner */
    .stSpinner > div {
        border-color: var(--accent-blue) !important;
    }

    /* ============================================ */
    /* SCROLLBARS                                  */
    /* ============================================ */
    ::-webkit-scrollbar {
        width: 12px;
        height: 12px;
    }

    ::-webkit-scrollbar-track {
        background: var(--bg-primary);
    }

    ::-webkit-scrollbar-thumb {
        background: var(--bg-surface);
        border-radius: var(--radius-sm);
        border: 2px solid var(--bg-primary);
    }

    ::-webkit-scrollbar-thumb:hover {
        background: var(--bg-surface-hover);
    }

    /* ============================================ */
    /* ANIMATIONS                                  */
    /* ============================================ */
    @keyframes pulse {
        0%, 100% {
            box-shadow: 0 0 24px rgba(249, 182, 18, 0.5);
        }
        50% {
            box-shadow: 0 0 32px rgba(249, 182, 18, 0.8);
        }
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .fade-in {
        animation: fadeIn 0.4s ease-out;
    }

    @keyframes slideIn {
        from {
            opacity: 0;
            transform: translateX(-20px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    .slide-in {
        animation: slideIn 0.4s ease-out;
    }
</style>
"""
    return _CACHED_CSS


def metric_card(label: str, value: str, delta=None, icon=None, color='#304CB2') -> str:
    """
    Premium metric card with glass-morphism background.

    Args:
        label: Metric label (e.g., "Total Candidates")
        value: Metric value (e.g., "142")
        delta: Optional delta indicator - dict with 'value' and 'direction' ('up'/'down')
        icon: Optional icon HTML entity (e.g., '&#128100;')
        color: Accent color (default: Southwest Blue)

    Returns:
        HTML string for metric card
    """
    delta_html = ''
    if delta:
        if isinstance(delta, dict):
            direction = delta.get('direction', 'up')
            delta_value = safe(delta.get('value', ''))
        else:
            direction = 'up'
            delta_value = safe(str(delta))
        arrow = '↑' if direction == 'up' else '↓'
        delta_class = 'positive' if direction == 'up' else 'negative'
        delta_html = f'<div class="metric-delta {delta_class}">{arrow} {delta_value}</div>'

    icon_html = f'<div class="metric-icon">{icon}</div>' if icon else ''

    return _clean_html(f"""
    <div class="metric-card-premium" style="--metric-color: {color};">
        {icon_html}
        <div class="metric-label">{safe(label)}</div>
        <div class="metric-value">{safe(value)}</div>
        {delta_html}
    </div>
    """)


def status_badge(text: str, color=None, variant='filled') -> str:
    """
    Modern pill badge with multiple variants.

    Args:
        text: Badge text
        color: Badge color (auto-detects for common statuses if not provided)
        variant: 'filled', 'outline', or 'subtle'

    Returns:
        HTML string for status badge
    """
    # Auto-color detection
    if color is None:
        text_lower = text.lower()
        if text_lower in ['active', 'hired', 'approved', 'success', 'completed']:
            color = '#2EA043'
        elif text_lower in ['rejected', 'failed', 'error', 'expired']:
            color = '#F85149'
        elif text_lower in ['pending', 'warning', 'in progress']:
            color = '#F9B612'
        elif text_lower in ['inactive', 'paused']:
            color = '#8B949E'
        else:
            color = '#304CB2'

    return _clean_html(f"""
    <span class="status-badge {variant}" style="--badge-color: {color};">{safe(text)}</span>
    """)


def stage_badge(stage: str) -> str:
    """
    Convenience wrapper for stage badges with proper coloring and icons.

    Args:
        stage: Pipeline stage name

    Returns:
        HTML string for stage badge
    """
    color = get_stage_color(stage)
    icon = get_stage_icon(stage)

    return _clean_html(f"""
    <span class="stage-badge" style="--stage-color: {color};">
        {icon} {safe(stage)}
    </span>
    """)


def section_header(title: str, subtitle=None, action_hint=None) -> str:
    """
    Premium section divider with gradient underline accent.

    Args:
        title: Section title
        subtitle: Optional subtitle text
        action_hint: Optional action hint text (displayed on the right)

    Returns:
        HTML string for section header
    """
    subtitle_html = f'<div class="section-header-subtitle">{safe(subtitle)}</div>' if subtitle else ''
    action_html = f'<div class="section-header-action">{safe(action_hint)}</div>' if action_hint else ''

    return _clean_html(f"""
    <div class="section-header">
        <div>
            <h3 class="section-header-title">{safe(title)}</h3>
            {subtitle_html}
        </div>
        {action_html}
    </div>
    """)


def pipeline_tracker(stages: list, current_stage: str = None, show_icons=True, stage_counts: dict = None) -> str:
    """
    Connected dot pipeline visualization with animations.

    Args:
        stages: List of stage names in order
        current_stage: Name of the current stage (for single-candidate view)
        show_icons: Whether to show stage icons (always True now for all stages)
        stage_counts: Dict of {stage_name: count} - stages with count > 0 glow

    Returns:
        HTML string for pipeline tracker
    """
    # Determine current index for single-candidate mode
    current_index = -1
    if current_stage:
        try:
            current_index = stages.index(current_stage)
        except ValueError:
            current_index = 0

    # Calculate progress line
    if current_index >= 0 and len(stages) > 1:
        progress_percent = (current_index / (len(stages) - 1)) * 100
    elif stage_counts:
        # Find the furthest stage with candidates for progress line
        furthest = -1
        for i, stage in enumerate(stages):
            if stage_counts.get(stage, 0) > 0:
                furthest = i
        progress_percent = (furthest / (len(stages) - 1)) * 100 if furthest >= 0 and len(stages) > 1 else 0
    else:
        progress_percent = 0

    stage_htmls = []
    for i, stage in enumerate(stages):
        icon = get_stage_icon(stage) if show_icons else '●'
        color = get_stage_color(stage)
        count = stage_counts.get(stage, 0) if stage_counts else 0

        if current_stage:
            # Single-candidate mode: completed / current / upcoming
            if i < current_index:
                status = 'completed'
            elif i == current_index:
                status = 'current'
            else:
                status = 'upcoming'
                color = '#6E7681'
        elif stage_counts:
            # Overview mode: glow stages that have candidates
            if count > 0:
                status = 'current'
            else:
                status = 'upcoming'
                color = '#6E7681'
        else:
            status = 'upcoming'
            color = '#6E7681'

        label_class = 'current' if status == 'current' else ''

        # Show count badge in overview mode
        count_html = f'<div style="color: var(--text-muted); font-size: 0.7rem; margin-top: 0.25rem;">{count}</div>' if stage_counts and count > 0 else ''

        stage_htmls.append(f"""
        <div class="pipeline-stage">
            <div class="pipeline-dot {status}" style="--stage-color: {color};">
                {icon}
            </div>
            <div class="pipeline-label {label_class}">{safe(stage)}</div>
            {count_html}
        </div>
        """)

    return _clean_html(f"""
    <div class="pipeline-tracker">
        <div class="pipeline-line">
            <div class="pipeline-line-progress" style="width: {progress_percent}%;"></div>
        </div>
        {''.join(stage_htmls)}
    </div>
    """)


def empty_state(message: str, submessage=None, icon='&#128269;') -> str:
    """
    Styled empty state component.

    Args:
        message: Primary message
        submessage: Optional secondary message
        icon: HTML entity for icon (default: magnifying glass)

    Returns:
        HTML string for empty state
    """
    submessage_html = f'<div class="empty-state-submessage">{safe(submessage)}</div>' if submessage else ''

    return _clean_html(f"""
    <div class="empty-state">
        <div class="empty-state-icon">{icon}</div>
        <div class="empty-state-message">{safe(message)}</div>
        {submessage_html}
    </div>
    """)


def avatar_badge(name: str, subtitle=None, size='md') -> str:
    """
    Avatar with initials and gradient background based on name hash.

    Args:
        name: Full name
        subtitle: Optional subtitle (e.g., role)
        size: 'sm' (32px), 'md' (48px), 'lg' (64px)

    Returns:
        HTML string for avatar badge
    """
    # Get initials (first letter of first two words)
    parts = name.strip().split()
    initials = ''.join([p[0].upper() for p in parts[:2]]) if parts else '?'

    # Generate gradient based on name hash
    name_hash = sum(ord(c) for c in name)
    hue1 = (name_hash * 137) % 360
    hue2 = (hue1 + 60) % 360
    gradient = f"linear-gradient(135deg, hsl({hue1}, 70%, 50%) 0%, hsl({hue2}, 70%, 40%) 100%)"

    sizes = {
        'sm': '32px',
        'md': '48px',
        'lg': '64px'
    }
    avatar_size = sizes.get(size, '48px')

    subtitle_html = f'<div class="avatar-subtitle">{safe(subtitle)}</div>' if subtitle else ''

    return _clean_html(f"""
    <div class="avatar-badge">
        <div class="avatar-circle" style="--avatar-size: {avatar_size}; --avatar-gradient: {gradient};">
            {initials}
        </div>
        <div class="avatar-text">
            <div class="avatar-name">{safe(name)}</div>
            {subtitle_html}
        </div>
    </div>
    """)


def kpi_row(items: list) -> str:
    """
    Row of KPI items inside a glass card with dividers.

    Args:
        items: List of dicts with keys: 'label', 'value', 'icon' (optional), 'color' (optional)
        Example: [{'label': 'Total', 'value': '42', 'icon': '👤', 'color': '#304CB2'}, ...]

    Returns:
        HTML string for KPI row
    """
    kpi_htmls = []
    for item in items:
        icon_html = f'<div class="kpi-icon" style="color: {item.get("color", "#304CB2")};">{item.get("icon", "")}</div>' if item.get('icon') else ''
        kpi_htmls.append(f"""
        <div class="kpi-item">
            {icon_html}
            <div class="kpi-value">{safe(item.get('value', '0'))}</div>
            <div class="kpi-label">{safe(item.get('label', ''))}</div>
        </div>
        """)

    return _clean_html(f"""
    <div class="kpi-row">
        {''.join(kpi_htmls)}
    </div>
    """)


def data_table_css() -> str:
    """
    Returns CSS specifically for premium st.dataframe styling.
    This is already included in premium_css(), so this is a no-op for backwards compatibility.

    Returns:
        Empty string (styles are in premium_css())
    """
    return ""


def progress_bar_html(value: float, max_value=100, color=None, height='8px', show_label=True) -> str:
    """
    Custom progress bar with gradient fill and smooth animation.

    Args:
        value: Current value
        max_value: Maximum value (default: 100)
        color: Bar color (default: blue to gold gradient)
        height: Bar height (default: '8px')
        show_label: Whether to show percentage label

    Returns:
        HTML string for progress bar
    """
    percent = (value / max_value * 100) if max_value > 0 else 0
    percent = min(100, max(0, percent))  # Clamp between 0-100

    color_start = color if color else '#304CB2'
    color_end = color if color else '#F9B612'

    label_html = ''
    if show_label:
        label_html = f"""
        <div class="progress-label">
            <span class="progress-label-left">{safe(f'{value}/{max_value}')}</span>
            <span class="progress-label-right">{percent:.1f}%</span>
        </div>
        """

    return _clean_html(f"""
    <div class="progress-bar-container" style="--progress-height: {height};">
        <div class="progress-bar-fill" style="width: {percent}%; --progress-color: {color_start}; --progress-color-end: {color_end};"></div>
    </div>
    {label_html}
    """)


def card_grid_open(columns=3) -> str:
    """
    Opens a CSS grid container for card layouts.

    Args:
        columns: Number of columns (default: 3)

    Returns:
        HTML string to open grid
    """
    return f'<div class="card-grid" style="--grid-columns: {columns};">'


def card_grid_close() -> str:
    """
    Closes the card grid container.

    Returns:
        HTML string to close grid
    """
    return '</div>'
