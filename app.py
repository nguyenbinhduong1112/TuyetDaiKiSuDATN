import streamlit as st
import torch
import numpy as np
import folium
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

# ==========================================
# CẤU HÌNH KẾT NỐI SQL SERVER
# ==========================================
SERVER_NAME = 'DESKTOP-U4FQD35' 
DATABASE_NAME = 'LogisticsDB'
CONN_STR = f"Driver={{SQL Server}};Server={SERVER_NAME};Database={DATABASE_NAME};Trusted_Connection=yes;"

# --- HÀM TÍNH KHOẢNG CÁCH CHUẨN (HAVERSINE) ---
def calculate_route_distance(locations, route_indices):
    if not route_indices or len(route_indices) < 2:
        return 0.0
    R = 6371.0 
    total_dist = 0.0
    full_route = route_indices + [route_indices[0]]
    for i in range(len(full_route) - 1):
        p1 = locations[full_route[i]]
        p2 = locations[full_route[i+1]]
        lat1, lon1 = math.radians(p1[0]), math.radians(p1[1])
        lat2, lon2 = math.radians(p2[0]), math.radians(p2[1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        total_dist += R * c
    return total_dist * 1.3

# --- HÀM HỖ TRỢ ĐỌC ẢNH SANG BASE64 ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""

# --- 1. THIẾT LẬP GIAO DIỆN VÀ LOGO CHÌM ---
st.set_page_config(layout="wide", page_title="Tài xế - Umbrella Logistics", page_icon=r"D:\datn\img\4D5185D2-0AD7-49AC-B7B2-4E94C13DB13C.png")

# Lấy ảnh cho hiệu ứng trượt nút Maps và Logo chìm
gmaps_hover_b64 = get_base64_of_bin_file(r"D:\datn\img\Google-Maps-PNG-Free-Download.png")
bg_img_b64 = get_base64_of_bin_file(r"D:\datn\img\E2449DA3-F2EB-430A-A588-2F9E9C6C2961.png")

# SỬ DỤNG DOUBLE BRACKETS {{ }} ĐỂ TRÁNH LỖI F-STRING
st.markdown(f"""
    <style>
    .stApp {{ background-color: #0E1117; color: white; }}
    [data-testid="stSidebar"] {{ background-color: #1A1C24; }}
    div[data-testid="metric-container"] {{ 
        background-color: #1A1C24; padding: 15px; 
        border-radius: 10px; border: 1px solid #333; 
        z-index: 2; position: relative;
    }}
    [data-testid="stImage"] {{ display: flex; justify-content: center; }}
    div.row-widget.stRadio > div {{ flex-direction:row; background: #1A1C24; padding: 10px; border-radius: 8px; z-index: 2; position: relative;}}
    
    /* CSS CHO NÚT GOOGLE MAPS CÓ HOVER PNG TRƯỢT NGANG */
    .gmaps-btn {{
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #FF4B4B !important;
        color: white !important;
        padding: 0.7rem 1rem;
        border-radius: 8px;
        text-decoration: none !important;
        font-weight: 700;
        font-size: 18px;
        border: 1px solid #FF4B4B !important;
        transition: all 0.3s ease-in-out;
        width: 100%;
        box-sizing: border-box;
        overflow: hidden;
    }}
    
    .gmaps-btn::before {{
        content: "";
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background-image: url('data:image/png;base64,{gmaps_hover_b64}');
        background-size: 40px;
        background-repeat: no-repeat;
        background-position: 20px center;
        transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
        z-index: 1;
        opacity: 0;
    }}

    .gmaps-btn:hover {{
        background-color: #FF7575 !important;
        border-color: #FF7575 !important;
    }}
    
    .gmaps-btn:hover::before {{
        left: 0;
        opacity: 0.6;
    }}

    .btn-text-content {{
        position: relative;
        z-index: 2;
    }}

    button[kind="primary"] {{
        background-color: #FF4B4B !important;
        border-color: #FF4B4B !important;
        transition: all 0.3s ease-in-out !important;
    }}
    button[kind="primary"]:hover {{
        background-color: #FF7575 !important;
        border-color: #FF7575 !important;
        color: white !important;
    }}

    .qr-overlay {{
        display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: rgba(0,0,0,0.85); z-index: 999999; 
        justify-content: center; align-items: center; backdrop-filter: blur(5px);
    }}
    #qr-toggle:checked ~ .qr-overlay {{ display: flex !important; }}
    
    .qr-popup {{
        background: white; padding: 20px; border-radius: 15px; 
        position: relative; text-align: center; box-shadow: 0 0 30px rgba(0,0,0,0.8);
    }}
    
    .close-btn {{
        position: absolute; top: -15px; right: -15px; background: #FF4B4B; 
        color: white; width: 40px; height: 40px; border-radius: 50%; 
        display: flex; justify-content: center; align-items: center; cursor: pointer; 
        font-size: 24px; font-weight: bold; border: 3px solid white; transition: 0.3s;
    }}
    
    .open-btn {{
        display: block; background: #262730; color: white; text-align: center;
        border-radius: 6px; cursor: pointer; font-weight: bold; 
        border: 1px solid #444; transition: 0.3s; 
    }}
    .open-btn:hover {{ background: #3a3d4a; border-color: #666; }}

    /* WATERMARK CSS */
    .bg-watermark {{
        position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
        width: 700px; height: 700px;
        background-image: url('data:image/png;base64,{bg_img_b64}');
        background-size: contain; background-position: center; background-repeat: no-repeat;
        opacity: 0.25; z-index: 0; pointer-events: none;
    }}
    </style>
    <div class="bg-watermark"></div>
    """, unsafe_allow_html=True)

# Khởi tạo dữ liệu
if 'locations' not in st.session_state:
    base_kho = [18.6601, 105.6942] 
    st.session_state.locations = np.zeros((6, 2))
    st.session_state.locations[0] = base_kho
    st.session_state.locations[1:] = base_kho + np.random.uniform(-0.01, 0.01, (5, 2))

if 'route_indices' not in st.session_state: st.session_state.route_indices = None
if 'actual_path' not in st.session_state: st.session_state.actual_path = None
if 'last_added_click' not in st.session_state: st.session_state.last_added_click = None

# --- KHỞI TẠO BIẾN CHO TÀI XẾ ---
if 'driver_loc' not in st.session_state: st.session_state.driver_loc = None
if 'driver_status' not in st.session_state: st.session_state.driver_status = "Ngoại tuyến"
if 'map_refresh_key' not in st.session_state: st.session_state.map_refresh_key = 0

@st.cache_resource
def load_all():
    model = PointerNet()
    if os.path.exists('weights.pth'):
        model.load_state_dict(torch.load('weights.pth', map_location='cpu'))
    model.eval()
    return model, MapManager()

model, map_mgr = load_all()

# --- HÀM LẤY TÊN THẬT TÀI XẾ TỪ DATABASE ---
def get_driver_fullname(username):
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("SELECT fullname FROM userstable WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row and row[0] else username
    except: return username

# --- HÀM CẬP NHẬT DATABASE NGẦM ---
def update_location(status, lat, lon):
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE userstable 
            SET current_status = ?, lat = ?, lon = ? 
            WHERE username = ?
        """, (status, lat, lon, st.session_state.username))
        conn.commit()
        conn.close()
        return True
    except: return False

# --- BỔ SUNG: DROPDOWN ĐĂNG XUẤT ĐÃ ĐỒNG BỘ LOGIN VÀ DATABASE ---
# Xử lý trường hợp vào thẳng file app.py không qua login
if "username" not in st.session_state or st.session_state.username is None: 
    st.session_state.username = "Khách vãng lai"

# Lấy tên hiển thị
driver_fullname = get_driver_fullname(st.session_state.username)

col_space, col_user = st.columns([8.5, 1.5])
with col_user:
    with st.popover(f"👤 {driver_fullname}", use_container_width=True):
        st.markdown(f"Tài xế: **{driver_fullname}**")
        
        new_status = st.selectbox(
            "Tình trạng:", 
            ["Sẵn sàng", "Đang giao hàng", "Ngoại tuyến"],
            index=["Sẵn sàng", "Đang giao hàng", "Ngoại tuyến"].index(st.session_state.driver_status)
        )
        
        if st.button("📍 Cập nhật vị trí", use_container_width=True):
            st.session_state.driver_status = new_status
            if new_status != "Ngoại tuyến":
                # Lấy tọa độ ảo quanh khu vực ĐH Vinh
                lat = 18.6733 + random.uniform(-0.02, 0.02)
                lon = 105.6813 + random.uniform(-0.02, 0.02)
                
                st.session_state.driver_loc = [lat, lon]
                update_location(new_status, lat, lon)
                st.session_state.map_refresh_key += 1 # Ép bản đồ load lại
                st.success("Đã cập nhật định vị!")
            else:
                st.session_state.driver_loc = None
                update_location(new_status, None, None)
                st.session_state.map_refresh_key += 1 # Ép bản đồ load lại
                st.warning("Đã tắt định vị.")
            st.rerun()
            
        st.divider()
        if st.button("🚪 Đăng xuất", use_container_width=True, type="primary"):
            st.session_state.role = None
            st.session_state.username = None
            st.rerun()

# --- 2. HEADER ---
try:
    with open(r"D:\datn\img\19180C31-3EB3-48C4-92C8-7CD1BC52F90C (1).png", "rb") as f:
        logo_head_b64 = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_head_b64}" style="width: 55px; margin-right: 15px; z-index: 2; position: relative;">'
except:
    logo_html = '🚚'

st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 10px; z-index: 2; position: relative;">
        {logo_html}
        <h1 style="margin: 0; font-size: 32px; font-weight: 700; color: white;">Hệ thống Tối ưu tuyến giao hàng AI training bằng DRL</h1>
    </div>
    <hr style="margin-top: 5px; border-color: #333; z-index: 2; position: relative;">
    """, unsafe_allow_html=True)

# --- 3. BỐ CỤC CHÍNH ---
col_map, col_ctrl = st.columns([3, 1])

with col_ctrl:
    st.subheader("Cấu hình hệ thống mô phỏng")
    click_mode = st.radio("Chế độ tương tác bản đồ:", ["📍 Thêm điểm giao", "🏠 Đổi vị trí Kho"])
    st.write("---")
    n_points = st.number_input("Tạo ngẫu nhiên (Số lượng):", min_value=3, max_value=20, value=max(3, len(st.session_state.locations)), step=1)
    
    if st.button("Trải đều ngẫu nhiên", use_container_width=True):
        st.session_state.route_indices = None
        st.session_state.actual_path = None
        current_kho = st.session_state.locations[0]
        st.session_state.locations = np.zeros((n_points, 2))
        st.session_state.locations[0] = current_kho
        st.session_state.locations[1:] = current_kho + np.random.uniform(-0.012, 0.012, (n_points - 1, 2))
        st.rerun()

    if st.button("Xóa hết đơn (Giữ nguyên Kho)", use_container_width=True):
        st.session_state.route_indices = None
        st.session_state.actual_path = None
        st.session_state.locations = np.array([st.session_state.locations[0]]) 
        st.rerun()

    st.write("---")
    if len(st.session_state.locations) < 2:
        st.warning("Hãy click lên bản đồ để thêm đơn hàng!")
    else:
        if st.button("Kích hoạt tối ưu thuật toán DRL", type="primary", use_container_width=True):
            with st.status("Đang xử lý thuật toán Deep RL...", expanded=True) as status:
                coords_tensor = torch.FloatTensor(st.session_state.locations)
                st.session_state.route_indices = solve_delivery_route(model, coords_tensor)
                node_ids = map_mgr.get_nearest_nodes(st.session_state.locations)
                ordered_nodes = [node_ids[i] for i in st.session_state.route_indices]
                st.session_state.actual_path = map_mgr.get_route_coords(ordered_nodes)
                status.update(label="Hoàn tất tối ưu!", state="complete", expanded=False)
            st.rerun()

with col_map:
    # Cố định bản đồ ở vị trí Kho
    m = folium.Map(location=st.session_state.locations[0].tolist(), zoom_start=14, tiles="cartodbpositron")
    
    for i, p in enumerate(st.session_state.locations):
        color = "#FF4B4B" if i == 0 else ("#1E90FF" if st.session_state.route_indices else "#555555")
        label = "KHO" if i == 0 else (f"{st.session_state.route_indices.index(i)}" if st.session_state.route_indices else "?")
        folium.Marker(location=[p[0], p[1]], icon=folium.DivIcon(html=f'<div style="color:white; background:{color}; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5); font-size: 13px;">{label}</div>')).add_to(m)
    
    if st.session_state.actual_path:
        folium.PolyLine(locations=st.session_state.actual_path, color="#FF0000", weight=6, opacity=0.8).add_to(m)
    
    # --- VẼ VỊ TRÍ TÀI XẾ (ICON XE TẢI XANH LÁ) ---
    if st.session_state.driver_loc and st.session_state.driver_status != "Ngoại tuyến":
        folium.Marker(
            location=st.session_state.driver_loc,
            icon=folium.Icon(color="green", icon="truck", prefix="fa"), 
            tooltip=f"Tài xế: {driver_fullname} ({st.session_state.driver_status})"
        ).add_to(m)
    
    # --- ĐIỂM FIX LỖI GIẬT LAG BẢN ĐỒ KHI KÉO THẢ VÀ CẬP NHẬT TRẠNG THÁI ---
    map_data = st_folium(
        m, 
        width="100%", 
        height=550, 
        key=f"vinh_map_interactive_{st.session_state.map_refresh_key}",
        returned_objects=["last_clicked"] 
    )
    
    if map_data and map_data.get("last_clicked"):
        lat, lng = map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"]
        if st.session_state.last_added_click != [lat, lng]:
            st.session_state.last_added_click = [lat, lng]
            if click_mode == "🏠 Đổi vị trí Kho": st.session_state.locations[0] = [lat, lng]
            else: st.session_state.locations = np.vstack((st.session_state.locations, [lat, lng]))
            st.session_state.route_indices, st.session_state.actual_path = None, None
            st.rerun()

# --- 4. THÔNG SỐ & MÃ QR ---
if st.session_state.route_indices and len(st.session_state.route_indices) > 1:
    st.markdown("### Phân tích kết quả tối ưu tuyến giao hàng:", unsafe_allow_html=True)
    col_info, col_qr = st.columns([2.8, 1.2], gap="large") 
    kho_loc = st.session_state.locations[st.session_state.route_indices[0]]
    pts = "/".join([f"{st.session_state.locations[i][0]},{st.session_state.locations[i][1]}" for i in st.session_state.route_indices[1:]])
    gmaps_url = f"https://www.google.com/maps/dir/{kho_loc[0]},{kho_loc[1]}/{pts}/{kho_loc[0]},{kho_loc[1]}"
    
    with col_info:
        m1, m2, m3 = st.columns([1.2, 1, 1])
        dist = calculate_route_distance(st.session_state.locations, st.session_state.route_indices)
        m1.metric("Trạng thái", "✅ Thành công")
        m2.metric("Quãng đường", f"{dist:.2f} km")
        m3.metric("Số điểm giao", f"{len(st.session_state.locations) - 1} điểm")
        st.markdown("<hr style='margin: 20px 0; border-color: #333;'>", unsafe_allow_html=True)
        st.markdown(f'<a href="{gmaps_url}" target="_blank" class="gmaps-btn"><span class="btn-text-content">MỞ BẢN ĐỒ GOOGLE MAPS</span></a>', unsafe_allow_html=True)

    with col_qr:
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={urllib.parse.quote(gmaps_url)}"
        st.markdown(f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; background-color: #1A1C24; padding: 20px; border-radius: 10px; border: 1px solid #333;">
            <div style="color: #e0e0e0; font-size: 15px; font-weight: bold; margin-bottom: 12px;"> QR Google Maps App</div>
            <img src="{qr_url}" style="width: 150px; border-radius: 8px; border: 3px solid white; margin-bottom: 15px;">
            <input type="checkbox" id="qr-toggle" style="display: none;">
            <label for="qr-toggle" class="open-btn" style="margin: 0; width: 150px; font-size: 14px; padding: 10px 5px;"> Phóng to QR</label>
            <div class="qr-overlay"><div class="qr-popup"><label for="qr-toggle" class="close-btn">×</label><img src="{qr_url}" style="width: 65vh; max-width: 600px; border-radius: 10px; border: 2px solid #333;"><h3 style="color: black; margin-top: 15px; font-weight: bold;">📱 Quét mã mở Google Maps</h3></div></div>
        </div>""", unsafe_allow_html=True)