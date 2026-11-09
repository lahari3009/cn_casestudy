import streamlit as st
import time
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx

st.set_page_config(
    page_title="Network Failure Detection & Redundancy",
    page_icon="🌐",
    layout="wide"
)

# ---------- Styling (black theme, white text, colourful accents) ----------
st.markdown("""
<style>
/* Base black background + white text */
[data-testid="stAppViewContainer"], .main, [data-testid="stHeader"] {
    background: #000000 !important;
    color: #ffffff !important;
}
[data-testid="stSidebar"] {
    background: #0a0a0f !important;
    border-right: 1px solid #1f2937;
}
h1, h2, h3, h4, p, label, span, li, div[data-testid="stMarkdownContainer"] {
    color: #ffffff;
}
h1 {
    background: linear-gradient(90deg, #22d3ee, #a78bfa, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
h2, h3 {border-left: 4px solid #22d3ee; padding-left: 10px;}
[data-testid="stCaptionContainer"], .stCaption, small {color: #cbd5e1 !important;}

/* Metric cards: white numbers, coloured accent */
div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #0d1117, #141b2d);
    border: 1px solid #22d3ee55;
    border-top: 3px solid #22d3ee;
    padding: 14px; border-radius: 12px;
    box-shadow: 0 0 14px #22d3ee22;
}
div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] * {
    color: #ffffff !important; font-weight: 800;
    /* FIX: stop Streamlit from truncating long values with "..." */
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    word-break: break-word !important;
    line-height: 1.2 !important;
    font-size: 1.7rem !important;
}
div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] * {
    color: #67e8f9 !important; font-weight: 600;
    /* FIX: let long labels wrap instead of "Packets received (simul..." */
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
}

/* Sidebar widgets: selectbox (failure type) fully visible */
/* Closed box: selected value */
div[data-baseweb="select"] > div {
    background: #0f172a !important;
    border: 2px solid #22d3ee !important;
    border-radius: 10px !important;
}
div[data-baseweb="select"] span, div[data-baseweb="select"] div,
div[data-baseweb="select"] input {
    color: #fde047 !important;          /* yellow selected text */
    -webkit-text-fill-color: #fde047 !important;
    font-weight: 700 !important;
}
div[data-baseweb="select"] svg {fill: #22d3ee !important; color: #22d3ee !important;}

/* Open dropdown list (options) */
div[data-baseweb="popover"], div[data-baseweb="popover"] > div,
div[data-baseweb="popover"] ul, div[data-baseweb="menu"],
[data-testid="stSelectboxVirtualDropdown"], ul[role="listbox"] {
    background: #0f172a !important;
    border: 1px solid #22d3ee !important;
    border-radius: 10px !important;
}
li[role="option"], ul[role="listbox"] li,
li[role="option"] *, ul[role="listbox"] li * {
    background: #0f172a !important;
    color: #ffffff !important;           /* white options */
    -webkit-text-fill-color: #ffffff !important;
    font-weight: 600 !important;
    font-size: 15px !important;
}
li[role="option"]:hover, li[role="option"]:hover *,
li[role="option"][aria-selected="true"], li[role="option"][aria-selected="true"] *,
ul[role="listbox"] li:hover, ul[role="listbox"] li:hover * {
    background: #22d3ee !important;      /* cyan highlight */
    color: #000000 !important;           /* black text on highlight */
    -webkit-text-fill-color: #000000 !important;
}
/* Slider numbers */
[data-testid="stSliderThumbValue"], [data-testid="stSliderTickBarMin"],
[data-testid="stSliderTickBarMax"], div[data-baseweb="slider"] div {
    color: #ffffff !important;
}
[data-testid="stSliderThumbValue"] {font-weight: 700; color: #22d3ee !important;}

/* Buttons */
.stButton button {
    border-radius: 10px; font-weight: 700; color: #ffffff !important;
    background: linear-gradient(90deg, #0891b2, #7c3aed);
    border: none; transition: transform .15s, box-shadow .15s;
}
.stButton button:hover {
    transform: translateY(-2px); box-shadow: 0 0 14px #22d3ee88; color: #ffffff !important;
}
.stButton button p {color: #ffffff !important;}

/* Progress bar */
div[data-testid="stProgress"] > div > div > div > div {
    background: linear-gradient(90deg, #22c55e, #facc15, #ef4444);
}

/* Info box */
div[data-testid="stAlert"] {
    background: #0c1a2b !important; border: 1px solid #22d3ee66; border-radius: 10px;
}
div[data-testid="stAlert"] * {color: #ffffff !important;}
</style>
""", unsafe_allow_html=True)

# ---------- Session state ----------
if "failed_link" not in st.session_state:
    st.session_state.failed_link = None
if "failed_router" not in st.session_state:
    st.session_state.failed_router = None
if "events" not in st.session_state:
    st.session_state.events = []
if "total_sent" not in st.session_state:
    st.session_state.total_sent = 0
if "total_received" not in st.session_state:
    st.session_state.total_received = 0
