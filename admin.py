import streamlit as st
import pandas as pd
import pyodbc
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import base64
import random
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderTimedOut, GeocoderServiceError
from datetime import datetime
import os
from config import CONN_STR
from address_search import address_form

geolocator = Nominatim(user_agent="umbrella_logistics_admin", timeout=10)


def safe_geocode(address):
    """Gọi Nominatim an toàn: trả về location hoặc None, hiện lỗi thân thiện nếu fail."""
    if not address or not address.strip():
        st.error("Vui lòng nhập địa chỉ.")
        return None
    try:
        return geolocator.geocode(address, timeout=10)
    except (GeocoderUnavailable, GeocoderTimedOut, GeocoderServiceError) as e:
        st.error(f"Dịch vụ bản đồ tạm thời không phản hồi. Vui lòng thử lại hoặc chọn vị trí trực tiếp trên Map. ({type(e).__name__})")
        return None
    except Exception as e:
        st.error(f"Lỗi khi tra cứu địa chỉ: {e}")
        return None

# --- TỐI ƯU CỐT LÕI: ĐỌC ẢNH 1 LẦN VÀO RAM ---
@st.cache_data
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    except Exception: return ""

# --- TỐI ƯU CỐT LÕI: HÀM GỌI DATABASE CHUNG ---
def execute_action(query, params=(), success_msg=None):
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        clear_admin_caches()
        if 'temp_admin_click' in st.session_state: 
            del st.session_state.temp_admin_click
        if success_msg: st.success(success_msg)
        st.rerun()
    except Exception as e:
        st.error(f"Lỗi truy vấn Database: {e}")

# --- CACHE TRUY VẤN SQL ---
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
        # [ĐÃ SỬA]: Lấy thêm cột delivery_status để Map biết đường đổi màu
        df = pd.read_sql("SELECT TOP (300) point_id, lat, lon, customer_name, ISNULL(created_by, 'admin') as created_by, ISNULL(created_at, GETDATE()) as created_at, ISNULL(delivery_status, '') as delivery_status FROM LogisticsPoints WHERE status = N'Chờ xử lý' AND order_type = N'chuỗi' ORDER BY created_at DESC", conn)
        conn.close()
        return df
    except: return pd.DataFrame()

@st.cache_data(ttl=15)
def get_active_points_count():
    try:
        conn = pyodbc.connect(CONN_STR)
        count = pd.read_sql("SELECT COUNT(*) FROM LogisticsPoints WHERE status = N'Chờ xử lý' AND order_type = N'chuỗi'", conn).iloc[0, 0]
        conn.close()
        return int(count)
    except: return 0

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

@st.cache_data(ttl=300)
def get_admin_fullname(username):
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT ISNULL(fullname, username) FROM userstable WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else username
    except:
        return username

@st.cache_data(ttl=15)
def get_pending_orders():
    try:
        conn = pyodbc.connect(CONN_STR)
        query = """
            SELECT
                SUM(CASE WHEN delivery_status = N'Đang chờ duyệt' AND order_type = N'chuỗi' THEN 1 ELSE 0 END) AS chain_driver_done,
                SUM(CASE WHEN status = N'Chờ Admin duyệt' AND order_type = N'chuỗi' THEN 1 ELSE 0 END) AS chain_user_create,
                SUM(CASE WHEN delivery_status = N'Đang chờ duyệt' AND order_type = N'lẻ' THEN 1 ELSE 0 END) AS cod_driver_done,
                SUM(CASE WHEN status = N'Chờ Admin duyệt' AND order_type = N'lẻ' THEN 1 ELSE 0 END) AS cod_user_create
            FROM LogisticsPoints
            WHERE status = N'Chờ Admin duyệt'
               OR delivery_status = N'Đang chờ duyệt'
        """
        row = pd.read_sql(query, conn).iloc[0]
        conn.close()
        return (
            0 if pd.isna(row["chain_driver_done"]) else int(row["chain_driver_done"]),
            0 if pd.isna(row["chain_user_create"]) else int(row["chain_user_create"]),
            0 if pd.isna(row["cod_driver_done"]) else int(row["cod_driver_done"]),
            0 if pd.isna(row["cod_user_create"]) else int(row["cod_user_create"]),
        )
    except: return 0, 0, 0, 0

def clear_admin_caches():
    get_warehouse_loc.clear()
    get_active_points.clear()
    get_active_points_count.clear()
    get_all_users.clear()
    get_admin_fullname.clear()
    get_pending_orders.clear()

