import streamlit as st
import pandas as pd
import pyodbc
import folium
from streamlit_folium import st_folium
import base64
import random
from geopy.geocoders import Nominatim
from datetime import datetime
import os
from config import CONN_STR

geolocator = Nominatim(user_agent="umbrella_logistics_admin")

# --- PHỤC HỒI TRÍ NHỚ TỪ URL KHI F5 ---
if "user" in st.query_params and "role" in st.query_params:
    st.session_state.username = st.query_params["user"]
    st.session_state.role = st.query_params["role"]

# --- TỐI ƯU CỐT LÕI: ĐỌC ẢNH 1 LẦN VÀO RAM ---
@st.cache_data
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except Exception: return ""

# ĐỌC ẢNH LOGO VÀ BACKGROUND TỪ ĐẦU (ĐÃ SỬA THÀNH ĐƯỜNG DẪN TƯƠNG ĐỐI)
bg_img_b64 = get_base64_of_bin_file(os.path.join("img", "E2449DA3-F2EB-430A-A588-2F9E9C6C2961.png"))
logo_head_b64 = get_base64_of_bin_file(os.path.join("img", "19180C31-3EB3-48C4-92C8-7CD1BC52F90C (1).png"))

# --- 1. THIẾT LẬP GIAO DIỆN CHUNG ---
st.set_page_config(layout="wide", page_title="Quản trị - UMBRELLA LOGISTICS")

# NHÚNG THƯ VIỆN FONTAWESOME 6 VÀ CSS NÉN (Dùng FontAwesome cho nút LÀM MỚI DỮ LIỆU)
st.markdown(f"""<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"><style>.stApp {{ background-color: #0E1117; color: white; }}[data-testid="stSidebar"] {{ background-color: #1A1C24; border-right: 1px solid #333; padding-top: 1rem; display: flex; flex-direction: column; justify-content: space-between; }}div[data-testid="metric-container"] {{ background-color: #1A1C24; padding: 15px; border-radius: 10px; border: 1px solid #333; }}.stDataFrame {{ border-radius: 8px; border: 1px solid #333; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] {{ gap: 8px; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] {{ background-color: transparent; border-radius: 8px; padding: 12px 15px; cursor: pointer; transition: all 0.2s ease-in-out; border-left: 4px solid transparent; margin-bottom: 2px; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {{ display: none !important; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover {{ background-color: #21262d; transform: translateX(4px); }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) {{ background-color: #21262d; border-left: 4px solid #FF4B4B; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] p {{ color: #8b949e !important; font-weight: 500; font-size: 16px; margin: 0; display: flex; align-items: center; gap: 12px; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) p {{ color: white !important; font-weight: 700; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(1) p::before {{ content: '\\f279'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(2) p::before {{ content: '\\f466'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(3) p::before {{ content: '\\f4fc'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(4) p::before {{ content: '\\f0c0'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover p::before, [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) p::before {{ color: #FF4B4B !important; }}div[data-testid="stPopover"] > button {{ background-color: #1A1C24 !important; color: white !important; border: 1px solid #333 !important; opacity: 1 !important; }}div[data-testid="stPopover"] > button:hover {{ background-color: #21262d !important; border-color: #FF4B4B !important; }}[data-testid="stSidebar"] .stButton > button {{ border-radius: 8px; font-weight: 700; text-transform: uppercase; font-size: 14px; letter-spacing: 1px; transition: all 0.2s; }}[data-testid="stSidebar"] .stButton > button p::before {{ content: '\\f2f9'; font-family: 'Font Awesome 6 Free'; font-weight: 900; margin-right: 8px; font-size: 16px; }}.bg-watermark {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 700px; height: 700px; background-image: url('data:image/png;base64,{bg_img_b64}'); background-size: contain; background-position: center; background-repeat: no-repeat; opacity: 0.15; z-index: 0; pointer-events: none; }}</style><div class="bg-watermark"></div>""", unsafe_allow_html=True)

# KIỂM TRA BẢO MẬT
if "username" not in st.session_state or str(st.session_state.role) != "1":
    st.warning("Vui lòng đăng nhập bằng tài khoản Quản trị viên!")
    st.stop()

