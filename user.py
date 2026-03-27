import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import os
import base64
import math
from geopy.geocoders import Nominatim
from datetime import datetime
import pyodbc
from config import CONN_STR

geolocator = Nominatim(user_agent="umbrella_logistics_user")

# --- TỐI ƯU HIỆU NĂNG: CACHE ẢNH VÀO RAM ---
@st.cache_data
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except Exception: return ""

# ĐỌC ẢNH LOGO VÀ BACKGROUND TỪ ĐẦU ĐỂ NHÚNG VÀO CSS (SỬ DỤNG ĐƯỜNG DẪN TƯƠNG ĐỐI)
bg_img_b64 = get_base64_of_bin_file(os.path.join("img", "E2449DA3-F2EB-430A-A588-2F9E9C6C2961.png"))
logo_head_b64 = get_base64_of_bin_file(os.path.join("img", "19180C31-3EB3-48C4-92C8-7CD1BC52F90C (1).png"))
page_icon_path = os.path.join("img", "4D5185D2-0AD7-49AC-B7B2-4E94C13DB13C.png")

# --- 1. THIẾT LẬP GIAO DIỆN CHUNG ---
st.set_page_config(layout="wide", page_title="Khách hàng - Umbrella Logistics", page_icon=page_icon_path if os.path.exists(page_icon_path) else None)

# CHÈN CSS ĐỒNG BỘ UI VÀ NHÚNG ICON VÀO NÚT LÀM MỚI BẰNG FONTAWESOME
st.markdown(f"""
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
    .stApp {{ background-color: #0E1117; color: white; }}
    [data-testid="stSidebar"] {{ background-color: #1A1C24; border-right: 1px solid #333; padding-top: 1rem; display: flex; flex-direction: column; justify-content: space-between; }}
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] {{ gap: 8px; }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] {{ background-color: transparent; border-radius: 8px; padding: 12px 15px; cursor: pointer; transition: all 0.2s ease-in-out; border-left: 4px solid transparent; margin-bottom: 2px; }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {{ display: none !important; }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover {{ background-color: #21262d; transform: translateX(4px); }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) {{ background-color: #21262d; border-left: 4px solid #FF4B4B; }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"] p {{ color: #8b949e !important; font-weight: 500; font-size: 16px; margin: 0; display: flex; align-items: center; gap: 12px; }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) p {{ color: white !important; font-weight: 700; }}
    
    /* Icon Menu Radio Sidebar bằng FontAwesome */
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(1) p::before {{ content: '\\f07a'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(2) p::before {{ content: '\\f466'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}
    [data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(3) p::before {{ content: '\\f2c2'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}
    [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover p::before, [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) p::before {{ color: #FF4B4B !important; }}
    
    /* STYLE CHO NÚT SIDEBAR: Dùng FontAwesome tạo icon Làm mới thay vì dùng Emoji/PNG */
    [data-testid="stSidebar"] .stButton > button {{ border-radius: 8px; font-weight: 700; text-transform: uppercase; font-size: 14px; letter-spacing: 1px; transition: all 0.2s; }}
    [data-testid="stSidebar"] .stButton > button p::before {{ 
        content: '\\f2f9'; /* Mã icon xoay tròn (fa-rotate-right) */
        font-family: 'Font Awesome 6 Free'; 
        font-weight: 900; 
        margin-right: 8px; 
        font-size: 16px;
    }} 
    
    /* UI Khác */
    div[data-testid="metric-container"] {{ background-color: #1A1C24; padding: 15px; border-radius: 10px; border: 1px solid #333; z-index: 2; position: relative; }}
    button[kind="primary"] {{ background-color: #FF4B4B !important; border-color: #FF4B4B !important; transition: all 0.3s ease-in-out !important; }}
    button[kind="primary"]:hover {{ background-color: #FF7575 !important; border-color: #FF7575 !important; color: white !important; }}
    .bg-watermark {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 700px; height: 700px; background-image: url('data:image/png;base64,{bg_img_b64}'); background-size: contain; background-position: center; background-repeat: no-repeat; opacity: 0.15; z-index: 0; pointer-events: none; }}
</style>
<div class="bg-watermark"></div>
""", unsafe_allow_html=True)