# ==========================================
# HÀM RENDER ĐƯỢC GỌI TỪ MAIN.PY
# ==========================================
def render_page():
    if "customer" not in st.session_state or str(st.session_state.get("role", "")) != "1":
        st.warning("Vui lòng đăng nhập bằng tài khoản Quản trị viên!")
        st.stop()

    bg_img_b64 = get_base64_of_bin_file(os.path.join("img", "watermark_optimized.webp"))
    logo_head_b64 = get_base64_of_bin_file(os.path.join("img", "logo_optimized.webp"))

    st.markdown(f"""<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"><style>.stApp {{ background-color: #0E1117; color: white; }}[data-testid="stSidebar"] {{ background-color: #1A1C24; border-right: 1px solid #333; padding-top: 1rem; display: flex; flex-direction: column; justify-content: space-between; }}div[data-testid="metric-container"] {{ background-color: #1A1C24; padding: 15px; border-radius: 10px; border: 1px solid #333; }}.stDataFrame {{ border-radius: 8px; border: 1px solid #333; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] {{ gap: 8px; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] {{ background-color: transparent; border-radius: 8px; padding: 12px 15px; cursor: pointer; transition: all 0.2s ease-in-out; border-left: 4px solid transparent; margin-bottom: 2px; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {{ display: none !important; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover {{ background-color: #21262d; transform: translateX(4px); }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) {{ background-color: #21262d; border-left: 4px solid #FF4B4B; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] p {{ color: #8b949e !important; font-weight: 500; font-size: 16px; margin: 0; display: flex; align-items: center; gap: 12px; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) p {{ color: white !important; font-weight: 700; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(1) p::before {{ content: '\\f279'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(2) p::before {{ content: '\\f466'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(3) p::before {{ content: '\\f0e7'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(4) p::before {{ content: '\\f1da'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(5) p::before {{ content: '\\f091'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(6) p::before {{ content: '\\f0c0'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover p::before, [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) p::before {{ color: #FF4B4B !important; }}div[data-testid="stPopover"] > button {{ background-color: #1A1C24 !important; color: white !important; border: 1px solid #333 !important; opacity: 1 !important; }}div[data-testid="stPopover"] > button:hover {{ background-color: #21262d !important; border-color: #FF4B4B !important; }}[data-testid="stSidebar"] .stButton > button {{ border-radius: 8px; font-weight: 700; text-transform: uppercase; font-size: 14px; letter-spacing: 1px; transition: all 0.2s; }}[data-testid="stSidebar"] .stButton > button p::before {{ content: '\\f2f9'; font-family: 'Font Awesome 6 Free'; font-weight: 900; margin-right: 8px; font-size: 16px; }}.bg-watermark {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 700px; height: 700px; background-image: url('data:image/webp;base64,{bg_img_b64}'); background-size: contain; background-position: center; background-repeat: no-repeat; opacity: 0.15; z-index: 0; pointer-events: none; }}</style><div class="bg-watermark"></div>""", unsafe_allow_html=True)

    pending_driver, pending_user, pending_cod_driver, pending_cod_user = get_pending_orders()
    pending_standard = pending_driver + pending_user
    pending_cod = pending_cod_driver + pending_cod_user
    
    css_dots = ""
    if pending_standard > 0:
        css_dots += """[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(2) p::after { content: ''; display: inline-block; width: 8px; height: 8px; background-color: #FF4B4B; border-radius: 50%; margin-left: 3px; transform: translateY(-8px); }"""
    if pending_cod > 0:
        css_dots += """[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(3) p::after { content: ''; display: inline-block; width: 8px; height: 8px; background-color: #1976D2; border-radius: 50%; margin-left: 3px; transform: translateY(-8px); }"""
    if css_dots:
        st.markdown(f"<style>{css_dots}</style>", unsafe_allow_html=True)

    current_admin = st.session_state.customer
    admin_name = get_admin_fullname(current_admin)

    col_space, col_user = st.columns([8.5, 1.5])
    with col_user:
        with st.popover(f"{admin_name}", use_container_width=True):
            st.markdown(f"**<i class='fa-solid fa-user-shield' style='color:#FF4B4B;'></i> Quản trị:**<br><span style='color:#e0e0e0;'>{admin_name}</span>", unsafe_allow_html=True)
            st.divider()
            if st.button("Đăng xuất", use_container_width=True, type="primary"):
                st.session_state.clear()
                st.query_params.clear()
                st.rerun()

    if logo_head_b64:
        logo_html = f'<img src="data:image/webp;base64,{logo_head_b64}" style="width: 45px; margin-right: 12px; z-index: 2; position: relative;">'
    else:
        logo_html = '<i class="fa-solid fa-truck-fast" style="font-size: 30px; margin-right: 12px; color: white; z-index: 2; position: relative;"></i>'

    with st.sidebar:
        st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                {logo_html}
                <h3 style='color: white; margin: 0; font-weight: bold;'>BẢNG QUẢN TRỊ</h3>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("LÀM MỚI DỮ LIỆU", use_container_width=True):
            clear_admin_caches()
            st.rerun()
            
        st.markdown("<hr style='margin: 10px 0; border-color: #333;'>", unsafe_allow_html=True)
        
        menu_selection = st.radio("Điều hướng", ["Bản đồ Điều phối", "Quản lý Đơn hàng", "Quản lý Hỏa tốc (COD)", "Lịch sử Đơn hàng", "Bảng Xếp Hạng", "Hệ thống Tài khoản"], label_visibility="collapsed")
        
        st.markdown("<div style='flex-grow: 1; height: 35vh;'></div>", unsafe_allow_html=True)
        st.markdown(f"""
            <div style="text-align: center; padding: 20px 0; border-top: 1px solid #333; margin-top: auto;">
                <img src="data:image/webp;base64,{bg_img_b64}" style="width: 140px; opacity: 0.15; filter: grayscale(100%); transition: all 0.3s ease;">
                <p style="color: #8b949e; font-size: 13px; margin-top: 15px; font-weight: bold; letter-spacing: 1px;">UMBRELLA LOGISTICS</p>
                <p style="color: #444; font-size: 11px; margin-top: -10px;">Vinh City Supply Chain © 2026</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:-50px;'></div>", unsafe_allow_html=True)

    if menu_selection == "Bản đồ Điều phối":
        df_users = get_all_users()
        wh_loc = get_warehouse_loc()
        active_points = get_active_points()
        active_points_count = get_active_points_count()

        st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 20px; z-index: 2; position: relative;">
                <i class="fa-solid fa-map-location-dot" style="font-size: 38px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
                <h1 style="margin: 0; font-size: 40px; font-weight: 700; color: white;">BẢNG ĐIỀU KHIỂN ĐIỀU PHỐI</h1>
            </div>
        """, unsafe_allow_html=True)

        if pending_standard > 0:
            st.markdown(f"""
                <div style="background-color: rgba(255, 204, 0, 0.15); border-left: 4px solid #ffcc00; padding: 12px 20px; border-radius: 5px; margin-bottom: 10px;">
                    <span style="color: #ffcc00; font-weight: bold; font-size: 15px;">
                        <i class="fa-solid fa-bell"></i> CÓ {pending_standard} YÊU CẦU ĐƠN CHUỖI ĐANG CHỜ XÁC NHẬN. VUI LÒNG CHUYỂN SANG TAB QUẢN LÝ ĐƠN HÀNG!
                    </span>
                </div>
            """, unsafe_allow_html=True)
            
        if pending_cod > 0:
            st.markdown(f"""
                <div style="background-color: rgba(25, 118, 210, 0.15); border-left: 4px solid #1976D2; padding: 12px 20px; border-radius: 5px; margin-bottom: 20px;">
                    <span style="color: #1976D2; font-weight: bold; font-size: 15px;">
                        <i class="fa-solid fa-truck-fast"></i> CÓ {pending_cod} YÊU CẦU HỎA TỐC (COD) ĐANG CHỜ XÁC NHẬN. VUI LÒNG CHUYỂN SANG TAB QUẢN LÝ HỎA TỐC!
                    </span>
                </div>
            """, unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Đơn chờ gom", active_points_count)
        c2.metric("Tài xế Online", len(df_users[(df_users['role'] == '2') & (df_users['current_status'] != "Ngoại tuyến")]))
        c3.metric("Tài khoản bị khóa", len(df_users[df_users['is_locked'] == 1]))
        c4.metric("Khu vực quản lý", "TP Vinh - Nghệ An")
        st.divider()

        col_map, col_list = st.columns([2.5, 1.2])

        with col_map:
            st.subheader("Bản đồ giám sát trực tuyến")
            m_admin = folium.Map(location=wh_loc, zoom_start=14, tiles="cartodbpositron")
            folium.Marker(location=wh_loc, icon=folium.DivIcon(html=f'<div style="color:white; background:#FF4B4B; border-radius:50%; width:35px; height:35px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5);">KHO</div>')).add_to(m_admin)
            order_cluster = MarkerCluster(name="Đơn hàng chờ gom").add_to(m_admin)
            
            for _, pt in active_points.iterrows():
                gmap_link = f"https://www.google.com/maps?q={pt['lat']},{pt['lon']}"
                create_time = pt['created_at'].strftime("%H:%M %d/%m/%Y") if isinstance(pt['created_at'], datetime) else str(pt['created_at'])
                popup_html = f"""<div style="width:200px; color:black; font-family:sans-serif;"><b style="color:#D32F2F;"><i class="fa-solid fa-location-dot"></i> ĐƠN HÀNG PHÁT SINH</b><br><hr style='margin:5px 0'><b>Mã đơn:</b> #{pt['point_id']}<br><b>Người tạo:</b> {pt['created_by']}<br><b>Thời gian:</b> {create_time}<br><a href='{gmap_link}' target='_blank' style='color:#1976D2; font-weight:bold; text-decoration:none;'><i class="fa-solid fa-link"></i> Xem Google Maps</a></div>"""
                
                if pt.get('delivery_status', '') == 'Đang chờ duyệt':
                    folium.Marker(location=[pt['lat'], pt['lon']], icon=folium.Icon(color="orange", icon="check", prefix="fa"), tooltip="Đơn chờ duyệt hoàn thành", popup=folium.Popup(popup_html, max_width=250)).add_to(order_cluster)
                else:
                    folium.Marker(location=[pt['lat'], pt['lon']], icon=folium.Icon(color="red", icon="info-sign"), tooltip="Đơn hàng chờ gom", popup=folium.Popup(popup_html, max_width=250)).add_to(order_cluster)
            
            active_drivers = df_users[(df_users['role'] == '2') & (df_users['current_status'] != 'Ngoại tuyến') & (df_users['lat'].notna())]
            for _, driver in active_drivers.iterrows():
                folium.Marker(location=[driver['lat'], driver['lon']], icon=folium.Icon(color="green" if driver['current_status'] == "Sẵn sàng" else "orange", icon="truck", prefix="fa"), tooltip=f"{driver['fullname']}").add_to(m_admin)

            if 'temp_admin_click' in st.session_state:
                t_lat, t_lon = st.session_state.temp_admin_click
                folium.Marker(
                    location=[t_lat, t_lon],
                    icon=folium.DivIcon(html=f'<div style="color:white; background:#1976D2; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:3px solid white; box-shadow: 0 0 15px #1976D2; font-size: 10px;">MỚI</div>'),
                    tooltip="Vị trí bạn vừa chọn"
                ).add_to(m_admin)

            map_data = st_folium(m_admin, width="100%", height=500, key="admin_folium_map", returned_objects=["last_clicked"])

            if map_data and map_data.get("last_clicked"):
                new_click = (map_data['last_clicked']['lat'], map_data['last_clicked']['lng'])
                if st.session_state.get('temp_admin_click') != new_click:
                    st.session_state.temp_admin_click = new_click
                    st.rerun()

            with st.popover("Sửa vị trí Kho", use_container_width=True):
                t1, t2 = st.tabs(["Nhập địa chỉ", "Chọn trên Map"])
                with t1:
                    wh_pick = address_form(key="addr_admin_warehouse",
                                            button_label="Lưu vị trí Kho")
                    if wh_pick:
                        try:
                            conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                            cursor.execute("UPDATE WarehouseConfig SET lat=?, lon=? WHERE id=1",
                                            (wh_pick["lat"], wh_pick["lon"]))
                            conn.commit(); conn.close()
                            clear_admin_caches()
                            st.success(f"Đã đổi Kho: {wh_pick['label']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Lỗi cập nhật kho: {e}")
                with t2:
                    if 'temp_admin_click' in st.session_state:
                        st.info(f"📍 Tọa độ chọn: {st.session_state.temp_admin_click[0]:.5f}, {st.session_state.temp_admin_click[1]:.5f}")
                        if st.button("Xác nhận đổi Kho tại đây"):
                            conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                            cursor.execute("UPDATE WarehouseConfig SET lat=?, lon=? WHERE id=1", (st.session_state.temp_admin_click[0], st.session_state.temp_admin_click[1]))
                            conn.commit(); conn.close()
                            del st.session_state.temp_admin_click
                            clear_admin_caches(); st.rerun()
                    else:
                        st.warning("Hãy click vào bản đồ để chọn vị trí.")

        with col_list:
            st.subheader("Quản lý Đơn hàng")
            with st.container(border=True):
                with st.popover("Thêm đơn hàng", use_container_width=True):
                    t3, t4, t5 = st.tabs(["Nhập địa chỉ", "Chọn trên Map", "Tạo đơn mẫu"])
                    with t3:
                        ord_pick = address_form(key="addr_admin_order",
                                                  button_label="Tạo đơn từ địa chỉ")
                        if ord_pick:
                            try:
                                conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                                cursor.execute("INSERT INTO LogisticsPoints (lat, lon, status, created_by, created_at, delivery_status, order_type) VALUES (?,?,?,?, GETDATE(), N'Chờ xác nhận', N'chuỗi')", (ord_pick["lat"], ord_pick["lon"], "Chờ xử lý", current_admin))
                                conn.commit(); conn.close()
                                clear_admin_caches()
                                st.success(f"Đã tạo đơn: {ord_pick['label']}")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Lỗi tạo đơn: {e}")
                    with t4:
                        st.markdown("<p style='font-size:14px; margin-bottom:10px; color:#8b949e;'>Vui lòng chọn trên bản đồ để ghim vị trí.</p>", unsafe_allow_html=True)
                        if 'temp_admin_click' in st.session_state:
                            st.info(f"Ghim tại: {st.session_state.temp_admin_click[0]:.5f}, {st.session_state.temp_admin_click[1]:.5f}")
                            if st.button("Tạo đơn tại điểm vừa bấm"):
                                conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                                cursor.execute("INSERT INTO LogisticsPoints (lat, lon, status, created_by, created_at, delivery_status, order_type) VALUES (?,?,?,?, GETDATE(), N'Chờ xác nhận', N'chuỗi')", (st.session_state.temp_admin_click[0], st.session_state.temp_admin_click[1], "Chờ xử lý", current_admin))
                                conn.commit(); conn.close()
                                del st.session_state.temp_admin_click
                                clear_admin_caches(); st.rerun()
                        else:
                            st.warning("Hãy click vào bản đồ để ghim điểm.")
                    with t5:
                        st.markdown("<p style='font-size:14px; margin-bottom:10px; color:#8b949e;'>Tạo 5 đơn hàng ngẫu nhiên quanh kho.</p>", unsafe_allow_html=True)
                        if st.button("Tạo 5 đơn mẫu", type="primary", use_container_width=True):
                            conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                            base_lat, base_lon = wh_loc[0], wh_loc[1]
                            for _ in range(5):
                                r_lat = base_lat + random.uniform(-0.015, 0.015)
                                r_lon = base_lon + random.uniform(-0.015, 0.015)
                                cursor.execute("INSERT INTO LogisticsPoints (lat, lon, status, created_by, created_at, delivery_status, order_type) VALUES (?,?,?,?, GETDATE(), N'Chờ xác nhận', N'chuỗi')", (r_lat, r_lon, "Chờ xử lý", current_admin))
                            conn.commit(); conn.close()
                            clear_admin_caches(); st.rerun()
                
                if not active_points.empty:
                    st.markdown("<small>Chọn mã đơn cần hủy:</small>", unsafe_allow_html=True)
                    target_del = st.selectbox("Mã đơn", active_points['point_id'].tolist(), label_visibility="collapsed")
                    with st.popover(f"Hủy đơn #{target_del}", use_container_width=True):
                        st.warning(f"Bạn chắc chắn muốn xóa đơn #{target_del}?")
                        if st.button("Có, xóa ngay!", type="primary", use_container_width=True):
                            conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                            cursor.execute("DELETE FROM LogisticsPoints WHERE point_id = ?", (int(target_del),))
                            conn.commit(); conn.close()
                            clear_admin_caches(); st.rerun()
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

    elif menu_selection == "Quản lý Đơn hàng":
        import admin_orders
        admin_orders.render_page()

    elif menu_selection == "Quản lý Hỏa tốc (COD)":
        import admincod
        admincod.render_cod_admin_page()

    elif menu_selection == "Lịch sử Đơn hàng":
        import order_history
        order_history.render_history(st.session_state.customer, str(st.session_state.role))

    elif menu_selection == "Bảng Xếp Hạng":
        import admin_leaderboard
        admin_leaderboard.render_leaderboard()

    elif menu_selection == "Hệ thống Tài khoản":
        import user_profile
        user_profile.render_profile(st.session_state.customer, str(st.session_state.role))
