import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import streamlit.components.v1 as components
import time
from datetime import datetime, timezone
import uuid
import random
import requests
import traceback
import threading

# --- 0. PRE-FLIGHT & SESSION STATE (Idempotency & Cache) ---
if 'device_id' not in st.session_state:
    st.session_state.device_id = str(uuid.uuid4()) # Prevents duplicate spam from panic clicks

if 'active_sos_id' not in st.session_state:
    st.session_state.active_sos_id = None

if 'sos_database' not in st.session_state:
    st.session_state.sos_database = []

def generate_nato_id():
    """Generates a radio-friendly ID (e.g., Alpha-73)"""
    nato = ["📡 Alpha", "📡 Bravo", "📡 Charlie", "📡 Delta", "📡 Echo", "📡 Foxtrot", "📡 Golf", "📡 Hotel"]
    return f"{random.choice(nato)}-{random.randint(10, 99)}"

# --- BACKEND LOGIC (Z'Ai COMMANDER) ---

# --- 0. FIREBASE & AI CLIENT SETUP ---
if not firebase_admin._apps:
    try:
        creds_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        pass # Handle gracefully if secrets are missing in demo

try:
    db = firestore.client(database_id="shakehand")
except Exception:
    db = None

def process_sos_logic(data, rapid_mode=False, is_bm=False, is_cn=False):
    """
    This is your core Backend processing logic.
    """
    # Dynamic trend and medical triage logic
    priority = "P3"
    water_level = data.get('water', '')
    water_trend = data.get('trend', '')
    medical = data.get('medical', [])
    user_note = data.get('note', '') # Fetch user note
    headcount = data.get('headcount', 1) # Fetch headcount, default to 1
    
    if "Chest" in water_level or "Rising Fast" in water_trend or "Severe Bleeding" in medical or "Hypothermia" in medical:
        priority = "P0" # Immediate life threat
    elif "Hips" in water_level or "Trapped" in data.get('tags', []):
        priority = "P1"
    elif "Knees" in water_level:
        priority = "P2"

    # Generate Radio-Friendly ID
    mission_id = generate_nato_id()
    
    # Generate Random Malaysia Phone No. 
    prefix = random.choice(['012', '017', '016', '011', '019', '018'])
    suffix = f"{random.randint(1000000, 9999999)}"
    mock_phone = f"{prefix}-{suffix}"

    # Generate Random GPS location 
    lat = round(3.14 + random.uniform(-0.02, 0.02), 4)
    lng = round(101.69 + random.uniform(-0.02, 0.02), 4)

    # Unified access to current time
    now = datetime.now(timezone.utc)
    
    # Base Payload (Saved IMMEDIATELY before AI to prevent blocking)
    new_sos = {
        "mission_id": mission_id,
        "device_id": st.session_state.device_id, # Idempotency key
        "role": data.get('role', 'Victim'),
        "headcount": headcount, # Save headcount to database
        "water": water_level,
        "trend": water_trend,
        "needs": data.get('needs', ''),
        "medical": ", ".join(medical),
        "tags": ", ".join(data.get('tags', [])),
        "note": user_note, # Save the typed message to database
        "jacket": data.get('jacket', 'Unknown'),
        "battery": data.get('battery', 'Unknown'),
        "priority": priority, 
        "status": "Pending Rescue", 
        "client_timestamp": data.get('client_time', now.timestamp()), 
        "server_timestamp": now.timestamp(), 
        "gps_accuracy": data.get('accuracy', '~15m Radius'),
        "gps_lat": lat, 
        "gps_lng": lng, 
        "contact": f"{mock_phone}",
        "ai_analysis": "⏳ Pending async analysis..." # Placeholder
    }
    
    # --- CRITICAL FIX: Upload to Firebase IMMEDIATELY (No AI blocking) ---
    upload_success = False
    try:
        if db:
            db.collection("rescue_missions").document(st.session_state.device_id).set(new_sos)
        upload_success = True
        st.session_state.active_sos_id = st.session_state.device_id
        st.session_state.sos_database.append(new_sos) 
    except Exception as e:
        err_msg = "❌ Network Failed. Connection lost."
        if is_bm: err_msg = "❌ Rangkaian Gagal. Sambungan terputus."
        elif is_cn: err_msg = "❌ 网络连接失败，已断开连接。"
        st.error(err_msg)
        
        sms_body = f"SOS! ID:{mission_id} P:{priority} GPS:{lat},{lng} Needs Help!"
        
        sms_btn = "💬 Tap to Send SMS (No Internet Needed)"
        if is_bm: sms_btn = "💬 Tekan untuk Hantar SMS (Tanpa Internet)"
        elif is_cn: sms_btn = "💬 点击发送短信 (无需网络)"
        
        st.markdown(f"""
        <a href="sms:999?body={sms_body}" style="background-color:#FF0000; color:white; padding:15px; border-radius:10px; text-decoration:none; display:block; text-align:center; font-weight:bold; font-size:20px;">
        {sms_btn}
        </a>
        """, unsafe_allow_html=True)
        return False

    # --- TRUE ASYNC AI BACKGROUND WORKER ---
    # Decoupled from UI flow to prevent freezing victim's device
    def run_ai_background(doc_id, profile, hc, wl, wt, med, tags, note, api_key):
        prompt = f"""
        You are a Disaster Rescue Commander. 
        Victim Profile: {profile}, Headcount: {hc}, Water: {wl} ({wt}), Medical: {med}, Hazards: {tags}
        Victim Note: "{note}"

        CRITICAL INSTRUCTION: Provide an EXTREMELY CONCISE analysis. Maximum 15 words per section. NO markdown formatting, NO bolding, NO bullet points. Keep it strictly plain text and short.
        If the "Victim Note" contains gibberish or random letters, ignore it entirely.

        Key Intel: [Max 15 words] next line
        Resources: [Max 15 words] next line 
        Supplies: [Max 15 words]
        """
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "ilmu-glm-5.1", 
                "messages": [{"role": "user", "content": prompt}]
            }
            
            response = requests.post(
                "https://api.ilmu.ai/v1/chat/completions", 
                headers=headers, 
                json=payload,
                timeout=50
            )
            
            ai_disclaimer = "[🤖 AI]\n"
            if response.status_code == 200:
                result = response.json()
                analysis_text = result["choices"][0]["message"]["content"].strip()
                final_ai_text = ai_disclaimer + analysis_text
                
                try:
                    thread_db = firestore.client(database_id="shakehand")
                    thread_db.collection("rescue_missions").document(doc_id).update({"ai_analysis": final_ai_text})
                except Exception:
                    pass
        except Exception:
            pass # Fail gracefully in background

    # Trigger thread if we have an API key configured securely
    if upload_success and not rapid_mode:
        my_api_key = ""
        try:
            my_api_key = st.secrets.get("GEMINI_KEY", "")
        except Exception:
            pass
            
        if my_api_key:
            threading.Thread(target=run_ai_background, args=(
                st.session_state.device_id, 
                new_sos['role'], new_sos['headcount'], water_level, water_trend, 
                new_sos['medical'], new_sos['tags'], user_note, my_api_key
            )).start()

    return True

