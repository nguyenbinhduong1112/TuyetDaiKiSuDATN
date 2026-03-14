import streamlit as st
import pandas as pd
import pyodbc
import folium
from streamlit_folium import st_folium
import base64

# ==========================================
# CẤU HÌNH KẾT NỐI SQL SERVER
# ==========================================
SERVER_NAME = 'DESKTOP-U4FQD35' 
DATABASE_NAME = 'LogisticsDB'
CONN_STR = f"Driver={{SQL Server}};Server={SERVER_NAME};Database={DATABASE_NAME};Trusted_Connection=yes;"

def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except Exception: return ""

# --- 1. THIẾT LẬP GIAO DIỆN CHUNG ---
st.set_page_config(layout="wide", page_title="Quản trị - UMBRELLA LOGISTICS")
bg_img_b64 = get_base64_of_bin_file(r"D:\datn\img\E2449DA3-F2EB-430A-A588-2F9E9C6C2961.png")

st.markdown(f"""
    <style>
    .stApp {{ background-color: #0E1117; color: white; }}
    [data-testid="stSidebar"] {{ background-color: #1A1C24; border-right: 1px solid #333; padding-top: 1rem; }}
    div[data-testid="metric-container"] {{ background-color: #1A1C24; padding: 15px; border-radius: 10px; border: 1px solid #333; }}
    .stDataFrame {{ border-radius: 8px; border: 1px solid #333; }}
    
    /* MENU TRƯỢT HIỆN ĐẠI CHO SIDEBAR */
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] {{ gap: 5px; }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] {{
        background-color: transparent; border-radius: 6px; padding: 10px 15px;
        cursor: pointer; transition: all 0.2s ease-in-out; border-left: 4px solid transparent; margin-bottom: 2px;
    }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {{ display: none !important; }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover {{ background-color: #21262d; transform: translateX(4px); }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) {{ background-color: #21262d; border-left: 4px solid #FF4B4B; }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] p {{ color: #8b949e !important; font-weight: 500; font-size: 16px; margin: 0; }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) p {{ color: white !important; font-weight: 700; }}
    
    /* WATERMARK CSS */
    .bg-watermark {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 700px; height: 700px; background-image: url('data:image/png;base64,{bg_img_b64}'); background-size: contain; background-position: center; background-repeat: no-repeat; opacity: 0.15; z-index: 0; pointer-events: none; }}
    </style>
    <div class="bg-watermark"></div>
""", unsafe_allow_html=True)

if "username" not in st.session_state or str(st.session_state.get("role")) != "1":
    st.warning("Vui lòng đăng nhập bằng tài khoản Quản trị viên!")
    st.stop()

# --- HÀM XỬ LÝ DATABASE ---
def get_all_users():
    try:
        conn = pyodbc.connect(CONN_STR)
        query = '''
            SELECT 
                username, 
                ISNULL(fullname, username) as fullname,
                role, 
                ISNULL(is_locked, 0) as is_locked,
                ISNULL(current_status, N'Ngoại tuyến') as current_status,
                lat, lon
            FROM userstable
        '''
        df = pd.read_sql(query, conn)
        df['role'] = df['role'].astype(str)
        conn.close()
        return df
    except: return pd.DataFrame()

def update_user_info(username, new_fullname, is_locked):
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("UPDATE userstable SET fullname = ?, is_locked = ? WHERE username = ?", (new_fullname, is_locked, username))
        conn.commit()
        conn.close()
        return True
    except: return False

df_users = get_all_users()

# ==========================================
# 2. POPOVER ĐĂNG XUẤT (GÓC PHẢI TRÊN CÙNG)
# ==========================================
admin_name = df_users[df_users['username'] == st.session_state.username]['fullname'].values[0] if not df_users.empty else st.session_state.username

col_space, col_user = st.columns([8.5, 1.5])
with col_user:
    with st.popover(f"Quản trị: {admin_name}", use_container_width=True):
        st.markdown(f"**{admin_name}**")
        st.write("Vai trò: Quản trị hệ thống")
        st.write("Trạng thái: Trực tuyến")
        st.divider()
        if st.button("Đăng xuất", use_container_width=True, type="primary"):
            st.session_state.role = None
            st.session_state.username = None
            st.rerun()