# --- TỐI ƯU CỐT LÕI: CACHE TRUY VẤN SQL ---
@st.cache_data(ttl=300) 
def get_warehouse_loc():
    try:
        conn = pyodbc.connect(CONN_STR)
        df = pd.read_sql("SELECT lat, lon FROM WarehouseConfig WHERE id = 1", conn)
        conn.close()
        return [df.iloc[0]['lat'], df.iloc[0]['lon']] if not df.empty else [18.6601, 105.6942]
    except: return [18.6601, 105.6942]

@st.cache_data(ttl=15) 
def get_active_points():
    try:
        conn = pyodbc.connect(CONN_STR)
        df = pd.read_sql("SELECT point_id, lat, lon, customer_name, ISNULL(created_by, 'admin') as created_by, ISNULL(created_at, GETDATE()) as created_at FROM LogisticsPoints WHERE status = N'Chờ xử lý'", conn)
        conn.close()
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=30) 
def get_all_users():
    try:
        conn = pyodbc.connect(CONN_STR)
        query = "SELECT username, ISNULL(fullname, username) as fullname, role, ISNULL(is_locked, 0) as is_locked, ISNULL(current_status, N'Ngoại tuyến') as current_status, lat, lon FROM userstable"
        df = pd.read_sql(query, conn)
        df['role'] = df['role'].astype(str)
        conn.close()
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=15)
def get_pending_orders():
    try:
        conn = pyodbc.connect(CONN_STR)
        c_driver = pd.read_sql("SELECT COUNT(*) FROM LogisticsPoints WHERE delivery_status = N'Đang chờ duyệt'", conn).iloc[0,0]
        c_user = pd.read_sql("SELECT COUNT(*) FROM LogisticsPoints WHERE status = N'Chờ Admin duyệt'", conn).iloc[0,0]
        conn.close()
        return c_driver, c_user
    except: return 0, 0

def update_user_info(username, new_fullname, is_locked):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        cursor.execute("UPDATE userstable SET fullname = ?, is_locked = ? WHERE username = ?", (new_fullname, is_locked, username))
        conn.commit(); conn.close()
        return True
    except: return False

# LẤY DỮ LIỆU TỪ CACHE
pending_driver, pending_user = get_pending_orders()
pending_orders = pending_driver + pending_user
df_users = get_all_users()
wh_loc = get_warehouse_loc()
active_points = get_active_points()

# --- CSS TẠO CHẤM ĐỎ TĨNH NHƯ SỐ MŨ CHO MENU QUẢN LÝ ĐƠN HÀNG ---
if pending_orders > 0:
    st.markdown("""<style>[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(2) p::after { content: ''; display: inline-block; width: 8px; height: 8px; background-color: #FF4B4B; border-radius: 50%; margin-left: 3px; transform: translateY(-8px); }</style>""", unsafe_allow_html=True)

# ==========================================
# 2. HEADER
# ==========================================
admin_name = df_users[df_users['username'] == st.session_state.username]['fullname'].values[0] if not df_users.empty else st.session_state.username

col_space, col_user = st.columns([8.5, 1.5])
with col_user:
    with st.popover(f"{admin_name}", use_container_width=True):
        st.markdown(f"**<i class='fa-solid fa-user-shield' style='color:#FF4B4B;'></i> Quản trị:**<br><span style='color:#e0e0e0;'>{admin_name}</span>", unsafe_allow_html=True)
        st.divider()
        if st.button("Đăng xuất", use_container_width=True, type="primary"):
            st.session_state.role = None; st.session_state.username = None; st.query_params.clear(); st.rerun()

# ==========================================
# 3. SIDEBAR (CHỈ DÙNG LOGO CHÍNH TẠI ĐÂY)
# ==========================================
if logo_head_b64:
    logo_html = f'<img src="data:image/png;base64,{logo_head_b64}" style="width: 45px; margin-right: 12px; z-index: 2; position: relative;">'
else:
    logo_html = '<i class="fa-solid fa-truck-fast" style="font-size: 30px; margin-right: 12px; color: white; z-index: 2; position: relative;"></i>'

