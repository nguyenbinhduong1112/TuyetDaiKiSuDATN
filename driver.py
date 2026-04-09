import streamlit as st
import torch
import numpy as np
import pandas as pd
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
from model import PointerNet
from map_utils import MapManager
from engine import solve_delivery_route
import os
import urllib.parse
import base64
import math
import random
import pyodbc
from config import CONN_STR

# --- CÁC HÀM XỬ LÝ LOGIC & CACHE (ĐƠN CHUỖI) ---
def calculate_route_distance(locations, route_indices):
    if not route_indices or len(route_indices) < 2: return 0.0
    R, total_dist = 6371.0, 0.0
    full_route = route_indices + [route_indices[0]]
    for i in range(len(full_route) - 1):
        p1, p2 = locations[full_route[i]], locations[full_route[i+1]]
        lat1, lon1, lat2, lon2 = map(math.radians, [p1[0], p1[1], p2[0], p2[1]])
        a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
        total_dist += R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
    return total_dist * 1.3

@st.cache_data
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f: return base64.b64encode(f.read()).decode()
    except Exception: return ""

@st.cache_data(ttl=30)
def fetch_real_data():
    try:
        conn = pyodbc.connect(CONN_STR)
        df_kho = pd.read_sql("SELECT lat, lon FROM WarehouseConfig WHERE id = 1", conn)
        kho = [df_kho.iloc[0]['lat'], df_kho.iloc[0]['lon']] if not df_kho.empty else [18.6601, 105.6942]
        df_pts = pd.read_sql("SELECT lat, lon FROM LogisticsPoints WHERE status = N'Chờ xử lý' AND order_type = N'chuỗi'", conn)
        conn.close()
        return np.array([kho] + df_pts.values.tolist()), len(df_pts)
    except: return np.array([[18.6601, 105.6942]]), 0

@st.cache_data(ttl=15)
def get_pending_count():
    try:
        conn = pyodbc.connect(CONN_STR)
        count = pd.read_sql("SELECT COUNT(*) FROM LogisticsPoints WHERE delivery_status = N'Đang chờ duyệt'", conn).iloc[0,0]
        conn.close()
        return count
    except: return 0

@st.cache_resource
def load_all():
    model = PointerNet()
    if os.path.exists('weights.pth'): model.load_state_dict(torch.load('weights.pth', map_location='cpu'))
    model.eval()
    return model, MapManager()

@st.cache_data(ttl=300)
def get_driver_fullname(username):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        cursor.execute("SELECT fullname FROM userstable WHERE username = ?", (username,))
        row = cursor.fetchone(); conn.close()
        return row[0] if row and row[0] else username
    except: return username

def get_driver_info_from_db(username):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        cursor.execute("SELECT current_status, lat, lon FROM userstable WHERE username = ?", (username,))
        row = cursor.fetchone(); conn.close()
        if row:
            status = row[0] if row[0] else "Ngoại tuyến"
            loc = [row[1], row[2]] if row[1] is not None and row[2] is not None else None
            return status, loc
        return "Ngoại tuyến", None
    except: return "Ngoại tuyến", None

def update_location(status, lat, lon):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        current_user = st.session_state.get("customer")
        cursor.execute("UPDATE userstable SET current_status = ?, lat = ?, lon = ? WHERE username = ?", (status, lat, lon, current_user))
        conn.commit(); conn.close()
        return True
    except: return False

