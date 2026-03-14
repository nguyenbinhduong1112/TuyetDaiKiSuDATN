import streamlit as st
import pandas as pd
import pyodbc
import folium
from streamlit_folium import st_folium
import base64
import random
from geopy.geocoders import Nominatim
from datetime import datetime

# ==========================================
# CẤU HÌNH KẾT NỐI SQL SERVER
# ==========================================
SERVER_NAME = 'DESKTOP-U4FQD35'
DATABASE_NAME = 'LogisticsDB'
CONN_STR = f"Driver={{SQL Server}};Server={SERVER_NAME};Database={DATABASE_NAME};Trusted_Connection=yes;"

geolocator = Nominatim(user_agent="umbrella_logistics_admin")

# --- PHỤC HỒI TRÍ NHỚ TỪ URL KHI F5 ---
if "user" in st.query_params and "role" in st.query_params:
    st.session_state.username = st.query_params["user"]
    st.session_state.role = st.query_params["role"]

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
    
    /* NÚT BẤM ĐẶC - KHÔNG TRONG SUỐT */
    div[data-testid="stPopover"] > button {{
        background-color: #1A1C24 !important;
        color: white !important;
        border: 1px solid #333 !important;
        opacity: 1 !important;
    }}
    div[data-testid="stPopover"] > button:hover {{
        background-color: #21262d !important;
        border-color: #FF4B4B !important;
    }}

    .bg-watermark {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 700px; height: 700px; background-image: url('data:image/png;base64,{bg_img_b64}'); background-size: contain; background-position: center; background-repeat: no-repeat; opacity: 0.15; z-index: 0; pointer-events: none; }}
    </style>
    <div class="bg-watermark"></div>