# ==========================================
# 3. SIDEBAR: MENU ĐIỀU HƯỚNG CHÍNH
# ==========================================
with st.sidebar:
    st.markdown("<h3 style='color: white; margin-bottom: 20px; font-weight: bold;'>BẢNG QUẢN TRỊ</h3>", unsafe_allow_html=True)
    
    menu_selection = st.radio(
        "Điều hướng",
        ["Bản đồ Điều phối", "Quản lý Tài xế", "Quản lý Khách hàng"],
        label_visibility="collapsed"
    )

st.markdown("<div style='margin-top:-50px;'></div>", unsafe_allow_html=True)

# ==========================================
# 4. XỬ LÝ GIAO DIỆN THEO MENU ĐÃ CHỌN
# ==========================================

# ----------------- GIAO DIỆN 1: BẢN ĐỒ ĐIỀU PHỐI -----------------
if menu_selection == "Bản đồ Điều phối":
    st.title("BẢNG ĐIỀU KHIỂN ĐIỀU PHỐI")
    
    total_drivers = len(df_users[df_users['role'] == '2']) if not df_users.empty else 0
    online_drivers = len(df_users[(df_users['role'] == '2') & (df_users['current_status'] != "Ngoại tuyến")]) if not df_users.empty else 0
    locked_users = len(df_users[df_users['is_locked'] == 1]) if not df_users.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng Tài xế", total_drivers)
    c2.metric("Đang hoạt động", online_drivers)
    c3.metric("Tài khoản bị khóa", locked_users)
    c4.metric("Trạng thái Máy chủ", "Bình thường")
    st.divider()

    col_map, col_list = st.columns([2.5, 1.2])

    with col_map:
        st.subheader("Bản đồ giám sát trực tuyến")
        m_admin = folium.Map(location=[18.6733, 105.6813], zoom_start=14, tiles="cartodbpositron")
        
        folium.Marker(
            location=[18.6601, 105.6942], 
            icon=folium.DivIcon(html='<div style="color:white; background:#FF4B4B; border-radius:50%; width:35px; height:35px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5);">KHO</div>')
        ).add_to(m_admin)
        
        if not df_users.empty:
            active_drivers_df = df_users[(df_users['role'] == '2') & 
                                         (df_users['current_status'] != 'Ngoại tuyến') & 
                                         (df_users['lat'].notna())]
            
            for _, driver in active_drivers_df.iterrows():
                icon_color = "green" if driver['current_status'] == "Sẵn sàng" else "orange"
                folium.Marker(
                    location=[driver['lat'], driver['lon']],
                    icon=folium.Icon(color=icon_color, icon="truck", prefix="fa"), 
                    tooltip=f"{driver['fullname']} ({driver['current_status']})"
                ).add_to(m_admin)

        st_folium(m_admin, width="100%", height=600, key="admin_folium_map", returned_objects=[])

    with col_list:
        st.subheader("Giám sát Tài xế")
        if st.button("Cập nhật dữ liệu", use_container_width=True): st.rerun()
            
        if not df_users.empty:
            driver_list = df_users[df_users['role'] == '2'].copy()
            if not driver_list.empty:
                # --- PHÉP THUẬT: ĐẨY TÀI XẾ ONLINE LÊN TRÊN CÙNG ---
                driver_list['is_offline'] = driver_list['current_status'] == "Ngoại tuyến"
                driver_list = driver_list.sort_values(by=['is_offline', 'fullname'])
                
                for _, drv in driver_list.iterrows():
                    if drv['current_status'] == "Ngoại tuyến": status_color = "gray"
                    elif drv['current_status'] == "Sẵn sàng": status_color = "#00FF00"
                    else: status_color = "orange"
                        
                    st.markdown(f"""
                    <div style="background-color: #1A1C24; padding: 15px; border-radius: 8px; border-left: 5px solid {status_color}; margin-bottom: 10px;">
                        <h4 style="margin:0; color: white;"><span style="color: {status_color}; font-size: 18px;">●</span> {drv['fullname']}</h4>
                        <p style="margin: 5px 0 0 0; font-size: 14px; color: #A0AEC0;">
                            Tên đăng nhập: {drv['username']} <br>
                            Trạng thái: <b>{drv['current_status']}</b>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
            else: st.info("Hệ thống chưa có dữ liệu tài xế.")

# ----------------- GIAO DIỆN 2: QUẢN LÝ TÀI XẾ -----------------
elif menu_selection == "Quản lý Tài xế":
    st.title("QUẢN LÝ DANH SÁCH TÀI XẾ")
    st.write("Xem và cập nhật thông tin đội ngũ giao hàng.")
    st.divider()
    
    if not df_users.empty:
        df_drivers = df_users[df_users['role'] == '2']
        if not df_drivers.empty:
            display_df = df_drivers[['username', 'fullname', 'current_status', 'is_locked']].copy()
            display_df['Trạng thái khóa'] = display_df['is_locked'].apply(lambda x: "Bị khóa" if x == 1 else "Bình thường")
            st.dataframe(display_df[['username', 'fullname', 'current_status', 'Trạng thái khóa']], use_container_width=True, hide_index=True)
            
            st.markdown("### Chỉnh sửa thông tin Tài xế")
            col_form1, col_form2 = st.columns(2)
            with col_form1:
                target_driver = st.selectbox("Chọn tài khoản Tài xế:", df_drivers['username'].tolist())
                driver_info = df_drivers[df_drivers['username'] == target_driver].iloc[0]
                
                with st.form("edit_driver_form"):
                    new_fn = st.text_input("Tên hiển thị (Tên thật):", value=driver_info['fullname'])
                    lock_status = "Bị khóa" if driver_info['is_locked'] == 1 else "Bình thường"
                    new_lock_str = st.radio("Quyền truy cập:", ["Bình thường", "Bị khóa"], index=0 if lock_status == "Bình thường" else 1, horizontal=True)
                    new_lock_val = 1 if new_lock_str == "Bị khóa" else 0
                    
                    if st.form_submit_button("Lưu thay đổi", use_container_width=True):
                        if update_user_info(target_driver, new_fn, new_lock_val):
                            st.success("Đã cập nhật dữ liệu thành công!")
                            st.rerun()
        else: st.info("Không có tài xế nào trong hệ thống.")

# ----------------- GIAO DIỆN 3: QUẢN LÝ KHÁCH HÀNG -----------------
elif menu_selection == "Quản lý Khách hàng":
    st.title("QUẢN LÝ DANH SÁCH KHÁCH HÀNG")
    st.write("Xem và thiết lập quyền truy cập cho người dùng.")
    st.divider()
    
    if not df_users.empty:
        df_customers = df_users[df_users['role'] == '3']
        if not df_customers.empty:
            display_df = df_customers[['username', 'fullname', 'is_locked']].copy()
            display_df['Trạng thái khóa'] = display_df['is_locked'].apply(lambda x: "Bị khóa" if x == 1 else "Bình thường")
            st.dataframe(display_df[['username', 'fullname', 'Trạng thái khóa']], use_container_width=True, hide_index=True)
            
            st.markdown("### Chỉnh sửa thông tin Khách hàng")
            col_form1, col_form2 = st.columns(2)
            with col_form1:
                target_customer = st.selectbox("Chọn tài khoản Khách hàng:", df_customers['username'].tolist())
                customer_info = df_customers[df_customers['username'] == target_customer].iloc[0]
                
                with st.form("edit_customer_form"):
                    new_fn = st.text_input("Tên hiển thị (Tên thật):", value=customer_info['fullname'])
                    lock_status = "Bị khóa" if customer_info['is_locked'] == 1 else "Bình thường"
                    new_lock_str = st.radio("Quyền truy cập:", ["Bình thường", "Bị khóa"], index=0 if lock_status == "Bình thường" else 1, horizontal=True)
                    new_lock_val = 1 if new_lock_str == "Bị khóa" else 0
                    
                    if st.form_submit_button("Lưu thay đổi", use_container_width=True):
                        if update_user_info(target_customer, new_fn, new_lock_val):
                            st.success("Đã cập nhật dữ liệu thành công!")
                            st.rerun()
        else: st.info("Không có khách hàng nào trong hệ thống. Hãy tạo thử ở trang đăng nhập!")