# ==========================================
# HÀM RENDER ĐƯỢC GỌI TỪ MAIN.PY
# ==========================================
def render_page():
    gmaps_hover_b64 = get_base64_of_bin_file(os.path.join("img", "Google-Maps-PNG-Free-Download.png"))
    bg_img_b64 = get_base64_of_bin_file(os.path.join("img", "E2449DA3-F2EB-430A-A588-2F9E9C6C2961.png"))
    logo_head_b64 = get_base64_of_bin_file(os.path.join("img", "19180C31-3EB3-48C4-92C8-7CD1BC52F90C (1).png"))

    # [CẬP NHẬT CSS]: Thêm icon Lịch sử \f1da vào vị trí số 4, Cá nhân xuống vị trí 5
    st.markdown(f"""<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"><style>.stApp {{ background-color: #0E1117; color: white; }}[data-testid="stSidebar"] {{ background-color: #1A1C24; border-right: 1px solid #333; padding-top: 1rem; display: flex; flex-direction: column; justify-content: space-between; }}div[data-testid="metric-container"] {{ background-color: #1A1C24; padding: 15px; border-radius: 10px; border: 1px solid #333; z-index: 2; position: relative; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] {{ gap: 8px; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] {{ background-color: transparent; border-radius: 8px; padding: 12px 15px; cursor: pointer; transition: all 0.2s ease-in-out; border-left: 4px solid transparent; margin-bottom: 2px; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child {{ display: none !important; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover {{ background-color: #21262d; transform: translateX(4px); }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) {{ background-color: #21262d; border-left: 4px solid #FF4B4B; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] p {{ color: #8b949e !important; font-weight: 500; font-size: 16px; margin: 0; display: flex; align-items: center; gap: 12px; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) p {{ color: white !important; font-weight: 700; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(1) p::before {{ content: '\\f468'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(2) p::before {{ content: '\\f466'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(3) p::before {{ content: '\\f5a0'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(4) p::before {{ content: '\\f1da'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [role="radiogroup"] > label:nth-child(5) p::before {{ content: '\\f2c2'; font-family: 'Font Awesome 6 Free'; font-weight: 900; width: 22px; text-align: center; color: inherit; transition: 0.3s; }}[data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:hover p::before, [data-testid="stSidebar"] .stRadio [data-baseweb="radio"]:has(input:checked) p::before {{ color: #FF4B4B !important; }}.gmaps-btn {{ position: relative; display: flex; align-items: center; justify-content: center; background-color: #FF4B4B !important; color: white !important; padding: 0.7rem 1rem; border-radius: 8px; text-decoration: none !important; font-weight: 700; font-size: 18px; border: 1px solid #FF4B4B !important; transition: all 0.3s ease-in-out; width: 100%; box-sizing: border-box; overflow: hidden; }}.gmaps-btn::before {{ content: ""; position: absolute; top: 0; left: -100%; width: 100%; height: 100%; background-image: url('data:image/png;base64,{gmaps_hover_b64}'); background-size: 40px; background-repeat: no-repeat; background-position: 20px center; transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1); z-index: 1; opacity: 0; }}.gmaps-btn:hover {{ background-color: #FF7575 !important; border-color: #FF7575 !important; }}.gmaps-btn:hover::before {{ left: 0; opacity: 0.6; }}.btn-text-content {{ position: relative; z-index: 2; display: flex; align-items: center; gap: 8px; }}button[kind="primary"] {{ background-color: #FF4B4B !important; border-color: #FF4B4B !important; transition: all 0.3s ease-in-out !important; }}button[kind="primary"]:hover {{ background-color: #FF7575 !important; border-color: #FF7575 !important; color: white !important; }}.qr-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.85); z-index: 999999; justify-content: center; align-items: center; backdrop-filter: blur(5px); }}#qr-toggle:checked ~ .qr-overlay {{ display: flex !important; }}.qr-popup {{ background: white; padding: 20px; border-radius: 15px; position: relative; text-align: center; box-shadow: 0 0 30px rgba(0,0,0,0.8); }}.close-btn {{ position: absolute; top: -15px; right: -15px; background: #FF4B4B; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; justify-content: center; align-items: center; cursor: pointer; font-size: 24px; font-weight: bold; border: 3px solid white; transition: 0.3s; }}.open-btn {{ display: block; background: #262730; color: white; text-align: center; border-radius: 6px; cursor: pointer; font-weight: bold; border: 1px solid #444; transition: 0.3s; }}.open-btn:hover {{ background: #3a3d4a; border-color: #666; }}.bg-watermark {{ position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 700px; height: 700px; background-image: url('data:image/png;base64,{bg_img_b64}'); background-size: contain; background-position: center; background-repeat: no-repeat; opacity: 0.15; z-index: 0; pointer-events: none; }}</style><div class="bg-watermark"></div>""", unsafe_allow_html=True)

    if "customer" not in st.session_state or str(st.session_state.get("role", "")) != "2":
        st.warning("Vui lòng đăng nhập bằng tài khoản Tài xế!")
        st.stop()

    if 'locations' not in st.session_state: st.session_state.locations, _ = fetch_real_data()
    if 'route_indices' not in st.session_state: st.session_state.route_indices = None
    if 'actual_path' not in st.session_state: st.session_state.actual_path = None
    if 'map_refresh_key' not in st.session_state: st.session_state.map_refresh_key = 0

    if 'driver_status' not in st.session_state or 'driver_loc' not in st.session_state:
        db_status, db_loc = get_driver_info_from_db(st.session_state.customer)
        st.session_state.driver_status = db_status
        st.session_state.driver_loc = db_loc

    model, map_mgr = load_all()
    driver_user = st.session_state.customer
    driver_fullname = get_driver_fullname(driver_user)

    col_space, col_user = st.columns([8.5, 1.5])
    with col_user:
        with st.popover(f"{driver_fullname}", use_container_width=True):
            st.markdown(f"**<i class='fa-solid fa-id-badge' style='color:#FF4B4B;'></i> Tài xế:**<br><span style='color:#e0e0e0;'>{driver_fullname}</span>", unsafe_allow_html=True)
            try:
                current_index = ["Sẵn sàng", "Đang giao hàng", "Ngoại tuyến"].index(st.session_state.driver_status)
            except ValueError:
                current_index = 2
            new_status = st.selectbox("Tình trạng:", ["Sẵn sàng", "Đang giao hàng", "Ngoại tuyến"], index=current_index)
            if st.button("Cập nhật vị trí", use_container_width=True):
                st.session_state.driver_status = new_status
                if new_status != "Ngoại tuyến":
                    if st.session_state.driver_loc is None:
                        lat, lon = 18.6733 + random.uniform(-0.01, 0.01), 105.6813 + random.uniform(-0.01, 0.01)
                        st.session_state.driver_loc = [lat, lon]
                    else:
                        lat, lon = st.session_state.driver_loc[0], st.session_state.driver_loc[1]
                    update_location(new_status, lat, lon)
                    st.session_state.map_refresh_key += 1
                    st.success("Đã cập nhật trạng thái!")
                else:
                    st.session_state.driver_loc = None
                    update_location(new_status, None, None)
                    st.session_state.map_refresh_key += 1
                    st.warning("Đã tắt định vị.")
                st.rerun()
            st.divider()
            
            # [CHỈ FIX ĐÚNG ĐOẠN NÀY]
            if st.button("Đăng xuất", use_container_width=True, type="primary"):
                st.session_state.clear()
                st.query_params.clear()
                st.rerun()

    if logo_head_b64:
        logo_sidebar_html = f'<img src="data:image/png;base64,{logo_head_b64}" style="width: 45px; margin-right: 12px; z-index: 2; position: relative;">'
    else:
        logo_sidebar_html = '<i class="fa-solid fa-truck-fast" style="font-size: 30px; margin-right: 12px; color: white; z-index: 2; position: relative;"></i>'

    with st.sidebar:
        st.markdown(f"<div style='display: flex; align-items: center; margin-bottom: 20px;'>{logo_sidebar_html}<h3 style='color: white; margin: 0; font-weight: bold;'>QUẢN LÝ CÔNG VIỆC</h3></div>", unsafe_allow_html=True)
        menu_selection = st.radio("Điều hướng", ["Đơn hàng chuỗi", "Đơn hàng lẻ", "Tình trạng giao thông", "Lịch sử đơn hàng", "Quản lý thông tin cá nhân"], label_visibility="collapsed")
        st.markdown("<div style='flex-grow: 1; height: 35vh;'></div>", unsafe_allow_html=True)
        st.markdown(f"""<div style="text-align: center; padding: 20px 0; border-top: 1px solid #333; margin-top: auto;"><img src="data:image/png;base64,{bg_img_b64}" style="width: 140px; opacity: 0.15; filter: grayscale(100%);"><p style="color: #8b949e; font-size: 13px; margin-top: 15px; font-weight: bold; letter-spacing: 1px;">UMBRELLA DRIVER APP</p><p style="color: #444; font-size: 11px; margin-top: -10px;">Vinh City Supply Chain © 2026</p></div>""", unsafe_allow_html=True)

    st.markdown("<div style='margin-top:-50px;'></div>", unsafe_allow_html=True)

    if menu_selection == "Đơn hàng chuỗi":
        st.markdown(f"""
            <div style="display: flex; align-items: center; margin-bottom: 10px; z-index: 2; position: relative;">
                <i class="fa-solid fa-truck-fast" style="font-size: 42px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
                <h1 style="margin: 0; font-size: 45px; font-weight: 700; color: white;">Hệ thống vận hành tài xế</h1>
            </div>
            <hr style="margin-top: 5px; border-color: #333; z-index: 2; position: relative;">
        """, unsafe_allow_html=True)

        col_map, col_ctrl = st.columns([3, 1])
        with col_ctrl:
            st.markdown("### <i class='fa-solid fa-gauge-high' style='color:#FF4B4B;'></i> Trạng thái vận hành", unsafe_allow_html=True)
            st.markdown("""<div style="background-color: rgba(40, 167, 69, 0.15); border-left: 4px solid #28a745; padding: 12px 15px; border-radius: 5px; margin-bottom: 15px;"><span style="color: #28a745; font-weight: bold; font-size: 14px;"><i class="fa-solid fa-wifi"></i> Đã kết nối tới hệ thống đơn hàng</span></div>""", unsafe_allow_html=True)
            st.write("---")
            
            if st.button("Đồng bộ đơn hàng mới", use_container_width=True):
                fetch_real_data.clear() 
                st.session_state.locations, n_orders = fetch_real_data()
                st.session_state.route_indices, st.session_state.actual_path = None, None
                st.rerun()

            pending_count = get_pending_count() 

            if pending_count > 0: st.button("Đang chờ Admin duyệt...", disabled=True, use_container_width=True)
            elif len(st.session_state.locations) <= 1: st.button("Đã hoàn thành tất cả", disabled=True, use_container_width=True)
            else:
                if st.button("Xác nhận đã hoàn thành đơn", use_container_width=True, type="primary"):
                    try:
                        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
                        cursor.execute("UPDATE LogisticsPoints SET delivery_status = N'Đang chờ duyệt' WHERE status = N'Chờ xử lý' AND order_type = N'chuỗi'")
                        conn.commit(); conn.close()
                        get_pending_count.clear() 
                        st.success("Đã gửi yêu cầu lên Admin!"); st.rerun()
                    except Exception: st.error("Lỗi cập nhật!")

            st.write("---")
            if len(st.session_state.locations) < 2:
                st.markdown("""<div style="background-color: rgba(255, 204, 0, 0.15); border-left: 4px solid #ffcc00; padding: 12px 15px; border-radius: 5px; margin-bottom: 15px;"><span style="color: #ffcc00; font-weight: bold; font-size: 14px;"><i class="fa-solid fa-folder-open"></i> Không có đơn hàng chờ xử lý.</span></div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""<div style="margin-bottom: 10px;"><span style="color: #e0e0e0; font-size: 15px;"><i class="fa-solid fa-box-open" style="color:#FF4B4B;"></i> Đơn hàng hiện tại: <b style="color: white;">{len(st.session_state.locations) - 1}</b></span></div>""", unsafe_allow_html=True)
                if st.button("Kích hoạt tối ưu lộ trình AI", type="primary", use_container_width=True):
                    with st.status("AI đang xử lý...", expanded=False):
                        coords_tensor = torch.FloatTensor(st.session_state.locations)
                        st.session_state.route_indices = solve_delivery_route(model, coords_tensor)
                        node_ids = map_mgr.get_nearest_nodes(st.session_state.locations)
                        ordered_nodes = [node_ids[i] for i in st.session_state.route_indices]
                        st.session_state.actual_path = map_mgr.get_route_coords(ordered_nodes)
                    st.rerun()

        with col_map:
            center = st.session_state.locations[0].tolist()
            m = folium.Map(location=center, zoom_start=14, tiles="cartodbpositron")
            for i, p in enumerate(st.session_state.locations):
                color = "#FF4B4B" if i == 0 else ("#1E90FF" if st.session_state.route_indices else "#555555")
                label = "KHO" if i == 0 else (f"{st.session_state.route_indices.index(i)}" if st.session_state.route_indices else "?")
                folium.Marker(location=[p[0], p[1]], icon=folium.DivIcon(html=f'<div style="color:white; background:{color}; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5); font-size: 13px;">{label}</div>')).add_to(m)
            
            if st.session_state.route_indices and len(st.session_state.route_indices) > 1:
                ordered_pts = [st.session_state.locations[i].tolist() for i in st.session_state.route_indices]
                ordered_pts.append(st.session_state.locations[st.session_state.route_indices[0]].tolist()) 
                AntPath(locations=ordered_pts, color="#1976D2", weight=4, dash_array=[15, 20], delay=800, tooltip="Vector Tuyến Giao Hàng").add_to(m)

            if st.session_state.actual_path: 
                folium.PolyLine(locations=st.session_state.actual_path, color="#FF0000", weight=6, opacity=0.8).add_to(m)
            
            if st.session_state.driver_loc and st.session_state.driver_status != "Ngoại tuyến":
                folium.Marker(location=st.session_state.driver_loc, icon=folium.Icon(color="green", icon="truck", prefix="fa"), tooltip=f"Tài xế: {driver_fullname}").add_to(m)
            st_folium(m, width="100%", height=550, key=f"driver_map_stable", returned_objects=[])

        if st.session_state.route_indices and len(st.session_state.route_indices) > 1:
            st.markdown("### <i class='fa-solid fa-route' style='color:#FF4B4B;'></i> Kết quả tối ưu lộ trình:", unsafe_allow_html=True)
            col_info, col_qr = st.columns([2.8, 1.2], gap="large") 
            kho_loc = st.session_state.locations[st.session_state.route_indices[0]]
            pts_list = [f"{st.session_state.locations[i][0]},{st.session_state.locations[i][1]}" for i in st.session_state.route_indices[1:]]
            pts_str = "/".join(pts_list)
            gmaps_url = f"https://www.google.com/maps/dir/Current+Location/{kho_loc[0]},{kho_loc[1]}/{pts_str}/"
            with col_info:
                m1, m2, m3 = st.columns([1.2, 1, 1])
                dist = calculate_route_distance(st.session_state.locations, st.session_state.route_indices)
                m1.metric("Trạng thái", "Thành công")
                m2.metric("Quãng đường", f"{dist:.2f} km")
                m3.metric("Số điểm giao", f"{len(st.session_state.locations) - 1} điểm")
                st.markdown("<hr style='margin: 20px 0; border-color: #333;'>", unsafe_allow_html=True)
                st.markdown(f'<a href="{gmaps_url}" target="_blank" class="gmaps-btn"><span class="btn-text-content"><i class="fa-solid fa-map-location-dot"></i> MỞ GOOGLE MAPS DẪN ĐƯỜNG</span></a>', unsafe_allow_html=True)
            with col_qr:
                qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={urllib.parse.quote(gmaps_url)}"
                st.markdown(f"""<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; background-color: #1A1C24; padding: 20px; border-radius: 10px; border: 1px solid #333;"><div style="color: #e0e0e0; font-size: 15px; font-weight: bold; margin-bottom: 12px;"><i class="fa-solid fa-qrcode" style="color:#FF4B4B;"></i> QR Google Maps App</div><img src="{qr_url}" style="width: 150px; border-radius: 8px; border: 3px solid white; margin-bottom: 15px;"><input type="checkbox" id="qr-toggle" style="display: none;"><label for="qr-toggle" class="open-btn" style="margin: 0; width: 150px; font-size: 14px; padding: 10px 5px;"> Phóng to QR</label><div class="qr-overlay"><div class="qr-popup"><label for="qr-toggle" class="close-btn">×</label><img src="{qr_url}" style="width: 65vh; max-width: 600px; border-radius: 10px; border: 2px solid #333;"><h3 style="color: black; margin-top: 15px; font-weight: bold;"><i class="fa-solid fa-mobile-screen-button"></i> Quét mã mở Google Maps</h3></div></div></div>""", unsafe_allow_html=True)

    elif menu_selection == "Đơn hàng lẻ":
        import drivecod
        drivecod.render_cod_page(driver_fullname)

    elif menu_selection == "Tình trạng giao thông":
        import drivertraffic
        drivertraffic.render_page()

    elif menu_selection == "Lịch sử đơn hàng":
        import order_history
        order_history.render_history(st.session_state.customer, str(st.session_state.role))

    elif menu_selection == "Quản lý thông tin cá nhân":
        import user_profile
        user_profile.render_profile(st.session_state.customer, str(st.session_state.role))