# KIỂM TRA BẢO MẬT
if "user" in st.query_params: st.session_state.username = st.query_params["user"]
if "role" in st.query_params: st.session_state.role = st.query_params["role"]

if "username" not in st.session_state or str(st.session_state.role) != "3":
    st.warning("Vui lòng đăng nhập bằng tài khoản Khách hàng!")
    st.stop()

# --- CACHE DATA ---
@st.cache_data(ttl=300)
def get_warehouse_loc():
    try:
        conn = pyodbc.connect(CONN_STR)
        df = pd.read_sql("SELECT lat, lon FROM WarehouseConfig WHERE id = 1", conn)
        conn.close()
        return [df.iloc[0]['lat'], df.iloc[0]['lon']] if not df.empty else [18.6601, 105.6942]
    except: return [18.6601, 105.6942]

@st.cache_data(ttl=300) 
def get_user_fullname(username):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        cursor.execute("SELECT fullname FROM userstable WHERE username = ?", (username,))
        row = cursor.fetchone(); conn.close()
        return row[0] if row and row[0] else username
    except: return username

@st.cache_data(ttl=30)
def get_user_history_orders(username):
    try:
        conn = pyodbc.connect(CONN_STR)
        df = pd.read_sql(f"SELECT point_id, lat, lon, status, delivery_status, created_at FROM LogisticsPoints WHERE created_by = '{username}' ORDER BY created_at DESC", conn)
        conn.close()
        return df
    except: return pd.DataFrame()

user_fullname = get_user_fullname(st.session_state.username)
wh_loc = get_warehouse_loc()

if 'temp_lat' not in st.session_state: st.session_state.temp_lat = None
if 'temp_lon' not in st.session_state: st.session_state.temp_lon = None

# Header Profile
col_space, col_user = st.columns([8.5, 1.5])
with col_user:
    with st.popover(f"{user_fullname}", use_container_width=True):
        st.markdown(f"**<i class='fa-solid fa-user' style='color:#FF4B4B;'></i> Khách hàng:**<br><span style='color:#e0e0e0;'>{user_fullname}</span>", unsafe_allow_html=True)
        st.divider()
        if st.button("Đăng xuất", use_container_width=True, type="primary"):
            st.session_state.role = None; st.session_state.username = None; st.query_params.clear(); st.rerun()

# ==========================================
# SIDEBAR MENU (CHỈ DÙNG LOGO TRƯỚC CHỮ UMBRELLA APP)
# ==========================================
if logo_head_b64:
    logo_sidebar_html = f'<img src="data:image/png;base64,{logo_head_b64}" style="width: 45px; margin-right: 12px; z-index: 2; position: relative;">'
else:
    logo_sidebar_html = '<i class="fa-solid fa-box" style="font-size: 30px; margin-right: 12px; color: white; z-index: 2; position: relative;"></i>'