if "total_lost" not in st.session_state:
    st.session_state.total_lost = 0
if "last_recovery" not in st.session_state:
    st.session_state.last_recovery = None

def add_event(message, level="INFO"):
    st.session_state.events.insert(0, {
        "Time": datetime.now().strftime("%H:%M:%S"),
        "Level": level,
        "Event": message
    })
    st.session_state.events = st.session_state.events[:100]

def reset_network():
    st.session_state.failed_link = None
    st.session_state.failed_router = None
    st.session_state.total_sent = 0
    st.session_state.total_received = 0
    st.session_state.total_lost = 0
    st.session_state.last_recovery = None
    st.session_state.events = []
    add_event("Network reset. All links restored.")

# ---------- Table colouring helpers ----------
def _cell_style(val):
    colors = {
        "DOWN": "background-color:#7f1d1d;color:#ffffff;font-weight:bold",
        "Failed": "background-color:#7f1d1d;color:#ffffff;font-weight:bold",
        "UP": "background-color:#14532d;color:#ffffff;font-weight:bold",
        "Available": "background-color:#14532d;color:#ffffff",
        "Backup path": "background-color:#075985;color:#ffffff;font-weight:bold",
        "CRITICAL": "background-color:#7f1d1d;color:#ffffff;font-weight:bold",
        "WARNING": "background-color:#78350f;color:#ffffff;font-weight:bold",
        "RECOVERY": "background-color:#14532d;color:#ffffff;font-weight:bold",
        "INFO": "background-color:#1e293b;color:#ffffff",
    }
    return colors.get(val, "color:#ffffff;background-color:#0d1117")

def styled(df):
    styler = df.style
    apply_fn = getattr(styler, "map", None) or styler.applymap
    return apply_fn(_cell_style)

# ---------- Header ----------
st.title("🌐 Network Failure Detection & Redundancy")
st.caption("OSPF-inspired failover demonstration • Main route, backup route, packet-loss estimate, and event history")

with st.sidebar:
    st.header("⚙️ Simulation Controls")
    st.write("Choose a failure to simulate.")
    failure_choice = st.selectbox(
        "Failure type",
        ["R1–R2 link failure", "R2–R4 link failure", "R1–R3 link failure", "R3–R4 link failure", "Router R2 failure", "Router R3 failure"]
    )
    packet_count = st.slider("Packets to send", min_value=10, max_value=100, value=20, step=10)
    st.caption("Statistics are simulated for demonstration; they are not captured from Packet Tracer.")

    if st.button("🚨 Simulate selected failure", use_container_width=True):
        link_map = {
            "R1–R2 link failure": ("R1", "R2"),
            "R2–R4 link failure": ("R2", "R4"),
            "R1–R3 link failure": ("R1", "R3"),
            "R3–R4 link failure": ("R3", "R4"),
        }
        if "link failure" in failure_choice:
            st.session_state.failed_link = link_map[failure_choice]
            st.session_state.failed_router = None
            add_event(f"Failure detected: link {failure_choice.replace(' link failure','')} is DOWN.", "CRITICAL")
        else:
            st.session_state.failed_router = failure_choice.split()[1]
            st.session_state.failed_link = None
            add_event(f"Failure detected: {st.session_state.failed_router} is DOWN.", "CRITICAL")

        # Simulated packet outcomes: transparent, illustrative values only.
        lost = max(1, round(packet_count * 0.10))
        received = packet_count - lost
        st.session_state.total_sent += packet_count
        st.session_state.total_received += received
        st.session_state.total_lost += lost
        add_event(f"Sent {packet_count} simulated packets; {lost} marked lost during transition.", "WARNING")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Restore / activate backup", use_container_width=True):
            st.session_state.failed_link = None
            st.session_state.failed_router = None
            st.session_state.last_recovery = datetime.now().strftime("%H:%M:%S")
            add_event("Network path restored in dashboard simulation. Verify real OSPF route in Packet Tracer.", "RECOVERY")
    with c2:
        if st.button("↻ Reset all", use_container_width=True):
            reset_network()

# ---------- Determine route status ----------
failed_router = st.session_state.failed_router
failed_link = st.session_state.failed_link
main_route = [("PC0", "R1"), ("R1", "R2"), ("R2", "R4"), ("R4", "PC1")]
backup_route = [("PC0", "R1"), ("R1", "R3"), ("R3", "R4"), ("R4", "PC1")]

def edge_is_down(edge):
    a, b = edge
    if failed_router and failed_router in edge:
        return True
    if failed_link and set(failed_link) == set(edge):
        return True
    return False

main_available = all(not edge_is_down(e) for e in main_route)
backup_available = all(not edge_is_down(e) for e in backup_route)

if main_available:
    active_route = "Main route (PC0 → R1 → R2 → R4 → PC1)"
    network_status = "OPERATIONAL"
    status_color = "🟢"
elif backup_available:
    active_route = "Backup route (PC0 → R1 → R3 → R4 → PC1)"
    network_status = "FAILOVER ACTIVE"
    status_color = "🟠"