""", unsafe_allow_html=True)

# KIỂM TRA BẢO MẬT
if "username" not in st.session_state or str(st.session_state.role) != "1":
    st.warning("Vui lòng đăng nhập bằng tài khoản Quản trị viên!")
    st.stop()

# --- HÀM XỬ LÝ DATABASE ---
def get_warehouse_loc():
    try:
        conn = pyodbc.connect(CONN_STR)
        df = pd.read_sql("SELECT lat, lon FROM WarehouseConfig WHERE id = 1", conn)
        conn.close()
        return [df.iloc[0]['lat'], df.iloc[0]['lon']] if not df.empty else [18.6601, 105.6942]
    except: return [18.6601, 105.6942]

def get_active_points():
    try:
        conn = pyodbc.connect(CONN_STR)
        df = pd.read_sql("SELECT point_id, lat, lon, customer_name, ISNULL(created_by, 'admin') as created_by, ISNULL(created_at, GETDATE()) as created_at FROM LogisticsPoints WHERE status = N'Chờ xử lý'", conn)
        conn.close()
        return df
    except: return pd.DataFrame()

def get_all_users():
    try:
        conn = pyodbc.connect(CONN_STR)
        query = "SELECT username, ISNULL(fullname, username) as fullname, role, ISNULL(is_locked, 0) as is_locked, ISNULL(current_status, N'Ngoại tuyến') as current_status, lat, lon FROM userstable"
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
        return True
    except: return False

df_users = get_all_users()
wh_loc = get_warehouse_loc()
active_points = get_active_points()

# ==========================================
# 2. HEADER
# ==========================================
admin_name = df_users[df_users['username'] == st.session_state.username]['fullname'].values[0] if not df_users.empty else st.session_state.username

col_space, col_user = st.columns([8.5, 1.5])
with col_user:
    with st.popover(f"Quản trị: {admin_name}", use_container_width=True):
        st.markdown(f"**{admin_name}**")
        st.divider()
        if st.button("Đăng xuất", use_container_width=True, type="primary"):
            st.session_state.role = None; st.session_state.username = None; st.query_params.clear(); st.rerun()

# ==========================================
# 3. SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("<h3 style='color: white; margin-bottom: 20px; font-weight: bold;'>BẢNG QUẢN TRỊ</h3>", unsafe_allow_html=True)
    menu_selection = st.radio("Điều hướng", ["Bản đồ Điều phối", "Quản lý Tài xế", "Quản lý Khách hàng"], label_visibility="collapsed")

st.markdown("<div style='margin-top:-50px;'></div>", unsafe_allow_html=True)

if menu_selection == "Bản đồ Điều phối":
    st.title("BẢNG ĐIỀU KHIỂN ĐIỀU PHỐI")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng đơn hàng", len(active_points))
    c2.metric("Tài xế Online", len(df_users[(df_users['role'] == '2') & (df_users['current_status'] != "Ngoại tuyến")]))
    c3.metric("Tài khoản bị khóa", len(df_users[df_users['is_locked'] == 1]))
    c4.metric("Trạng thái Máy chủ", "Bình thường")
    st.divider()

    col_map, col_list = st.columns([2.5, 1.2])

    with col_map:
        st.subheader("Bản đồ giám sát trực tuyến")
        m_admin = folium.Map(location=wh_loc, zoom_start=14, tiles="cartodbpositron")
        
        folium.Marker(location=wh_loc, icon=folium.DivIcon(html=f'<div style="color:white; background:#FF4B4B; border-radius:50%; width:35px; height:35px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5);">KHO</div>')).add_to(m_admin)
        
        for _, pt in active_points.iterrows():
            gmap_link = f"https://www.google.com/maps?q={pt['lat']},{pt['lon']}"
            create_time = pt['created_at'].strftime("%H:%M %d/%m/%Y") if isinstance(pt['created_at'], datetime) else str(pt['created_at'])
            popup_html = f"""<div style="width:200px; color:black; font-family:sans-serif;"><b style="color:#D32F2F;">📍 ĐƠN HÀNG PHÁT SINH</b><br><hr style='margin:5px 0'><b>Mã đơn:</b> #{pt['point_id']}<br><b>Người tạo:</b> admin<br><b>Thời gian:</b> {create_time}<br><a href='{gmap_link}' target='_blank' style='color:#1976D2; font-weight:bold; text-decoration:none;'>🔗 Xem Google Maps</a></div>"""
            folium.Marker(location=[pt['lat'], pt['lon']], icon=folium.Icon(color="red", icon="info-sign"), tooltip="Đơn hàng phát sinh", popup=folium.Popup(popup_html, max_width=250)).add_to(m_admin)
        
        active_drivers = df_users[(df_users['role'] == '2') & (df_users['current_status'] != 'Ngoại tuyến') & (df_users['lat'].notna())]
        for _, driver in active_drivers.iterrows():
            folium.Marker(location=[driver['lat'], driver['lon']], icon=folium.Icon(color="green" if driver['current_status'] == "Sẵn sàng" else "orange", icon="truck", prefix="fa"), tooltip=f"{driver['fullname']}").add_to(m_admin)

        map_data = st_folium(m_admin, width="100%", height=500, key="admin_folium_map", returned_objects=["last_clicked"])

        # NÚT SỬA KHO
        with st.popover("Sửa vị trí Kho", use_container_width=True):
            t1, t2 = st.tabs(["Nhập địa chỉ", "Chọn trên Map"])
            with t1:
                addr_wh = st.text_input("Nhập địa chỉ kho mới:")
                if st.button("Tìm & Lưu Kho"):
                    loc = geolocator.geocode(addr_wh)
                    if loc:
                        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                        cursor.execute("UPDATE WarehouseConfig SET lat=?, lon=? WHERE id=1", (loc.latitude, loc.longitude))
                        conn.commit(); st.rerun()
            with t2:
                st.info("Vui lòng chọn trên bản đồ để ghim vị trí")
                if map_data and map_data.get("last_clicked"):
                    if st.button("Xác nhận đổi Kho tại đây"):
                        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                        cursor.execute("UPDATE WarehouseConfig SET lat=?, lon=? WHERE id=1", (map_data['last_clicked']['lat'], map_data['last_clicked']['lng']))
                        conn.commit(); st.rerun()

    with col_list:
        st.subheader("Quản lý Đơn hàng")
        with st.container(border=True):
            # Thêm đơn hàng
            with st.popover("Thêm đơn hàng", use_container_width=True):
                t3, t4 = st.tabs(["Nhập địa chỉ", "Chọn trên Map"])
                with t3:
                    addr_ord = st.text_input("Địa chỉ đơn:")
                    if st.button("Tạo đơn"):
                        loc = geolocator.geocode(addr_ord)
                        if loc:
                            conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                            cursor.execute("INSERT INTO LogisticsPoints (lat, lon, status, created_by, created_at) VALUES (?,?,?,?, GETDATE())", (loc.latitude, loc.longitude, "Chờ xử lý", "admin"))
                            conn.commit(); st.rerun()
                with t4:
                    st.info("Vui lòng chọn trên bản đồ để ghim vị trí")
                    if map_data and map_data.get("last_clicked"):
                        if st.button("Tạo đơn tại điểm vừa bấm"):
                            conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                            cursor.execute("INSERT INTO LogisticsPoints (lat, lon, status, created_by, created_at) VALUES (?,?,?,?, GETDATE())", (map_data['last_clicked']['lat'], map_data['last_clicked']['lng'], "Chờ xử lý", "admin"))
                            conn.commit(); st.rerun()
            
            # Hủy đơn hàng - ĐÃ THÊM XÁC NHẬN
            if not active_points.empty:
                st.markdown("<small>Chọn mã đơn cần hủy:</small>", unsafe_allow_html=True)
                target_del = st.selectbox("Mã đơn", active_points['point_id'].tolist(), label_visibility="collapsed")
                
                # Popover để xác nhận xóa
                with st.popover(f"Hủy đơn #{target_del}", use_container_width=True):
                    st.warning(f"Bạn chắc chắn muốn xóa đơn #{target_del}?")
                    if st.button("Có, xóa ngay!", type="primary", use_container_width=True):
                        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                        cursor.execute("DELETE FROM LogisticsPoints WHERE point_id = ?", (int(target_del),))
                        conn.commit(); st.rerun()
            else:
                st.info("Không có đơn chờ.")

        st.divider()
        st.subheader("Giám sát Tài xế")
        driver_list = df_users[df_users['role'] == '2'].copy()
        driver_list['is_offline'] = driver_list['current_status'] == "Ngoại tuyến"
        driver_list = driver_list.sort_values(by=['is_offline', 'fullname'])
        for _, drv in driver_list.iterrows():
            is_off = drv['current_status'] == "Ngoại tuyến"
            status_color = "gray" if is_off else ("#00FF00" if drv['current_status']=="Sẵn sàng" else "orange")
            st.markdown(f'<div style="background-color: #1A1C24; padding: 12px; border-radius: 8px; border-left: 5px solid {status_color}; margin-bottom: 10px;"><h4 style="margin:0; color: white;"><span style="color: {status_color};">●</span> {drv["fullname"]}</h4><small style="color:#A0AEC0;">Trạng thái: <b>{drv["current_status"]}</b></small></div>', unsafe_allow_html=True)