with st.sidebar:
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            {logo_html}
            <h3 style='color: white; margin: 0; font-weight: bold;'>BẢNG QUẢN TRỊ</h3>
        </div>
    """, unsafe_allow_html=True)
    
    # NÚT LÀM MỚI ĐÃ ĐƯỢC NHÚNG ICON QUA CSS
    if st.button("LÀM MỚI DỮ LIỆU", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("<hr style='margin: 10px 0; border-color: #333;'>", unsafe_allow_html=True)
    menu_selection = st.radio("Điều hướng", ["Bản đồ Điều phối", "Quản lý Đơn hàng", "Quản lý Tài xế", "Quản lý Khách hàng"], label_visibility="collapsed")
    
    st.markdown("<div style='flex-grow: 1; height: 35vh;'></div>", unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style="text-align: center; padding: 20px 0; border-top: 1px solid #333; margin-top: auto;">
            <img src="data:image/png;base64,{bg_img_b64}" style="width: 140px; opacity: 0.15; filter: grayscale(100%); transition: all 0.3s ease;">
            <p style="color: #8b949e; font-size: 13px; margin-top: 15px; font-weight: bold; letter-spacing: 1px;">UMBRELLA LOGISTICS</p>
            <p style="color: #444; font-size: 11px; margin-top: -10px;">Vinh City Supply Chain © 2026</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top:-50px;'></div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# GIAO DIỆN 1: BẢN ĐỒ ĐIỀU PHỐI (Dùng FontAwesome ở Header)
# ---------------------------------------------------------
if menu_selection == "Bản đồ Điều phối":
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px; z-index: 2; position: relative;">
            <i class="fa-solid fa-map-location-dot" style="font-size: 38px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 40px; font-weight: 700; color: white;">BẢNG ĐIỀU KHIỂN ĐIỀU PHỐI</h1>
        </div>
    """, unsafe_allow_html=True)

    if pending_orders > 0:
        st.markdown(f"""
            <div style="background-color: rgba(255, 204, 0, 0.15); border-left: 4px solid #ffcc00; padding: 12px 20px; border-radius: 5px; margin-bottom: 20px;">
                <span style="color: #ffcc00; font-weight: bold; font-size: 15px;">
                    <i class="fa-solid fa-bell"></i> CÓ {pending_orders} YÊU CẦU ĐANG CHỜ XÁC NHẬN. VUI LÒNG CHUYỂN SANG TAB QUẢN LÝ ĐƠN HÀNG ĐỂ DUYỆT!
                </span>
            </div>
        """, unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng đơn hàng", len(active_points))
    c2.metric("Tài xế Online", len(df_users[(df_users['role'] == '2') & (df_users['current_status'] != "Ngoại tuyến")]))
    c3.metric("Tài khoản bị khóa", len(df_users[df_users['is_locked'] == 1]))
    c4.metric("Khu vực quản lý", "TP Vinh - Nghệ An")
    st.divider()

    col_map, col_list = st.columns([2.5, 1.2])

    with col_map:
        st.subheader("Bản đồ giám sát trực tuyến")
        m_admin = folium.Map(location=wh_loc, zoom_start=14, tiles="cartodbpositron")
        folium.Marker(location=wh_loc, icon=folium.DivIcon(html=f'<div style="color:white; background:#FF4B4B; border-radius:50%; width:35px; height:35px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5);">KHO</div>')).add_to(m_admin)
        
        for _, pt in active_points.iterrows():
            gmap_link = f"https://www.google.com/maps?q={pt['lat']},{pt['lon']}"
            create_time = pt['created_at'].strftime("%H:%M %d/%m/%Y") if isinstance(pt['created_at'], datetime) else str(pt['created_at'])
            popup_html = f"""<div style="width:200px; color:black; font-family:sans-serif;"><b style="color:#D32F2F;"><i class="fa-solid fa-location-dot"></i> ĐƠN HÀNG PHÁT SINH</b><br><hr style='margin:5px 0'><b>Mã đơn:</b> #{pt['point_id']}<br><b>Người tạo:</b> {pt['created_by']}<br><b>Thời gian:</b> {create_time}<br><a href='{gmap_link}' target='_blank' style='color:#1976D2; font-weight:bold; text-decoration:none;'><i class="fa-solid fa-link"></i> Xem Google Maps</a></div>"""
            folium.Marker(location=[pt['lat'], pt['lon']], icon=folium.Icon(color="red", icon="info-sign"), tooltip="Đơn hàng chờ gom", popup=folium.Popup(popup_html, max_width=250)).add_to(m_admin)
        
        active_drivers = df_users[(df_users['role'] == '2') & (df_users['current_status'] != 'Ngoại tuyến') & (df_users['lat'].notna())]
        for _, driver in active_drivers.iterrows():
            folium.Marker(location=[driver['lat'], driver['lon']], icon=folium.Icon(color="green" if driver['current_status'] == "Sẵn sàng" else "orange", icon="truck", prefix="fa"), tooltip=f"{driver['fullname']}").add_to(m_admin)

        map_data = st_folium(m_admin, width="100%", height=500, key="admin_folium_map", returned_objects=["last_clicked"])

        with st.popover("Sửa vị trí Kho", use_container_width=True):
            t1, t2 = st.tabs(["Nhập địa chỉ", "Chọn trên Map"])
            with t1:
                addr_wh = st.text_input("Nhập địa chỉ kho mới:")
                if st.button("Tìm & Lưu Kho"):
                    loc = geolocator.geocode(addr_wh)
                    if loc:
                        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                        cursor.execute("UPDATE WarehouseConfig SET lat=?, lon=? WHERE id=1", (loc.latitude, loc.longitude))
                        conn.commit(); conn.close()
                        st.cache_data.clear(); st.rerun()
            with t2:
                st.info("Vui lòng chọn trên bản đồ để ghim vị trí")
                if map_data and map_data.get("last_clicked"):
                    if st.button("Xác nhận đổi Kho tại đây"):
                        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                        cursor.execute("UPDATE WarehouseConfig SET lat=?, lon=? WHERE id=1", (map_data['last_clicked']['lat'], map_data['last_clicked']['lng']))
                        conn.commit(); conn.close()
                        st.cache_data.clear(); st.rerun()

    with col_list:
        st.subheader("Quản lý Đơn hàng")
        with st.container(border=True):
            with st.popover("Thêm đơn hàng", use_container_width=True):
                t3, t4, t5 = st.tabs(["Nhập địa chỉ", "Chọn trên Map", "Tạo đơn mẫu"])
                with t3:
                    addr_ord = st.text_input("Địa chỉ đơn:")
                    if st.button("Tạo đơn"):
                        loc = geolocator.geocode(addr_ord)
                        if loc:
                            conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                            cursor.execute("INSERT INTO LogisticsPoints (lat, lon, status, created_by, created_at, delivery_status) VALUES (?,?,?,?, GETDATE(), N'Chờ xác nhận')", (loc.latitude, loc.longitude, "Chờ xử lý", "admin"))
                            conn.commit(); conn.close()
                            st.cache_data.clear(); st.rerun()
                with t4:
                    st.markdown("<p style='font-size:14px; margin-bottom:10px; color:#8b949e;'>Vui lòng chọn trên bản đồ để ghim vị trí.</p>", unsafe_allow_html=True)
                    if map_data and map_data.get("last_clicked"):
                        if st.button("Tạo đơn tại điểm vừa bấm"):
                            conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                            cursor.execute("INSERT INTO LogisticsPoints (lat, lon, status, created_by, created_at, delivery_status) VALUES (?,?,?,?, GETDATE(), N'Chờ xác nhận')", (map_data['last_clicked']['lat'], map_data['last_clicked']['lng'], "Chờ xử lý", "admin"))
                            conn.commit(); conn.close()
                            st.cache_data.clear(); st.rerun()
                with t5:
                    st.markdown("<p style='font-size:14px; margin-bottom:10px; color:#8b949e;'>Tạo 5 đơn hàng ngẫu nhiên quanh kho.</p>", unsafe_allow_html=True)
                    if st.button("Tạo 5 đơn mẫu", type="primary", use_container_width=True):
                        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                        base_lat, base_lon = wh_loc[0], wh_loc[1]
                        for _ in range(5):
                            r_lat = base_lat + random.uniform(-0.015, 0.015)
                            r_lon = base_lon + random.uniform(-0.015, 0.015)
                            cursor.execute("INSERT INTO LogisticsPoints (lat, lon, status, created_by, created_at, delivery_status) VALUES (?,?,?,?, GETDATE(), N'Chờ xác nhận')", (r_lat, r_lon, "Chờ xử lý", "admin"))
                        conn.commit(); conn.close()
                        st.cache_data.clear(); st.rerun()
            
            if not active_points.empty:
                st.markdown("<small>Chọn mã đơn cần hủy:</small>", unsafe_allow_html=True)
                target_del = st.selectbox("Mã đơn", active_points['point_id'].tolist(), label_visibility="collapsed")
                with st.popover(f"Hủy đơn #{target_del}", use_container_width=True):
                    st.warning(f"Bạn chắc chắn muốn xóa đơn #{target_del}?")
                    if st.button("Có, xóa ngay!", type="primary", use_container_width=True):
                        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                        cursor.execute("DELETE FROM LogisticsPoints WHERE point_id = ?", (int(target_del),))
                        conn.commit(); conn.close()
                        st.cache_data.clear(); st.rerun()
            else: st.info("Không có đơn chờ.")

        st.divider()
        st.subheader("Giám sát Tài xế")
        driver_list = df_users[df_users['role'] == '2'].copy()
        driver_list['is_offline'] = driver_list['current_status'] == "Ngoại tuyến"
        driver_list = driver_list.sort_values(by=['is_offline', 'fullname'])
        for _, drv in driver_list.iterrows():
            is_off = drv['current_status'] == "Ngoại tuyến"
            status_color = "gray" if is_off else ("#00FF00" if drv['current_status']=="Sẵn sàng" else "orange")
            st.markdown(f'<div style="background-color: #1A1C24; padding: 12px; border-radius: 8px; border-left: 5px solid {status_color}; margin-bottom: 10px;"><h4 style="margin:0; color: white;"><i class="fa-solid fa-circle" style="color: {status_color}; font-size: 10px; margin-right: 5px;"></i> {drv["fullname"]}</h4><small style="color:#A0AEC0;">Trạng thái: <b>{drv["current_status"]}</b></small></div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# GIAO DIỆN 1.5: QUẢN LÝ ĐƠN HÀNG (Dùng FontAwesome ở Header)
# ---------------------------------------------------------
elif menu_selection == "Quản lý Đơn hàng":
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px; z-index: 2; position: relative;">
            <i class="fa-solid fa-boxes-stacked" style="font-size: 38px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 40px; font-weight: 700; color: white;">QUẢN LÝ ĐƠN HÀNG</h1>
        </div>
    """, unsafe_allow_html=True)
    st.divider()

    # HIỂN THỊ YÊU CẦU TỪ KHÁCH HÀNG (TẠO ĐƠN MỚI)
    if pending_user > 0:
        st.markdown(f"""
            <div style="background-color: rgba(25, 118, 210, 0.15); border-left: 4px solid #1976D2; padding: 12px 20px; border-radius: 5px; margin-bottom: 20px;">
                <span style="color: #1976D2; font-weight: bold; font-size: 15px;">
                    <i class="fa-solid fa-box"></i> CÓ {pending_user} ĐƠN YÊU CẦU TẠO MỚI TỪ KHÁCH HÀNG!
                </span>
            </div>
        """, unsafe_allow_html=True)
        if st.button("DUYỆT TẤT CẢ ĐƠN CỦA KHÁCH VÀO HỆ THỐNG", type="primary", use_container_width=True):
            conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
            cursor.execute("UPDATE LogisticsPoints SET status = N'Chờ xử lý' WHERE status = N'Chờ Admin duyệt'")
            conn.commit(); conn.close()
            st.cache_data.clear()
            st.success("Đã duyệt thành công! Các đơn này đã xuất hiện trên bản đồ Tài xế.")
            st.rerun()
        st.divider()

    # HIỂN THỊ YÊU CẦU TỪ TÀI XẾ (XIN HOÀN THÀNH)
    if pending_driver > 0:
        st.markdown(f"""
            <div style="background-color: rgba(255, 204, 0, 0.15); border-left: 4px solid #ffcc00; padding: 12px 20px; border-radius: 5px; margin-bottom: 20px;">
                <span style="color: #ffcc00; font-weight: bold; font-size: 15px;">
                    <i class="fa-solid fa-bell"></i> CÓ {pending_driver} ĐƠN HÀNG ĐANG CHỜ XÁC NHẬN HOÀN THÀNH TỪ TÀI XẾ!
                </span>
            </div>
        """, unsafe_allow_html=True)
        
        requesting_driver = "Không xác định"
        try:
            conn_dr = pyodbc.connect(CONN_STR)
            dr_df = pd.read_sql("SELECT ISNULL(fullname, username) as fullname FROM userstable WHERE role='2' AND current_status != N'Ngoại tuyến'", conn_dr)
            if not dr_df.empty:
                requesting_driver = dr_df.iloc[0]['fullname']
            conn_dr.close()
        except: pass
        request_time = datetime.now().strftime("%H:%M:%S - %d/%m/%Y")

        with st.expander("Bấm vào đây để xem chi tiết & xử lý yêu cầu", expanded=True):
            st.markdown(f"""
                <div style="background-color: #21262d; padding: 15px; border-radius: 8px; margin-bottom: 15px; border-left: 4px solid #FF4B4B;">
                    <h4 style="margin-top: 0; color: white; margin-bottom: 10px;">Chi tiết yêu cầu</h4>
                    <p style="margin: 8px 0; color: #8b949e; font-size: 15px;"><i class="fa-solid fa-user-tie" style="color: #FF4B4B; width: 25px;"></i> <b>Tài xế yêu cầu:</b> <span style="color: white; font-weight: bold;">{requesting_driver}</span></p>
                    <p style="margin: 8px 0; color: #8b949e; font-size: 15px;"><i class="fa-solid fa-clock" style="color: #FF4B4B; width: 25px;"></i> <b>Thời gian xác nhận:</b> <span style="color: white;">{request_time}</span></p>
                    <p style="margin: 8px 0; color: #8b949e; font-size: 15px;"><i class="fa-solid fa-box-open" style="color: #FF4B4B; width: 25px;"></i> <b>Số lượng đơn:</b> <span style="color: white;">{pending_driver} đơn hàng</span></p>
                </div>
            """, unsafe_allow_html=True)

            c_btn1, c_btn2 = st.columns(2)
            if c_btn1.button("DUYỆT TẤT CẢ HOÀN THÀNH", type="primary", use_container_width=True, key="app_all_driver"):
                conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                cursor.execute("UPDATE LogisticsPoints SET status = N'Đã hoàn thành', delivery_status = N'Đã hoàn thành' WHERE delivery_status = N'Đang chờ duyệt'")
                conn.commit(); conn.close()
                st.cache_data.clear()
                st.success("Đã duyệt thành công!"); st.rerun()
            if c_btn2.button("TỪ CHỐI TẤT CẢ", use_container_width=True, key="rej_all_driver"):
                conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                cursor.execute("UPDATE LogisticsPoints SET delivery_status = N'Chờ xác nhận' WHERE delivery_status = N'Đang chờ duyệt'")
                conn.commit(); conn.close()
                st.cache_data.clear(); st.rerun()

    if pending_orders == 0:
        st.info("Hiện không có đơn hàng hay yêu cầu nào đang chờ duyệt.")

# ---------------------------------------------------------
# GIAO DIỆN 2: QUẢN LÝ TÀI XẾ (Dùng FontAwesome ở Header)
# ---------------------------------------------------------
elif menu_selection == "Quản lý Tài xế":
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px; z-index: 2; position: relative;">
            <i class="fa-solid fa-id-card-clip" style="font-size: 38px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 40px; font-weight: 700; color: white;">QUẢN LÝ DANH SÁCH TÀI XẾ</h1>
        </div>
    """, unsafe_allow_html=True)
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
                    new_lock_str = st.radio("Quyền truy cập:", ["Bình thường", "Bị khóa"], index=int(driver_info['is_locked']), horizontal=True)
                    if st.form_submit_button("Lưu thay đổi", use_container_width=True):
                        if update_user_info(target_driver, new_fn, 1 if new_lock_str == "Bị khóa" else 0):
                            st.cache_data.clear()
                            st.success("Đã cập nhật!"); st.rerun()

# ---------------------------------------------------------
# GIAO DIỆN 3: QUẢN LÝ KHÁCH HÀNG (Dùng FontAwesome ở Header)
# ---------------------------------------------------------
elif menu_selection == "Quản lý Khách hàng":
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px; z-index: 2; position: relative;">
            <i class="fa-solid fa-users" style="font-size: 38px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 40px; font-weight: 700; color: white;">QUẢN LÝ DANH SÁCH KHÁCH HÀNG</h1>
        </div>
    """, unsafe_allow_html=True)
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
                    new_lock_str = st.radio("Quyền truy cập:", ["Bình thường", "Bị khóa"], index=int(customer_info['is_locked']), horizontal=True)
                    if st.form_submit_button("Lưu thay đổi", use_container_width=True):
                        if update_user_info(target_customer, new_fn, 1 if new_lock_str == "Bị khóa" else 0):
                            st.cache_data.clear()
                            st.success("Đã cập nhật!"); st.rerun()