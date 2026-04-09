import streamlit as st
import pyodbc
import base64
import os
import jwt  # Thư viện mã hóa
from datetime import datetime, timedelta, timezone
from config import CONN_STR

# Khóa bí mật (Bắt buộc phải giống hệt khóa trong main.py)
SECRET_KEY = "umbrella_logistics_super_secret_key_2026"

# --- HÀM HỖ TRỢ ĐỌC ẢNH SANG BASE64 ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception: return ""

# --- BACKEND DATABASE ---
def init_db():
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='userstable' and xtype='U')
            CREATE TABLE userstable (
                username VARCHAR(50) PRIMARY KEY, 
                password VARCHAR(255), 
                role INT,
                is_locked INT DEFAULT 0
            )
        ''')
        cursor.execute('SELECT COUNT(*) FROM userstable')
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO userstable (username, password, role, is_locked) VALUES ('admin', '123', 1, 0)")
            cursor.execute("INSERT INTO userstable (username, password, role, is_locked) VALUES ('taixe', '123', 2, 0)")
            conn.commit() 
        conn.close()
    except Exception as e: st.error(f"Lỗi DB: {e}")

def login_user(username, password):
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute('SELECT role, ISNULL(is_locked, 0) FROM userstable WHERE username = ? AND password = ?', (username, password))
        data = cursor.fetchone()
        conn.close()
        if data:
            if data[1] == 1: return "LOCKED"
            return data[0]
        return None
    except: return None

def add_user(new_user, new_pass, role_num):
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO userstable (username, password, role, is_locked) VALUES (?, ?, ?, 0)", (new_user, new_pass, role_num))
        conn.commit() 
        conn.close()
        return True
    except: return False

# ==========================================
# HÀM RENDER ĐƯỢC GỌI TỪ MAIN.PY
# ==========================================
def render_page():
    init_db()
    
    if "role" not in st.session_state: st.session_state.role = None
    if "customer" not in st.session_state: st.session_state.customer = None

    # --- ĐỌC ẢNH LOGO VÀ BACKGROUND ---
    bg_img_b64 = get_base64_of_bin_file(os.path.join("img", "E2449DA3-F2EB-430A-A588-2F9E9C6C2961.png"))
    logo_head_b64 = get_base64_of_bin_file(os.path.join("img", "19180C31-3EB3-48C4-92C8-7CD1BC52F90C (1).png"))

    # ==========================================
    # CSS SIÊU CẤP ĐỘ LẠI STREAMLIT UI
    # ==========================================
    st.markdown(f"""
        <style>
        /* Nền tổng thể */
        .stApp {{ background-color: #07080A; }}
        
        /* Hiệu ứng Watermark nền mờ rảo */
        .bg-watermark {{
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            width: 850px; height: 850px;
            background-image: url('data:image/png;base64,{bg_img_b64}');
            background-size: contain; background-position: center; background-repeat: no-repeat;
            opacity: 0.08; z-index: 0; pointer-events: none;
            filter: grayscale(100%);
        }}

        /* HOẠT ẢNH: Trượt lên và Nổi */
        @keyframes slideUpFade {{
            from {{ opacity: 0; transform: translateY(40px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes float {{
            0% {{ transform: translateY(0px); }}
            50% {{ transform: translateY(-8px); filter: drop-shadow(0 10px 15px rgba(255, 75, 75, 0.4)); }}
            100% {{ transform: translateY(0px); }}
        }}
        
        /* ĐỘ LẠI CONTAINER THÀNH CARD KÍNH (GLASSMORPHISM) */
        div[data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stContainer"] {{
            background: rgba(18, 20, 28, 0.65) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.07) !important;
            border-top: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 24px !important;
            padding: 40px 30px !important;
            box-shadow: 0 30px 60px -12px rgba(0,0,0,0.8) !important;
            z-index: 2;
            position: relative;
            animation: slideUpFade 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }}
        
        /* Header Logo Đẹp Mắt */
        .premium-header {{ text-align: center; margin-bottom: 35px; }}
        .premium-header img {{
            width: 95px;
            margin-bottom: 20px;
            animation: float 4s ease-in-out infinite;
        }}
        .premium-header h1 {{
            color: #FFFFFF; font-weight: 900; font-size: 28px; margin: 0;
            letter-spacing: 2px;
            background: linear-gradient(90deg, #FFFFFF, #A0AEC0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .premium-header p {{ color: #718096; font-size: 14px; margin-top: 8px; letter-spacing: 0.5px; font-weight: 500; }}

        /* ĐỘ TABS THÀNH PILLS (VIÊN THUỐC) */
        [data-testid="stTabs"] [role="tablist"] {{
            gap: 12px; border-bottom: none; justify-content: center; margin-bottom: 30px;
        }}
        [data-testid="stTabs"] button[role="tab"] {{
            background-color: #1A1C24 !important;
            border: 1px solid #2D3748 !important;
            border-radius: 30px !important;
            padding: 10px 30px !important;
            color: #718096 !important;
            font-weight: 700 !important;
            font-size: 15px !important;
            transition: all 0.3s ease;
        }}
        [data-testid="stTabs"] button[role="tab"]:hover {{ background-color: #2D3748 !important; color: white !important; }}
        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
            background: rgba(255, 75, 75, 0.15) !important;
            border: 1px solid #FF4B4B !important;
            color: #FF4B4B !important;
            box-shadow: 0 0 15px rgba(255, 75, 75, 0.2) !important;
        }}
        
        /* Tùy chỉnh Tiêu đề Ô nhập liệu (Label) */
        .stTextInput label, .stSelectbox label {{
            font-size: 13px !important; color: #A0AEC0 !important;
            font-weight: 600 !important; letter-spacing: 0.5px !important;
            margin-bottom: 4px !important;
        }}

        /* Tùy chỉnh Ô nhập liệu (Input & Select) */
        div[data-baseweb="input"], div[data-baseweb="select"] > div {{ 
            background-color: #0D0E12 !important; 
            border: 1px solid #2D3748 !important; 
            border-radius: 12px !important; 
            transition: all 0.3s ease !important;
        }}
        input {{ color: white !important; padding: 16px 15px !important; font-size: 15px !important; }}
        div[data-baseweb="input"]:focus-within, div[data-baseweb="select"] > div:focus-within {{ 
            border-color: #FF4B4B !important; 
            box-shadow: 0 0 0 1px #FF4B4B !important;
            background-color: #12141A !important;
        }}
        
        /* Nút Bấm Phát Sáng */
        button[kind="primary"] {{ 
            background: linear-gradient(135deg, #FF4B4B 0%, #E53E3E 100%) !important;
            border: none !important; width: 100%; 
            border-radius: 12px !important; padding: 14px !important; 
            font-weight: 800 !important; font-size: 16px !important;
            letter-spacing: 1px !important; color: white !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 8px 25px rgba(229, 62, 62, 0.3) !important;
            margin-top: 10px !important;
        }}
        button[kind="primary"]:hover {{
            transform: translateY(-3px) !important;
            box-shadow: 0 12px 30px rgba(229, 62, 62, 0.5) !important;
            filter: brightness(1.1) !important;
        }}

        /* ẨN VIỀN FORM MẶC ĐỊNH ĐỂ KHÔNG PHÁ VỠ UI KÍNH MỜ */
        div[data-testid="stForm"] {{
            border: none !important;
            padding: 0 !important;
            background: transparent !important;
        }}
        </style>
        <div class="bg-watermark"></div>
        """, unsafe_allow_html=True)

    # --- KHUNG RỖNG ĐỂ XÓA GIAO DIỆN TRƯỚC KHI CHUYỂN TRANG (Khắc phục Bóng ma) ---
    login_placeholder = st.empty()

    with login_placeholder.container():
        # Đẩy nhẹ form xuống giữa không gian
        st.markdown("<div style='height: 4vh;'></div>", unsafe_allow_html=True) 
        
        col1, col2, col3 = st.columns([1, 1.2, 1])
        with col2:
            # Bản thân st.container này sẽ được tự động áp hiệu ứng Glassmorphism từ CSS
            with st.container(border=True):
                
                # Hero Header mượt mà
                st.markdown(f"""
                    <div class="premium-header">
                        <img src="data:image/png;base64,{logo_head_b64}" alt="Umbrella Logo">
                        <h1>UMBRELLA LOGISTICS</h1>
                        <p>Hệ thống Quản trị Chuỗi Cung ứng Vinh City</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Tab được độ thành nút Pill
                tab_login, tab_signup = st.tabs(["Đăng nhập", "Tạo tài khoản"])
                
                with tab_login:
                    # BỌC TRONG FORM ĐỂ KHÔNG BỊ LOAD LẠI KHI GÕ PHÍM
                    with st.form(key="login_form", border=False):
                        user = st.text_input("TÊN ĐĂNG NHẬP", placeholder="Nhập tài khoản hệ thống", key="l_user")
                        pwd = st.text_input("MẬT KHẨU", placeholder="••••••••", type="password", key="l_pwd")
                        
                        # Chuyển st.button thành st.form_submit_button
                        submit_login = st.form_submit_button("XÁC NHẬN ĐĂNG NHẬP", type="primary")
                        
                        if submit_login:
                            if not user or not pwd:
                                st.warning("Vui lòng điền đầy đủ thông tin!")
                            else:
                                with st.spinner("Đang xác thực hệ thống..."):
                                    result = login_user(user, pwd)
                                    if result == "LOCKED":
                                        st.error("Tài khoản của bạn đã bị khóa bởi Quản trị viên!")
                                    elif result is not None:
                                        # 1. Lưu vào RAM
                                        st.session_state.role = str(result)
                                        st.session_state.customer = user
                                        
                                        # 2. [MỚI] MÃ HÓA JWT VÀ GẮN LÊN URL TRÌNH DUYỆT
                                        payload = {
                                            "username": user,
                                            "role": str(result),
                                            "exp": datetime.now(timezone.utc) + timedelta(days=30) # Sống 30 ngày
                                        }
                                        # Dùng máy ép tạo Token
                                        encoded_token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
                                        # Ném lên URL
                                        st.query_params["token"] = encoded_token
                                        
                                        # XÓA SẠCH GIAO DIỆN CŨ TRƯỚC KHI RERUN (Diệt Bóng ma)
                                        login_placeholder.empty()
                                        st.rerun()
                                    else: 
                                        st.error("Thông tin đăng nhập không chính xác!")
                
                with tab_signup:
                    # BỌC TRONG FORM ĐỂ KHÔNG BỊ LOAD LẠI KHI GÕ PHÍM
                    with st.form(key="signup_form", border=False):
                        new_user = st.text_input("TÊN TÀI KHOẢN MỚI", placeholder="Ví dụ: taixe01", key="s_user")
                        new_pwd = st.text_input("TẠO MẬT KHẨU", placeholder="Sử dụng mật khẩu mạnh", type="password", key="s_pwd")
                        
                        role_map = {"Tài xế": 2, "Khách hàng": 3}
                        choice = st.selectbox("CHỌN VAI TRÒ VẬN HÀNH", list(role_map.keys()))
                        
                        # Chuyển st.button thành st.form_submit_button
                        submit_signup = st.form_submit_button("TIẾN HÀNH ĐĂNG KÝ", type="primary")
                        
                        if submit_signup:
                            if new_user and new_pwd:
                                with st.spinner("Đang khởi tạo định danh..."):
                                    if add_user(new_user, new_pwd, role_map[choice]): 
                                        st.success("Tạo tài khoản thành công! Hãy chuyển sang Tab Đăng nhập.")
                                    else: 
                                        st.error("Định danh này đã tồn tại. Vui lòng chọn tên khác!")
                            else: 
                                st.warning("Hệ thống yêu cầu điền đầy đủ thông tin.")