# (Quản lý Tài xế & Khách hàng giữ nguyên...)
elif menu_selection == "Quản lý Tài xế":
    st.title("QUẢN LÝ DANH SÁCH TÀI XẾ")
    st.divider()
    if not df_users.empty:
        df_drivers = df_users[df_users['role'] == '2']
        if not df_drivers.empty:
            display_df = df_drivers[['username', 'fullname', 'current_status', 'is_locked']].copy()
            display_df['Trạng thái khóa'] = display_df['is_locked'].apply(lambda x: "Bị khóa" if x == 1 else "Bình thường")
            st.dataframe(display_df[['username', 'fullname', 'current_status', 'Trạng thái khóa']], use_container_width=True, hide_index=True)
            st.markdown("### Chỉnh sửa thông tin Tài xế")
            target_driver = st.selectbox("Chọn tài khoản Tài xế:", df_drivers['username'].tolist())
            driver_info = df_drivers[df_drivers['username'] == target_driver].iloc[0]
            with st.form("edit_driver_form"):
                new_fn = st.text_input("Tên hiển thị (Tên thật):", value=driver_info['fullname'])
                new_lock_str = st.radio("Quyền truy cập:", ["Bình thường", "Bị khóa"], index=int(driver_info['is_locked']), horizontal=True)
                if st.form_submit_button("Lưu thay đổi", use_container_width=True):
                    if update_user_info(target_driver, new_fn, 1 if new_lock_str == "Bị khóa" else 0):
                        st.success("Đã cập nhật!"); st.rerun()

elif menu_selection == "Quản lý Khách hàng":
    st.title("QUẢN LÝ DANH SÁCH KHÁCH HÀNG")
    st.divider()
    if not df_users.empty:
        df_customers = df_users[df_users['role'] == '3']
        if not df_customers.empty:
            display_df = df_customers[['username', 'fullname', 'is_locked']].copy()
            display_df['Trạng thái khóa'] = display_df['is_locked'].apply(lambda x: "Bị khóa" if x == 1 else "Bình thường")
            st.dataframe(display_df[['username', 'fullname', 'Trạng thái khóa']], use_container_width=True, hide_index=True)
            st.markdown("### Chỉnh sửa thông tin Khách hàng")
            target_customer = st.selectbox("Chọn tài khoản Khách hàng:", df_customers['username'].tolist())
            customer_info = df_customers[df_customers['username'] == target_customer].iloc[0]
            with st.form("edit_customer_form"):
                new_fn = st.text_input("Tên hiển thị (Tên thật):", value=customer_info['fullname'])
                new_lock_str = st.radio("Quyền truy cập:", ["Bình thường", "Bị khóa"], index=int(customer_info['is_locked']), horizontal=True)
                if st.form_submit_button("Lưu thay đổi", use_container_width=True):
                    if update_user_info(target_customer, new_fn, 1 if new_lock_str == "Bị khóa" else 0):
                        st.success("Đã cập nhật!"); st.rerun()