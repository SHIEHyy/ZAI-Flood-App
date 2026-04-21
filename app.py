import streamlit as st
import time

# --- 1. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="Z.AI - Emergency Escape", page_icon="🧠", layout="centered")

# Custom CSS for a professional "Crisis App" look
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
        height: 60px;
        font-size: 18px;
        font-weight: bold;
        border-radius: 12px;
    }
    .stRadio > label { font-size: 20px !important; font-weight: bold; }
    .stCheckbox { font-size: 18px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR DEMO CONTROLS ---
with st.sidebar:
    st.header("⚙️ Judge's Demo Panel")
    st.info("Use these to simulate real-world emergency conditions.")
    sim_battery = st.slider("Simulate Device Battery", 0, 100, 75)
    st.divider()
    st.caption("Z.AI Mesh Protocol: v1.0.4")

# --- 3. PHASE 1: ALERT & CHECKLIST ---
st.title("🧠 Z.AI Emergency Portal")

if sim_battery <= 15:
    st.error(f"⚠️ CRITICAL BATTERY: {sim_battery}% - Switching to Ultra-Power Save Mode")
else:
    st.warning("⚠️ FLOOD WARNING: 15 MINUTES TO EVACUATE")

with st.expander("📋 AI Escape Checklist (Complete Immediately)", expanded=True):
    st.checkbox("Grab Identification & Documents")
    st.checkbox("Emergency Medication")
    st.checkbox("Power Bank & Cables")
    st.checkbox("Bottled Water")

st.divider()

# --- 4. PHASE 2: SITUATIONAL DATA ---
st.header("🚨 Rapid SOS Status")

# Water Level Selection
st.subheader("1. Current Water Level")
water_level = st.radio(
    "Select the depth at your location:",
    ["1. Above Knees 🦵", "2. Above Hips 👤", "3. Around Chest ⚠️"],
    index=None,
    help="Tap the option that matches your situation"
)

if water_level == "3. Around Chest ⚠️":
    st.error("PRIORITY P0: Rescuers alerted to life-threatening depth.")

# Group Status
st.subheader("2. People with you")
col_p1, col_p2 = st.columns(2)
with col_p1:
    people_count = st.selectbox("Number of people:", ["Just Me", "2-4 People", "5+ People"])
with col_p2:
    vulnerable = st.multiselect("Special needs:", ["Children", "Elderly", "Disabled"])

# Survival Position
st.subheader("3. Current Position & Hazards")
position = st.selectbox("Where are you located?", [
    "Ground Level", 
    "On the Rooftop", 
    "Hanging on a Tree", 
    "Inside Building (Upper Floor)",
    "Floating with a Log/Debris"
])

# Safety Gear & Hazards
hazards = st.multiselect("Identify Immediate Dangers:", 
                         ["Falling Trees", "Downed Power Lines", "Fast Current", "Tall Building Nearby (Safe)"])
is_wearing_jacket = st.toggle("🦺 I am wearing a life jacket")

# --- 5. PHASE 3: SUBMIT / SOS ---
st.divider()

if st.button("🔥 SEND STANDARDIZED SOS SIGNAL", type="primary"):
    if water_level is None:
        st.warning("Please select a water level before sending.")
    else:
        with st.spinner("Encrypting & Broadcasting via Mesh Network..."):
            time.sleep(2)
            st.success("✅ SOS Transmitted!")
            st.balloons()
            st.info(f"Summary Sent: {water_level} | {people_count} | Position: {position}")

# --- 6. PHASE 4: EXTREME CONDITIONS ---
if st.button("🔦 Activate LED Rescue Signal"):
    st.toast("LED Beacon Activated!")
    flash_placeholder = st.empty()
    # Flash effect
    for _ in range(4):
        flash_placeholder.markdown("<div style='background-color: white; height: 100px; border-radius: 10px; border: 2px solid grey;'></div>", unsafe_allow_html=True)
        time.sleep(0.3)
        flash_placeholder.markdown("<div style='background-color: black; height: 100px; border-radius: 10px; border: 2px solid grey;'></div>", unsafe_allow_html=True)
        time.sleep(0.3)
    flash_placeholder.empty()
    st.success("Visual Beacon is pulsing. Device screen dimmed to save battery.")

# --- 7. FOOTER STATUS ---
st.divider()
battery_color = "red" if sim_battery <= 20 else "#00FF00"
st.markdown(f"""
    <div style="text-align: center; padding: 10px;">
        <span style="color: {battery_color}; font-weight: bold;">🔋 Battery: {sim_battery}%</span> | 
        📍 <b>GPS: 3.1390° N, 101.6869° E</b>
    </div>
    """, unsafe_allow_html=True)