else:
    active_route = "No complete route available"
    network_status = "CONNECTIVITY LOST"
    status_color = "🔴"

# ---------- Metrics ----------
# FIX: wider first column so the status text has room
m1, m2, m3, m4 = st.columns(4)
m1.metric("Network status", status_color)
m2.metric("Packets sent (simulated)", st.session_state.total_sent)
m3.metric("Packets received (simulated)", st.session_state.total_received)
m4.metric("Packets lost (simulated)", st.session_state.total_lost)

if st.session_state.total_sent:
    loss_rate = st.session_state.total_lost / st.session_state.total_sent * 100
else:
    loss_rate = 0.0

st.progress(min(loss_rate / 100, 1.0), text=f"Illustrative packet-loss rate: {loss_rate:.1f}%")
st.info(f"**Current route decision:** {active_route}")

# ---------- Topology ----------
st.subheader("🗺️ Network Topology")
st.caption("Green = working link • Red = failed link • Cyan = selected backup route")

G = nx.Graph()
positions = {
    "PC0": (0, 1),
    "R1": (1.5, 1),
    "R2": (3, 2),
    "R3": (3, 0),
    "R4": (4.5, 1),
    "PC1": (6, 1)
}
G.add_nodes_from(positions)
all_edges = [
    ("PC0", "R1"), ("R1", "R2"), ("R1", "R3"),
    ("R2", "R4"), ("R3", "R4"), ("R4", "PC1")
]
G.add_edges_from(all_edges)

fig, ax = plt.subplots(figsize=(12, 4.8))
fig.patch.set_facecolor("#000000")
ax.set_facecolor("#000000")

healthy_edges, down_edges, backup_edges = [], [], []
for edge in all_edges:
    if edge_is_down(edge):
        down_edges.append(edge)
    elif not main_available and backup_available and (edge in backup_route or (edge[1], edge[0]) in backup_route):
        backup_edges.append(edge)
    else:
        healthy_edges.append(edge)

nx.draw_networkx_edges(G, positions, edgelist=healthy_edges, width=3, edge_color="#22c55e", ax=ax)
if backup_edges:
    nx.draw_networkx_edges(G, positions, edgelist=backup_edges, width=5, edge_color="#22d3ee", ax=ax)
if down_edges:
    nx.draw_networkx_edges(G, positions, edgelist=down_edges, width=4, edge_color="#ef4444", style="dashed", ax=ax)

node_colors = []
for node in G.nodes:
    if node == failed_router:
        node_colors.append("#ef4444")
    elif node in ("PC0", "PC1"):
        node_colors.append("#7c3aed")
    else:
        node_colors.append("#0891b2")
nx.draw_networkx_nodes(G, positions, node_color=node_colors, node_size=2300, edgecolors="#ffffff", linewidths=2, ax=ax)
nx.draw_networkx_labels(G, positions, font_color="white", font_size=11, font_weight="bold", ax=ax)

for a, b in all_edges:
    x1, y1 = positions[a]
    x2, y2 = positions[b]
    mx, my = (x1+x2)/2, (y1+y2)/2
    label = ""
    if set((a,b)) == {"R1","R2"}: label = "10.0.12.0/30"
    elif set((a,b)) == {"R1","R3"}: label = "10.0.13.0/30"
    elif set((a,b)) == {"R2","R4"}: label = "10.0.24.0/30"
    elif set((a,b)) == {"R3","R4"}: label = "10.0.34.0/30"
    elif set((a,b)) == {"PC0","R1"}: label = "192.168.1.0/24"
    elif set((a,b)) == {"R4","PC1"}: label = "192.168.4.0/24"
    if label:
        ax.text(mx, my + (0.14 if y2 >= y1 else -0.14), label, color="#ffffff",
                fontsize=8.5, ha="center", va="center",
                bbox=dict(facecolor="#271B11", edgecolor="#b4ee22", alpha=0.95, pad=2.5, boxstyle="round"))
ax.axis("off")
plt.tight_layout()
st.pyplot(fig, use_container_width=True)
plt.close(fig)

# ---------- Status and event log ----------
left, right = st.columns([1, 1])
with left:
    st.subheader("🔎 Link Status")
    link_rows = []
    for a, b in all_edges:
        is_down = edge_is_down((a,b))
        link_rows.append({
            "Connection": f"{a} — {b}",
            "Status": "DOWN" if is_down else "UP",
            "Type": "Failed" if is_down else ("Backup path" if not main_available and backup_available and ((a,b) in backup_route or (b,a) in backup_route) else "Available")
        })
    st.dataframe(styled(pd.DataFrame(link_rows)), hide_index=True, use_container_width=True)

with right:
    st.subheader("📋 Event History")
    if st.session_state.events:
        st.dataframe(styled(pd.DataFrame(st.session_state.events)), hide_index=True, use_container_width=True)
    else:
        st.write("No events yet. Use the sidebar to simulate a failure.")