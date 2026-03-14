import streamlit as st
import pyodbc
import base64

# ==========================================
# 1. CẤU HÌNH TAB TRÌNH DUYỆT (BẮT BUỘC ĐỂ ĐẦU TIÊN)
# ==========================================
st.set_page_config(
    page_title="Đăng nhập - Umbrella Logistics", 
    page_icon=r"D:\datn\img\4D5185D2-0AD7-49AC-B7B2-4E94C13DB13C.png",
    layout="wide"
)

# ==========================================
# 2. CẤU HÌNH KẾT NỐI SQL SERVER
# ==========================================
SERVER_NAME = 'DESKTOP-U4FQD35' 
DATABASE_NAME = 'LogisticsDB'
CONN_STR = f"Driver={{SQL Server}};Server={SERVER_NAME};Database={DATABASE_NAME};Trusted_Connection=yes;"

# --- PHỤC HỒI TRÍ NHỚ TỪ URL KHI F5 (BỔ SUNG MỚI) ---
if "user" in st.query_params and "role" in st.query_params:
    st.session_state.username = st.query_params["user"]
    st.session_state.role = st.query_params["role"]

# --- HÀM HỖ TRỢ ĐỌC ẢNH SANG BASE64 ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception: return ""

bg_img_b64 = get_base64_of_bin_file(r"D:\datn\img\E2449DA3-F2EB-430A-A588-2F9E9C6C2961.png")

# --- CSS DESIGN ---
st.markdown(f"""
    <style>
    .stApp {{ background-color: #0E1117; }}
    .bg-watermark {{
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        width: 700px; height: 700px;
        background-image: url('data:image/png;base64,{bg_img_b64}');
        background-size: contain; background-position: center; background-repeat: no-repeat;
        opacity: 0.3; z-index: 0; pointer-events: none;
    }}
    div[data-baseweb="input"] {{ background-color: #1A1C24 !important; border: 1px solid #333 !important; border-radius: 8px !important; }}
    input {{ color: white !important; }}
    button[kind="primary"] {{ background-color: #FF4B4B !important; border: none !important; width: 100%; border-radius: 8px !important; padding: 10px !important; }}
    </style>
    <div class="bg-watermark"></div>
    """, unsafe_allow_html=True)

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

# --- GIAO DIỆN CHÍNH ---
init_db()
if "role" not in st.session_state: st.session_state.role = None
if "username" not in st.session_state: st.session_state.username = None

def login_page():
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center; color: white;'>ĐĂNG NHẬP HỆ THỐNG</h2>", unsafe_allow_html=True)
            tab_login, tab_signup = st.tabs(["Đăng nhập", "Tạo tài khoản"])
            
            with tab_login:
                user = st.text_input("", placeholder="Tên đăng nhập", key="l_user")
                pwd = st.text_input("", placeholder="Mật khẩu", type="password", key="l_pwd")
                if st.button("Đăng nhập ngay", type="primary"):
                    result = login_user(user, pwd)
                    if result == "LOCKED":
                        st.error("Tài khẩu đã bị khóa!")
                    elif result is not None:
                        # LƯU VÀO SESSION VÀ ĐẨY LÊN URL CHỐNG F5
                        st.session_state.role = result
                        st.session_state.username = user
                        st.query_params["user"] = user
                        st.query_params["role"] = str(result)
                        st.rerun()
                    else: st.error("Sai tài khoản hoặc mật khẩu!")
            
            with tab_signup:
                new_user = st.text_input("", placeholder="Tên tài khoản mới", key="s_user")
                new_pwd = st.text_input("", placeholder="Mật khẩu mới", type="password", key="s_pwd")
                role_map = {"Tài xế": 2, "Người dùng": 3}
                choice = st.selectbox("Vai trò", list(role_map.keys()))
                if st.button("Xác nhận đăng ký", type="primary"):
                    if new_user and new_pwd:
                        if add_user(new_user, new_pwd, role_map[choice]): 
                            st.success("Thành công! Mời Đăng nhập.")
                        else: st.error("Tên tài khoản đã tồn tại!")
                    else: st.warning("Điền đủ thông tin.")

# --- ĐIỀU HƯỚNG ---
page_login = st.Page(login_page, title="Đăng nhập")
page_admin = st.Page("admin.py", title="Quản trị viên")
page_driver = st.Page("app.py", title="Bản đồ AI Logistics")
page_user = st.Page("user.py", title="Mua sắm trực tuyến")

if st.session_state.role is None: 
    pg = st.navigation([page_login])
elif str(st.session_state.role) == "1": 
    pg = st.navigation([page_admin])
elif str(st.session_state.role) == "2": 
    pg = st.navigation([page_driver])
else: 
    pg = st.navigation([page_user])

pg.run()