with st.sidebar:
    st.markdown(f"<div style='display: flex; align-items: center; margin-bottom: 20px;'>{logo_sidebar_html}<h3 style='color: white; margin: 0; font-weight: bold;'>Dịch vụ vận tải</h3></div>", unsafe_allow_html=True)
    
    if st.button("LÀM MỚI DỮ LIỆU", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    st.markdown("<hr style='margin: 10px 0; border-color: #333;'>", unsafe_allow_html=True)
    menu_selection = st.radio("Điều hướng", ["Đặt đơn hàng", "Lịch sử đơn hàng", "Quản lý thông tin cá nhân"], label_visibility="collapsed")
    st.markdown("<div style='flex-grow: 1; height: 35vh;'></div>", unsafe_allow_html=True)
    st.markdown(f"""<div style="text-align: center; padding: 20px 0; border-top: 1px solid #333; margin-top: auto;"><img src="data:image/png;base64,{bg_img_b64}" style="width: 140px; opacity: 0.15; filter: grayscale(100%);"><p style="color: #8b949e; font-size: 13px; margin-top: 15px; font-weight: bold; letter-spacing: 1px;">UMBRELLA CUSTOMER APP</p><p style="color: #444; font-size: 11px; margin-top: -10px;">Vinh City Supply Chain © 2026</p></div>""", unsafe_allow_html=True)

st.markdown("<div style='margin-top:-50px;'></div>", unsafe_allow_html=True)

# ==========================================
# GIAO DIỆN 1: ĐẶT ĐƠN HÀNG 
# ==========================================
if menu_selection == "Đặt đơn hàng":
    # Gọi thẳng icon FontAwesome (fa-cart-shopping) thay vì load ảnh tĩnh
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px; z-index: 2; position: relative;">
            <i class="fa-solid fa-cart-shopping" style="font-size: 38px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 45px; font-weight: 700; color: white;">Tạo đơn vận chuyển</h1>
        </div>
        <hr style="margin-top: 5px; border-color: #333; z-index: 2; position: relative;">
    """, unsafe_allow_html=True)

    col_map, col_form = st.columns([3, 1])
    
    with col_form:
        st.markdown("### Chọn vị trí nhận/giao", unsafe_allow_html=True)
        st.markdown("""<div style="background-color: rgba(25, 118, 210, 0.15); border-left: 4px solid #1976D2; padding: 12px 15px; border-radius: 5px; margin-bottom: 15px;"><span style="color: #1976D2; font-weight: bold; font-size: 14px;">Nhập địa chỉ bên dưới hoặc <b>bấm trực tiếp lên bản đồ</b>. Đơn sau khi tạo sẽ được gửi cho Quản trị viên duyệt.</span></div>""", unsafe_allow_html=True)
        
        addr_input = st.text_input("Nhập địa chỉ (TP Vinh, Nghệ An):")
        if st.button("TÌM KIẾM VỊ TRÍ", use_container_width=True):
            with st.spinner("Đang tìm vị trí..."):
                loc = geolocator.geocode(addr_input)
                if loc:
                    st.session_state.temp_lat = loc.latitude; st.session_state.temp_lon = loc.longitude
                    st.success("Đã ghim vị trí trên bản đồ!")
                else: st.error("Không tìm thấy địa chỉ!")

        st.write("---")
        if st.session_state.temp_lat and st.session_state.temp_lon:
            st.markdown(f"""<div style="padding: 10px; border: 1px solid #FF4B4B; border-radius: 8px; margin-bottom: 15px; background: rgba(255, 75, 75, 0.1);"><b style="color:white;">Vị trí đã chọn:</b><br><code style="color:#FF4B4B; background:transparent;">Vĩ độ: {st.session_state.temp_lat:.5f}</code><br><code style="color:#FF4B4B; background:transparent;">Kinh độ: {st.session_state.temp_lon:.5f}</code></div>""", unsafe_allow_html=True)
            
            if st.button("GỬI YÊU CẦU TẠO ĐƠN", type="primary", use_container_width=True):
                with st.spinner("Đang gửi yêu cầu cho Admin..."):
                    try:
                        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO LogisticsPoints (lat, lon, status, created_by, created_at, delivery_status) 
                            VALUES (?, ?, N'Chờ Admin duyệt', ?, GETDATE(), N'Chờ xếp xe')
                        """, (st.session_state.temp_lat, st.session_state.temp_lon, st.session_state.username))
                        conn.commit(); conn.close()
                        st.session_state.temp_lat = None; st.session_state.temp_lon = None
                        st.cache_data.clear()
                        st.success("GỬI ĐƠN THÀNH CÔNG! ĐANG CHỜ ADMIN DUYỆT ĐỂ XẾP XE.")
                    except Exception as e: st.error(f"Có lỗi xảy ra: {e}")
        else:
            st.button("GỬI YÊU CẦU TẠO ĐƠN", disabled=True, use_container_width=True)

    with col_map:
        center_loc = [st.session_state.temp_lat, st.session_state.temp_lon] if st.session_state.temp_lat else wh_loc
        m_user = folium.Map(location=center_loc, zoom_start=14, tiles="cartodbpositron")
        folium.Marker(location=wh_loc, icon=folium.DivIcon(html=f'<div style="color:white; background:#555; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5); font-size: 11px;">KHO</div>')).add_to(m_user)
        
        if st.session_state.temp_lat and st.session_state.temp_lon:
            folium.Marker(
                location=[st.session_state.temp_lat, st.session_state.temp_lon], 
                icon=folium.DivIcon(html=f'<div style="color:white; background:#1976D2; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5); font-size: 11px;">MỚI</div>'),
                tooltip="Vị trí bạn muốn giao/nhận"
            ).add_to(m_user)

        map_data = st_folium(m_user, width="100%", height=550, key="user_create_order_map", returned_objects=["last_clicked"])
        if map_data and map_data.get("last_clicked"):
            lat, lon = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
            if lat != st.session_state.temp_lat or lon != st.session_state.temp_lon:
                st.session_state.temp_lat = lat; st.session_state.temp_lon = lon
                st.rerun()

