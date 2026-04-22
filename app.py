import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import time
from datetime import datetime
import uuid
import random
from google import genai
import traceback

# --- BACKEND LOGIC (Z'Ai COMMANDER) ---

# --- 0. FIREBASE & AI CLIENT SETUP ---
if not firebase_admin._apps:
    creds_dict = dict(st.secrets["firebase"])
    cred = credentials.Certificate(creds_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client(database_id="shakehand")

# Enter the Z'Ai API Key
client = genai.Client(
    api_key=st.secrets["GEMINI_KEY"],
    http_options={'base_url': 'api.ilmu.ai/v1'}
)

if 'sos_database' not in st.session_state:
    st.session_state.sos_database = []

def process_sos_logic(data):
    """
    This is your core Backend processing logic.
    When the teammate clicks the "Submit" button on the frontend, call this function directly.
    """
    # Basic priority judgment
    priority = "P3" # Start by assuming this is a low-priority case (P3)
    water_level = data.get('water', '')
    env_info = data.get('env', '')
    
    if "Chest" in water_level or "Floating" in env_info or "Hanging" in env_info:
        priority = "P0"
    elif "Hips" in water_level or "Rooftop" in env_info:
        priority = "P1"
    elif "Knees" in water_level:
        priority = "P2"

    # Use AI to analyse victim information 
    user_note = data.get('note', '') # Define user note (Messages left by user)
    ai_analysis = " " # Define AI analysis first, later only fill in the blank

    if user_note.strip():  # if user note is not leave blank, then...
        # Give Z'Ai Prompt
        prompt = f"""
        You are a Disaster Emergency Search and Rescue Commander.
        Received victim SOS data: Water Level 【{water_level}】, Environment 【{env_info}】.
        The victim sent a panicked distress message: "{user_note}"

        Please use highly professional, concise, and structured language to infer based on the above information. 
        You MUST strictly follow the format below (no extra text, no greetings):
        Key Intelligence: [Extracted within 20 words: casualties, number of people, or specific dangers]
        Core Resources: [Comma-separated, e.g.: Medical Team, Speedboat]
        Support Supplies: [Comma-separated, e.g.: First Aid Kit, Insulated Gloves]
"""
        try:
            response = client.models.generate_content(
                model='nemo-super', 
                contents=prompt
            )
            ai_analysis = response.text.strip() # Response from AI
            print(f"\n✅ AI analyse successfully：{ai_analysis[:50]}...\n")  

        except Exception as e:
            traceback.print_exc()  # Backup Plan (if ai can't response)
            ai_analysis = "AI analysis network delay, please view original message: " + user_note
            print("\n" + "="*40)
            print(f"❌ AI Error Type: {type(e).__name__}")  
            print(f"❌ Error Detail: {e}")
            print("="*40 + "\n")

    # Generate Random Malaysia Phone No. 
    prefix = random.choice(['012', '017', '016', '011', '019', '018'])
    suffix = f"{random.randint(1000000, 9999999)}"
    mock_phone = f"{prefix}-{suffix}"

    # Generate Random GPS location 
    lat = round(3.14 + random.uniform(-0.02, 0.02), 4)
    lng = round(101.69 + random.uniform(-0.02, 0.02), 4)

    # Unified access to current time
    now = datetime.now()

    # Store data into database 
    new_sos = {
        "id": str(uuid.uuid4())[:8], # Generate a unique identifier
        "water": water_level,
        "env": env_info,
        "needs": data.get('needs', ''),
        "note": user_note, # Store the processed message / remark
        "ai_analysis": ai_analysis, # Store the result from AI
        "battery": data.get('battery', 'Unknown'),
        "priority": priority, # Setting the urgency level
        "status": "Pending", #Initial task status
        "timestamp": now.timestamp(), # Computer time
        "time_str": now.strftime("%H:%M:%S"), # Human time
        "gps": f"Longitude {lng}, Latitude {lat}",  # GPS text for UI
        "gps_lat": lat, # Numerics for Map
        "gps_lng": lng, # Numerics for Map
        "contact": f"{mock_phone}" # Phone no. 
    }
    
    # --- CRITICAL FIX: Upload to Firebase ---
    try:
        db.collection("rescue_missions").document(new_sos["id"]).set(new_sos)
        st.session_state.sos_database.append(new_sos) # Also keep in local session
        return True
    except Exception as e:
        st.error(f"Database Error: {e}")
        return False


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
position = st.selectbox("Where are you located?",
[
    "Ground Level", 
    "On the Rooftop", 
    "Hanging on a Tree", 
    "Inside Building (Upper Floor)",
    "Floating with a Log/Debris"
])
 
# Safety Gear & Hazards
hazards = st.multiselect("Identify Immediate Dangers:", 
                        ["Falling Trees", "Downed Power Lines", "Fast Current", "Tall Building Nearby (Safe)"])

# User Note for AI Analysis
st.subheader("4. Additional Remarks for AI")
user_note_input = st.text_area("Tell AI about your situation (e.g., 'Injured', 'Trapped'):", placeholder="I am trapped on the second floor with a baby...")

is_wearing_jacket = st.toggle("🦺 I am wearing a life jacket")
 
# --- 5. PHASE 3: SUBMIT / SOS ---
st.divider()
 
if st.button("🔥 SEND STANDARDIZED SOS SIGNAL", type="primary"):
    if water_level is None:
       st.warning("Please select a water level before sending.")
    else:
        with st.spinner("Encrypting & Broadcasting via Mesh Network..."):
           # Prepare data for Backend function
           sos_payload = {
               "water": water_level,
               "env": position,
               "note": user_note_input,
               "needs": ", ".join(vulnerable) if vulnerable else "None",
               "battery": f"{sim_battery}%"
           }
           
           # Call Backend Logic
           success = process_sos_logic(sos_payload)
           
           if success:
               time.sleep(1) # Visual delay for realism
               st.success("✅ SOS Transmitted!")
               st.balloons()
               st.info(f"Summary Sent: {water_level} | {people_count} | Position: {position}")
               if user_note_input and st.session_state.sos_database:
                   st.subheader("🤖 AI Commander Analysis:")
                   st.write(st.session_state.sos_database[-1]['ai_analysis'])
 
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