# --- 1. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="Z.AI - Emergency", page_icon="🆘", layout="centered")

# Custom CSS for fixing the empty space and sticky header
st.markdown("""
    <style>
    /* Absolute top sticky header to remove empty space */
    .sticky-header {
        position: fixed;
        top: 60px; /* Offset for Streamlit native header */
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 730px; /* Aligns with Streamlit center layout */
        background-color: #001f3f;
        color: #FFFFFF;
        padding: 15px;
        border-radius: 0 0 15px 15px;
        z-index: 99999;
        text-align: center;
        font-weight: bold;
        box-shadow: 0px 4px 10px rgba(0,0,0,0.5);
    }
    /* Push content down so it doesn't hide behind the fixed header */
    .block-container {
        padding-top: 120px !important; /* Push down to avoid overlap */
    }
    .stButton>button {
        width: 100%;
        height: 70px;
        font-size: 20px;
        font-weight: bold;
        border-radius: 12px;
        border: 2px solid #FFFFFF;
    }
    .btn-rapid { background-color: #D90429 !important; color: white !important; }
    .stRadio > label { font-size: 18px !important; font-weight: bold; }
    .stCheckbox > label { font-size: 18px !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)


# --- 1.5 LANGUAGE SELECTION (Moved to Top Right) ---
col_spacer, col_lang = st.columns([2, 1])
with col_lang:
    ui_lang = st.selectbox("🌐 Language / Bahasa", ["🇬🇧 English", "🇲🇾 Bahasa Melayu", "🇨🇳 中文"])

is_bm = "Bahasa Melayu" in ui_lang
is_cn = "中文" in ui_lang

# Helper function to swap languages cleanly
def _T(en, bm, cn):
    if is_cn: return cn
    if is_bm: return bm
    return en

# --- 2. SIDEBAR DEMO CONTROLS ---
with st.sidebar:
    st.header(_T("⚙️ Simulator Panel", "⚙️ Panel Simulator", "⚙️ 模拟器面板"))
    sim_battery = st.slider(_T("🔋 Device Battery", "🔋 Bateri Peranti", "🔋 设备电量"), 0, 100, 15)
    sim_accuracy = st.slider(_T("📍 GPS Error Radius (m)", "📍 Ralat Radius GPS (m)", "📍 GPS 误差半径 (米)"), 5, 2000, 15)
    
    st.caption(_T("💻 v2.0 - Resilient Protocol", "💻 v2.0 - Protokol Berdaya Tahan", "💻 v2.0 - 弹性协议"))

# --- STICKY HEADER (Life-line info at the top) ---
battery_display = f"🔋 {sim_battery}%"
if sim_battery <= 20:
    battery_display = _T(f"⚠️ [!] BATTERY LOW: {sim_battery}%", f"⚠️ [!] BATERI LEMAH: {sim_battery}%", f"⚠️ [!] 电量不足: {sim_battery}%")

accuracy_display = f"~{sim_accuracy}m"
if sim_accuracy > 100:
    accuracy_display = _T("⚠️ POOR (Update Landmark)", "⚠️ LEMAH (Kemas Kini Mercu Tanda)", "⚠️ 弱 (请更新地标)")

gps_lock_text = _T("📍 GPS Lock:", "📍 Kunci GPS:", "📍 GPS 定位:")
st.markdown(f"""
    <div class="sticky-header">
        {battery_display} &nbsp; | &nbsp; {gps_lock_text} {accuracy_display}
    </div>
""", unsafe_allow_html=True)


# --- 3. RAPID SOS (Bypass everything) ---
btn_rapid_text = _T("🚨 1-TAP RAPID SOS (SEND LOCATION NOW)", "🚨 SOS PANTAS 1-TEKAN (HANTAR LOKASI SEKARANG)", "🚨 一键紧急 SOS (立即发送位置)")
if st.button(btn_rapid_text, type="primary"):
    spinner_text = _T("📡 Transmitting Data...", "📡 Menghantar Data...", "📡 正在传输数据...")
    with st.spinner(spinner_text):
        rapid_payload = {
            "role": "👤 Victim",
            "headcount": 1, # Default rapid headcount to 1
            "water": "❓ Unknown",
            "trend": "❓ Unknown",
            "battery": f"{sim_battery}%",
            "accuracy": accuracy_display,
            "client_time": datetime.now(timezone.utc).timestamp()
        }
        if process_sos_logic(rapid_payload, rapid_mode=True, is_bm=is_bm, is_cn=is_cn):
            succ_msg = _T("✅ LOCATION SENT! Rescuers are notified. Stay calm.", "✅ LOKASI DIHANTAR! Penyelamat telah dimaklumkan. Bertenang.", "✅ 位置已发送！救援人员已收到通知。请保持冷静。")
            st.success(succ_msg)

st.divider()

# Only show checklist if battery is safe
if sim_battery > 20:
    checklist_title = _T("📋 Pre-evacuation Checklist", "📋 Senarai Semak Pra-Pemindahan", "📋 撤离前准备清单")
    checklist_text = _T("🪪 Grab IDs\n💊 Medications\n🔋 Powerbank\n💧 Water", "🪪 Ambil Kad Pengenalan\n💊 Ubat-ubatan\n🔋 Powerbank\n💧 Air", "🪪 带上身份证件\n💊 必需药品\n🔋 充电宝\n💧 饮用水")
    with st.expander(checklist_title):
        st.write(checklist_text)

# --- 4. PHASE 2: DETAILED FORM OR ACTIVE SOS VIEW ---
if st.session_state.active_sos_id:
    # SUCCESS PAGE - HOLD POSITION
    st.success(_T("✅ SOS TRANSMITTED SUCCESSFULLY!", "✅ SOS BERJAYA DIHANTAR!", "✅ SOS 成功发送！"))
    
    st.markdown(f"### {_T('🛑 HOLD YOUR POSITION', '🛑 KEKAL DI TEMPAT ANDA', '🛑 请留在原地')}")
    st.write(_T(
        "Rescue teams have received your coordinates. Please stay put if it is safe to do so. Conserve your battery.", 
        "Pasukan penyelamat telah menerima koordinat anda. Sila kekal di tempat anda jika selamat. Jimatkan bateri anda.", 
        "救援队伍已收到您的坐标。在安全的情况下请留在原地。请节约设备电量。"
    ))
    
    st.divider()
    
    # INTEGRATED SURVIVAL TOOLS
    st.subheader(_T("🛠️ Survival Tools", "🛠️ Alat Kendiri", "🛠️ 求生工具"))
    col_tool1, col_tool2 = st.columns(2)

    with col_tool1:
        btn_flash = _T("🔦 Visual Flash", "🔦 Denyar Visual", "🔦 屏幕闪光")
        if st.button(btn_flash):
            toast_f = _T("🔦 Flasher activated on screen!", "🔦 Denyar skrin diaktifkan!", "🔦 屏幕闪光已激活！")
            st.toast(toast_f)
            # CSS Injection for native screen flashing
            st.markdown("""
            <style>
            @keyframes flashEffect {
                0% { background-color: #FFFFFF; }
                50% { background-color: #000000; }
                100% { background-color: #FFFFFF; }
            }
            .stApp {
                animation: flashEffect 0.2s 20; /* Flashes quickly 20 times */
            }
            </style>
            """, unsafe_allow_html=True)

    with col_tool2:
        btn_siren = _T("🔊 Audio Siren", "🔊 Siren Audio", "🔊 警报器声音")
        if st.button(btn_siren):
            toast_s = _T("🔊 Siren playing!", "🔊 Siren dimainkan!", "🔊 警报器正在播放！")
            st.toast(toast_s)
            # Direct Audio Context Trigger
            components.html("""
            <script>
                let ctx = new (window.AudioContext || window.webkitAudioContext)();
                let osc = ctx.createOscillator();
                let gainNode = ctx.createGain();
                osc.type = 'square';
                osc.frequency.setValueAtTime(880, ctx.currentTime);
                osc.frequency.setValueAtTime(1100, ctx.currentTime + 0.5);
                osc.frequency.setValueAtTime(880, ctx.currentTime + 1.0);
                osc.connect(gainNode);
                gainNode.connect(ctx.destination);
                osc.start();
                osc.stop(ctx.currentTime + 2.0);
            </script>
            """, height=0)

    st.divider()

    # STATUS UPDATE CONTROLS
    st.subheader(_T("🔄 Status Update", "🔄 Kemas Kini Status", "🔄 状态更新"))
    st.write(_T(
        "If your current location becomes unsafe, do NOT send a new SOS. Inform the control room below:", 
        "Jika lokasi semasa anda tidak selamat, JANGAN hantar SOS baru. Maklumkan bilik kawalan di bawah:", 
        "如果当前位置变得不安全，请勿发送新的 SOS。请在下方通知控制室："
    ))

    colA, colB = st.columns(2)
    
    btn_cancel = _T("🛡️ I AM SAFE (CANCEL SOS)", "🛡️ SAYA SELAMAT (BATALKAN SOS)", "🛡️ 我已安全 (取消 SOS)")
    if colA.button(btn_cancel):
        if db:
            db.collection("rescue_missions").document(st.session_state.active_sos_id).update({"status": "Resolved - Safe"})
        st.session_state.active_sos_id = None
        cancel_success = _T("✅ SOS Cancelled. Stay safe.", "✅ SOS Dibatalkan. Kekal selamat.", "✅ SOS 已取消。注意安全。")
        st.success(cancel_success)
        st.rerun()
        
    btn_unsafe = _T("🚨 LOCATION UNSAFE", "🚨 LOKASI TIDAK SELAMAT", "🚨 位置不安全")
    if colB.button(btn_unsafe, type="primary"):
        # Update existing document instead of creating a new one
        if db:
            db.collection("rescue_missions").document(st.session_state.active_sos_id).update({
                "priority": "P0",
                "trend": "Rising Fast",
                "note": "URGENT UPDATE: Victim reported current location is no longer safe!"
            })
        st.warning(_T("⚠️ Control room updated! Priority escalated.", "⚠️ Bilik kawalan dikemas kini! Keutamaan ditingkatkan.", "⚠️ 已通知控制室！优先级已提升。"))

else:
    # DATA COLLECTION FORM
    form_header = _T("📝 Provide Details (If Safe to do so)", "📝 Berikan Butiran (Jika Selamat)", "📝 提供详细信息 (在安全的情况下)")
    st.header(form_header)
    
    with st.form("sos_form"):
        q_role = _T("🙋‍♂️ Who needs help?", "🙋‍♂️ Siapa yang perlukan bantuan?", "🙋‍♂️ 谁需要帮助？")
        opt_role_en = ["👤 I am the victim", "👁️ I am reporting for someone else"]
        opt_role_bm = ["👤 Saya mangsa", "👁️ Saya melapor untuk orang lain"]
        opt_role_cn = ["👤 我是受害者", "👁️ 我代他人报告"]
        
        current_opt_role = _T(opt_role_en, opt_role_bm, opt_role_cn)
        role_ui = st.radio(q_role, current_opt_role, index=0)
        
        st.subheader(_T("⚕️ 1. Medical Emergencies", "⚕️ 1. Kecemasan Perubatan", "⚕️ 1. 医疗紧急情况"))
        col_m1, col_m2 = st.columns(2)
        med_1 = col_m1.checkbox(_T("🩸 Severe Bleeding", "🩸 Pendarahan Teruk", "🩸 严重出血"))
        med_2 = col_m1.checkbox(_T("🥶 Hypothermia (Shivering)", "🥶 Hipotermia (Menggigil)", "🥶 失温 (发抖)"))
        med_3 = col_m2.checkbox(_T("🫁 Need Oxygen/Insulin", "🫁 Perlu Oksigen/Insulin", "🫁 需要氧气/胰岛素"))
        med_4 = col_m2.checkbox(_T("😵 Unconscious", "😵 Tidak Sedarkan Diri", "😵 失去意识"))
        
        # Keep tags in English for the backend AI
        medical_tags = []
        if med_1: medical_tags.append("Severe Bleeding")
        if med_2: medical_tags.append("Hypothermia")
        if med_3: medical_tags.append("Need Oxygen/Insulin")
        if med_4: medical_tags.append("Unconscious")

        st.subheader(_T("🌊 2. Water Situation", "🌊 2. Keadaan Air", "🌊 2. 水位情况"))
        col1, col2 = st.columns(2)
        with col1:
            water_depth_label = _T("📏 Depth:", "📏 Kedalaman:", "📏 深度:")
            opts_depth_en = ["🦵 Above Knees", "🩳 Above Hips", "🫁 Around Chest"]
            opts_depth_bm = ["🦵 Atas Lutut", "🩳 Atas Pinggang", "🫁 Paras Dada"]
            opts_depth_cn = ["🦵 没过膝盖", "🩳 没过臀部", "🫁 到达胸部"]
            current_opts_depth = _T(opts_depth_en, opts_depth_bm, opts_depth_cn)
            
            water_level_ui = st.radio(water_depth_label, current_opts_depth, index=None)
            
            # Map back to English for Backend
            water_level = None
            if water_level_ui:
                idx = current_opts_depth.index(water_level_ui)
                water_level = opts_depth_en[idx]

        with col2:
            water_trend_label = _T("📈 Flow:", "📈 Aliran:", "📈 水流:")
            opts_trend_en = ["🌊 Rising Fast", "📉 Stable / Dropping"]
            opts_trend_bm = ["🌊 Naik Cepat", "📉 Stabil / Menurun"]
            opts_trend_cn = ["🌊 快速上涨", "📉 稳定 / 下降"]
            current_opts_trend = _T(opts_trend_en, opts_trend_bm, opts_trend_cn)
            
            water_trend_ui = st.radio(water_trend_label, current_opts_trend, index=None)

            # Map back to English for Backend
            water_trend = None
            if water_trend_ui:
                idx = current_opts_trend.index(water_trend_ui)
                water_trend = opts_trend_en[idx]

        st.subheader(_T("⚠️ 3. Environment Hazards", "⚠️ 3. Bahaya Persekitaran", "⚠️ 3. 环境危险"))
        col_h1, col_h2 = st.columns(2)
        haz_1 = col_h1.checkbox(_T("🚪 Trapped inside", "🚪 Terperangkap di dalam", "🚪 被困室内"))
        haz_2 = col_h1.checkbox(_T("🌳 Hanging on tree/roof", "🌳 Bergantung pada pokok/bumbung", "🌳 挂在树上/屋顶"))
        haz_3 = col_h2.checkbox(_T("🌪️ Fast current", "🌪️ Arus deras", "🌪️ 急流"))
        haz_4 = col_h2.checkbox(_T("⚡ Live wires", "⚡ Wayar elektrik hidup", "⚡ 漏电/裸露电线"))
        
        env_tags = []
        if haz_1: env_tags.append("Trapped inside")
        if haz_2: env_tags.append("Hanging on tree/roof")
        if haz_3: env_tags.append("Fast current")
        if haz_4: env_tags.append("Live wires")

        st.subheader(_T("👨‍👩‍👧‍👦 4. Group Status", "👨‍👩‍👧‍👦 4. Status Kumpulan", "👨‍👩‍👧‍👦 4. 团队状况"))
        hc_label = _T("🔢 Total Number of People (Including yourself)", "🔢 Jumlah Orang (Termasuk diri anda)", "🔢 总人数 (包括您自己)")
        headcount = st.number_input(hc_label, min_value=1, max_value=100, value=1, step=1)
        
        col_v1, col_v2 = st.columns(2)
        vul_1 = col_v1.checkbox(_T("👶 Children", "👶 Kanak-kanak", "👶 儿童"))
        vul_2 = col_v1.checkbox(_T("🧓 Elderly", "🧓 Warga Emas", "🧓 老人"))
        vul_3 = col_v1.checkbox(_T("♿ Disabled", "♿ OKU", "♿ 残疾人士"))
        vul_4 = col_v2.checkbox(_T("📦 Pets (In Cage)", "📦 Haiwan Peliharaan (Dalam Sangkar)", "📦 宠物 (在笼中)"))
        vul_5 = col_v2.checkbox(_T("🐕 Pets (No Cage)", "🐕 Haiwan Peliharaan (Tiada Sangkar)", "🐕 宠物 (无笼)"))
        
        vulnerable = []
        if vul_1: vulnerable.append("Children")
        if vul_2: vulnerable.append("Elderly")
        if vul_3: vulnerable.append("Disabled")
        if vul_4: vulnerable.append("Pets (In Cage)")
        if vul_5: vulnerable.append("Pets (No Cage)")
        
        # User Manual Text Area
        st.subheader(_T("💬 5. Additional Remarks", "💬 5. Catatan Tambahan", "💬 5. 补充备注"))
        note_label = _T("Type any specific requests or conditions:", "Taip sebarang permintaan atau keadaan khusus:", "输入任何具体请求或情况:")
        note_place = _T("E.g., Need baby formula, stranded on red roof...", "Cth., Perlu susu bayi, terkandas di bumbung merah...", "例如：需要婴儿配方奶粉，被困在红色屋顶上...")
        user_note_input = st.text_area(note_label, placeholder=note_place)

        jacket_label = _T("🦺 Safety Gear:", "🦺 Peralatan Keselamatan:", "🦺 安全装备:")
        jacket_opts_en = ["❌ No Life Jacket", "✅ Wearing Life Jacket"]
        jacket_opts_bm = ["❌ Tiada Jaket Keselamatan", "✅ Memakai Jaket Keselamatan"]
        jacket_opts_cn = ["❌ 没有救生衣", "✅ 穿着救生衣"]
        current_jacket_opts = _T(jacket_opts_en, jacket_opts_bm, jacket_opts_cn)
        
        jacket_ui = st.radio(jacket_label, current_jacket_opts, index=0)
        
        # Map back to English for Backend
        jacket = jacket_opts_en[current_jacket_opts.index(jacket_ui)]

        confirm_label = _T("☑️ Confirm information is accurate", "☑️ Sahkan maklumat adalah tepat", "☑️ 确认信息准确无误")
        confirm = st.checkbox(confirm_label)
        
        btn_submit = _T("🚀 SEND DETAILED SOS", "🚀 HANTAR SOS TERPERINCI", "🚀 发送详细 SOS")
        submitted = st.form_submit_button(btn_submit, type="primary")
        
        if submitted:
            if not confirm:
                warn_1 = _T("⚠️ Please check 'Confirm information' before sending.", "⚠️ Sila semak 'Sahkan maklumat' sebelum menghantar.", "⚠️ 请在发送前勾选“确认信息准确无误”。")
                st.warning(warn_1)
            elif water_level is None:
                warn_2 = _T("⚠️ Please select a water depth.", "⚠️ Sila pilih kedalaman air.", "⚠️ 请选择水深。")
                st.warning(warn_2)
            else:
                info_tx = _T("📡 Transmitting Data...", "📡 Menghantar Data...", "📡 正在传输数据...")
                st.info(info_tx)
                
                # Map role back to English for payload consistency
                role_en_full = opt_role_en[current_opt_role.index(role_ui)]

                sos_payload = {
                    "role": role_en_full,
                    "headcount": headcount, # Passed to backend
                    "water": water_level,
                    "trend": water_trend,
                    "medical": medical_tags,
                    "tags": env_tags,
                    "note": user_note_input, # Passed to backend
                    "needs": ", ".join(vulnerable) if vulnerable else "None",
                    "jacket": jacket,
                    "battery": f"{sim_battery}%",
                    "accuracy": accuracy_display,
                    "client_time": datetime.now(timezone.utc).timestamp()
                }
                
                success = process_sos_logic(sos_payload, is_bm=is_bm, is_cn=is_cn)
                if success:
                    succ_msg2 = _T("✅ DETAILED SOS SENT. AI Commander has updated the Rescue Team.", "✅ SOS TERPERINCI DIHANTAR. Komander AI telah memaklumkan Pasukan Penyelamat.", "✅ 详细 SOS 已发送。AI 指挥官已更新救援团队。")
                    st.success(succ_msg2)