# ==========================================
# GIAO DIỆN 2: LỊCH SỬ ĐƠN HÀNG 
# ==========================================
elif menu_selection == "Lịch sử đơn hàng":
    # Dùng FontAwesome (fa-boxes-stacked) 
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px; z-index: 2; position: relative;">
            <i class="fa-solid fa-boxes-stacked" style="font-size: 38px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 40px; font-weight: 700; color: white;">Lịch sử đơn hàng của bạn</h1>
        </div>
        <hr style="margin-top: 5px; border-color: #333; z-index: 2; position: relative;">
    """, unsafe_allow_html=True)

    df_history = get_user_history_orders(st.session_state.username)
    if not df_history.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Tổng số đơn đã tạo", len(df_history))
        c2.metric("Đang chờ duyệt/Xử lý", len(df_history[df_history['status'] != 'Đã hoàn thành']))
        c3.metric("Đã hoàn thành", len(df_history[df_history['status'] == 'Đã hoàn thành']))
        st.divider()

        df_display = df_history.copy()
        
        # --- BỘ PHIÊN DỊCH TRẠNG THÁI DÀNH RIÊNG CHO KHÁCH HÀNG ---
        df_display['status'] = df_display['status'].replace({
            'Chờ Admin duyệt': 'Đang chờ Admin duyệt',
            'Chờ xử lý': 'Đã duyệt - Đang điều phối xe',
            'Đã hoàn thành': 'Giao hàng thành công'
        })
        
        df_display.rename(columns={'point_id': 'Mã Đơn', 'lat': 'Vĩ độ', 'lon': 'Kinh độ', 'status': 'Trạng thái Hệ thống', 'delivery_status': 'Trạng thái Giao hàng', 'created_at': 'Thời gian tạo'}, inplace=True)
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else: st.info("Bạn chưa tạo đơn hàng nào. Hãy sang mục 'Đặt đơn hàng' để bắt đầu nhé!")

# ==========================================
# GIAO DIỆN 3: QUẢN LÝ THÔNG TIN CÁ NHÂN 
# ==========================================
elif menu_selection == "Quản lý thông tin cá nhân":
    # Dùng FontAwesome (fa-id-badge)
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px; z-index: 2; position: relative;">
            <i class="fa-solid fa-id-badge" style="font-size: 38px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 40px; font-weight: 700; color: white;">Quản lý thông tin cá nhân</h1>
        </div>
        <hr style="margin-top: 5px; border-color: #333; z-index: 2; position: relative;">
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div style="background-color: #1A1C24; padding: 20px; border-radius: 10px; border: 1px solid #333; max-width: 500px; z-index: 2; position: relative;">
            <h3 style="color: white; margin-top:0;">Hồ sơ Khách hàng</h3>
            <p style="color: #8b949e; font-size: 16px;"><b>Tài khoản đăng nhập:</b> <span style="color:white;">{st.session_state.username}</span></p>
            <p style="color: #8b949e; font-size: 16px;"><b>Họ và tên:</b> <span style="color:white;">{user_fullname}</span></p>
            <p style="color: #8b949e; font-size: 16px;"><b>Phân quyền hệ thống:</b> <span style="color:white;">Khách hàng (Role 3)</span></p>
        </div>
    """, unsafe_allow_html=True)