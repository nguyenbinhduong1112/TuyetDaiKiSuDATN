import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import pyodbc
import math
import os
import torch
import numpy as np
import urllib.parse
from config import CONN_STR

# --- IMPORT THUẬT TOÁN AI (GIỐNG HỆT DRIVER.PY) ---
from model import PointerNet
from map_utils import MapManager
from engine import solve_delivery_route

# --- LOAD AI MODEL VÀO RAM ---
@st.cache_resource
def load_all_cod():
    model = PointerNet()
    if os.path.exists('weights.pth'): 
        model.load_state_dict(torch.load('weights.pth', map_location='cpu'))
    model.eval()
    return model, MapManager()

# --- HÀM TÍNH KHOẢNG CÁCH (Tuyến đường) ---
def calculate_route_distance(locations, route_indices=None):
    if not route_indices:
        route_indices = list(range(len(locations)))
    if len(route_indices) < 2: return 0.0
    R, total_dist = 6371.0, 0.0
    for i in range(len(route_indices) - 1):
        p1, p2 = locations[route_indices[i]], locations[route_indices[i+1]]
        lat1, lon1, lat2, lon2 = map(math.radians, [p1[0], p1[1], p2[0], p2[1]])
        a = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
        total_dist += R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))
    return total_dist * 1.3 

# --- LẤY DỮ LIỆU ĐƠN COD ---
@st.cache_data(ttl=15)
def get_available_cod_orders():
    try:
        conn = pyodbc.connect(CONN_STR)
        query = """
            SELECT point_id, pickup_lat, pickup_lon, lat, lon, created_by, created_at, group_id
            FROM LogisticsPoints 
            WHERE status = N'Chờ xử lý' AND order_type = N'lẻ'
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

@st.cache_data(ttl=15)
def get_my_active_cod_order(driver_username):
    try:
        conn = pyodbc.connect(CONN_STR)
        query = f"""
            SELECT point_id, pickup_lat, pickup_lon, lat, lon, created_by, delivery_status, group_id
            FROM LogisticsPoints 
            WHERE status = N'Đang giao' AND order_type = N'lẻ' 
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except: return pd.DataFrame()

# --- HÀM CẬP NHẬT TRẠNG THÁI (NHÓM ĐƠN) ---
def assign_cod_group_to_driver(point_ids, driver_username):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(point_ids))
        sql = f"UPDATE LogisticsPoints SET status = N'Đang giao' WHERE point_id IN ({placeholders})"
        cursor.execute(sql, point_ids)
        conn.commit(); conn.close()
        return True
    except: return False

def complete_cod_group(point_ids):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(point_ids))
        sql = f"UPDATE LogisticsPoints SET status = N'Chờ Admin duyệt', delivery_status = N'Đang chờ duyệt' WHERE point_id IN ({placeholders})"
        cursor.execute(sql, point_ids)
        conn.commit(); conn.close()
        return True
    except: return False

# ==========================================
# GIAO DIỆN CHÍNH (Được gọi từ driver.py)
# ==========================================
def render_cod_page(driver_fullname):
    if 'cod_route_indices' not in st.session_state: st.session_state.cod_route_indices = None
    if 'cod_actual_path' not in st.session_state: st.session_state.cod_actual_path = None

    driver_user = st.session_state.get("customer", "")
    my_active_order = get_my_active_cod_order(driver_user)
    
    model, map_mgr = load_all_cod()
    col_map, col_ctrl = st.columns([3, 1])
    
    with col_ctrl:
        st.markdown("### <i class='fa-solid fa-list-check' style='color:#FF4B4B;'></i> Tác vụ COD", unsafe_allow_html=True)
        
        if not my_active_order.empty:
            pickup = [my_active_order.iloc[0]['pickup_lat'], my_active_order.iloc[0]['pickup_lon']]
            dropoffs = my_active_order[['lat', 'lon']].values.tolist()
            locations = [pickup] + dropoffs
            point_ids = my_active_order['point_id'].tolist()
            
            if st.session_state.cod_route_indices:
                dist_km = calculate_route_distance(locations, st.session_state.cod_route_indices)
            else:
                dist_km = calculate_route_distance(locations)

            st.markdown(f"""
            <div style="background-color: rgba(156, 39, 176, 0.15); border-left: 4px solid #9C27B0; padding: 15px; border-radius: 5px; margin-bottom: 15px;">
                <span style="color: #9C27B0; font-weight: bold; font-size: 15px;"><i class="fa-solid fa-motorcycle"></i> ĐANG CHẠY CHUYẾN HỎA TỐC</span><br>
                <span style="color: #e0e0e0; font-size: 13px;">Khách hàng: <b>{my_active_order.iloc[0]['created_by']}</b></span><br>
                <span style="color: #e0e0e0; font-size: 13px;">Số điểm giao: <b>{len(dropoffs)}</b></span><br>
                <span style="color: #e0e0e0; font-size: 13px;">Khoảng cách: <b>~{dist_km:.1f} km</b></span>
            </div>
            """, unsafe_allow_html=True)
            
            if len(locations) > 2 and not st.session_state.cod_route_indices:
                if st.button("Kích hoạt tối ưu AI", type="primary", use_container_width=True):
                    with st.status("AI đang phân tích lộ trình...", expanded=False):
                        coords_tensor = torch.FloatTensor(locations)
                        st.session_state.cod_route_indices = solve_delivery_route(model, coords_tensor)
                        node_ids = map_mgr.get_nearest_nodes(locations)
                        ordered_nodes = [node_ids[i] for i in st.session_state.cod_route_indices]
                        st.session_state.cod_actual_path = map_mgr.get_route_coords(ordered_nodes)
                    st.rerun()
            
            if my_active_order.iloc[0]['delivery_status'] == "Đang chờ duyệt":
                st.button("Đã báo cáo Admin duyệt...", disabled=True, use_container_width=True)
            else:
                st.write("---")
                if st.button("XÁC NHẬN HOÀN THÀNH CHUYẾN", type="primary", use_container_width=True):
                    with st.spinner("Gửi yêu cầu..."):
                        if complete_cod_group(point_ids):
                            get_my_active_cod_order.clear()
                            st.session_state.cod_route_indices = None
                            st.session_state.cod_actual_path = None
                            st.success("Báo cáo thành công! Chờ Admin duyệt.")
                            st.rerun()
                        else:
                            st.error("Lỗi cập nhật.")
                            
        else:
            avail_orders = get_available_cod_orders()
            if avail_orders.empty:
                st.markdown("""<div style="background-color: rgba(255, 204, 0, 0.15); border-left: 4px solid #ffcc00; padding: 12px 15px; border-radius: 5px; margin-bottom: 15px;"><span style="color: #ffcc00; font-weight: bold; font-size: 14px;"><i class="fa-solid fa-mug-hot"></i> Hiện không có chuyến COD nào.</span></div>""", unsafe_allow_html=True)
                if st.button("Làm mới danh sách", use_container_width=True):
                    get_available_cod_orders.clear(); st.rerun()
            else:
                # Gom nhóm theo group_id
                avail_orders['group_id'] = avail_orders['group_id'].fillna(avail_orders['point_id'].astype(str))
                trip_groups = avail_orders.groupby('group_id')
                options = {}
                for grp_id, group in trip_groups:
                    ids = group['point_id'].tolist()
                    creator = group.iloc[0]['created_by']
                    label = f"Khách {creator} - Giao {len(ids)} điểm (Mã: {grp_id})"
                    options[label] = ids
                
                st.markdown(f"""<div style="margin-bottom: 10px;"><span style="color: #e0e0e0; font-size: 15px;"><i class="fa-solid fa-clipboard-list" style="color:#FF4B4B;"></i> Có <b style="color: white;">{len(options)}</b> tuyến đang chờ.</span></div>""", unsafe_allow_html=True)
                
                selected_label = st.selectbox("Chọn chuyến để nhận:", list(options.keys()))
                selected_ids = options[selected_label]
                
                if st.button("NHẬN CHUYẾN NÀY", type="primary", use_container_width=True):
                    if st.session_state.get('driver_status', 'Ngoại tuyến') == "Ngoại tuyến":
                        st.error("Bật trạng thái Sẵn sàng để nhận cuốc!")
                    else:
                        with st.spinner("Đang chốt chuyến..."):
                            if assign_cod_group_to_driver(selected_ids, driver_user):
                                get_available_cod_orders.clear()
                                get_my_active_cod_order.clear()
                                st.session_state.cod_route_indices = None
                                st.session_state.cod_actual_path = None
                                st.success("Nhận chuyến thành công!")
                                st.rerun()

    with col_map:
        if not my_active_order.empty:
            center_lat, center_lon = my_active_order.iloc[0]['pickup_lat'], my_active_order.iloc[0]['pickup_lon']
        else:
            avail_orders = get_available_cod_orders()
            if not avail_orders.empty:
                center_lat, center_lon = avail_orders.iloc[0]['pickup_lat'], avail_orders.iloc[0]['pickup_lon']
            else:
                center_lat, center_lon = 18.6601, 105.6942
                
        m_cod = folium.Map(location=[center_lat, center_lon], zoom_start=14, tiles="cartodbpositron")
        
        if not my_active_order.empty:
            pickup = [my_active_order.iloc[0]['pickup_lat'], my_active_order.iloc[0]['pickup_lon']]
            dropoffs = my_active_order[['lat', 'lon']].values.tolist()
            locations = [pickup] + dropoffs
            
            if st.session_state.cod_route_indices:
                for i, loc_idx in enumerate(st.session_state.cod_route_indices):
                    p = locations[loc_idx]
                    color = "#FF9800" if loc_idx == 0 else "#1E90FF"
                    label = "LẤY" if loc_idx == 0 else str(i)
                    folium.Marker([p[0], p[1]], icon=folium.DivIcon(html=f'<div style="color:white; background:{color}; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5); font-size: 13px; z-index:1000;">{label}</div>')).add_to(m_cod)
                if st.session_state.cod_actual_path: 
                    folium.PolyLine(locations=st.session_state.cod_actual_path, color="#FF0000", weight=6, opacity=0.8).add_to(m_cod)
            else:
                folium.Marker(pickup, icon=folium.DivIcon(html=f'<div style="color:white; background:#FF9800; border-radius:50%; width:35px; height:35px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5); font-size: 11px; z-index:1000;">LẤY</div>')).add_to(m_cod)
                for i, d in enumerate(dropoffs):
                    folium.Marker(d, icon=folium.DivIcon(html=f'<div style="color:white; background:#4CAF50; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5); font-size: 11px; z-index:900;">G{i+1}</div>')).add_to(m_cod)
                folium.PolyLine(locations=locations, color="#9C27B0", weight=5, dash_array="10").add_to(m_cod)
                
        else:
            avail_orders = get_available_cod_orders()
            if not avail_orders.empty:
                avail_orders['group_id'] = avail_orders['group_id'].fillna(avail_orders['point_id'].astype(str))
                trip_groups = avail_orders.groupby('group_id')
                for grp_id, group in trip_groups:
                    p_lat, p_lon = group.iloc[0]['pickup_lat'], group.iloc[0]['pickup_lon']
                    if pd.notna(p_lat):
                        folium.Marker([p_lat, p_lon], icon=folium.DivIcon(html=f'<div style="color:white; background:#FF9800; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5); font-size: 10px; z-index:900;">LẤY</div>'), tooltip=f"Khách: {group.iloc[0]['created_by']}").add_to(m_cod)
                        for _, row in group.iterrows():
                            d_lat, d_lon = row['lat'], row['lon']
                            if pd.notna(d_lat):
                                folium.Marker([d_lat, d_lon], icon=folium.Icon(color="green", icon="arrow-down", prefix="fa"), tooltip=f"Đơn #{row['point_id']}").add_to(m_cod)
                                folium.PolyLine(locations=[[p_lat, p_lon], [d_lat, d_lon]], color="#9C27B0", weight=3, opacity=0.6).add_to(m_cod)
                
        if st.session_state.get('driver_loc') and st.session_state.get('driver_status') != "Ngoại tuyến":
            folium.Marker(location=st.session_state.driver_loc, icon=folium.Icon(color="blue", icon="truck", prefix="fa"), tooltip=f"Vị trí của bạn").add_to(m_cod)
            
        st_folium(m_cod, width="100%", height=550, key="driver_cod_map_unique", returned_objects=[])

    # =======================================================
    # KHU VỰC HIỂN THỊ LINK MAPS & QR CODE (FIXED)
    # =======================================================
    if not my_active_order.empty:
        st.markdown("### <i class='fa-solid fa-location-arrow' style='color:#FF4B4B;'></i> Trình chỉ đường Hỏa tốc", unsafe_allow_html=True)
        col_info, col_qr = st.columns([2.8, 1.2], gap="large") 
        
        pickup = [my_active_order.iloc[0]['pickup_lat'], my_active_order.iloc[0]['pickup_lon']]
        dropoffs = my_active_order[['lat', 'lon']].values.tolist()
        locations = [pickup] + dropoffs
        
        # [QUAN TRỌNG]: LUÔN BẮT ĐẦU TỪ VỊ TRÍ HIỆN TẠI (MY LOCATION)
        route_pts_url = ["My+Location"]
        
        if st.session_state.cod_route_indices:
            # Nếu có tối ưu AI, thêm các điểm theo đúng thứ tự (Bao gồm điểm Lấy và các điểm Giao)
            for i in st.session_state.cod_route_indices:
                p = locations[i]
                route_pts_url.append(f"{p[0]},{p[1]}")
        else:
            # Nếu không tối ưu, đi từ My Location -> Pickup -> Các điểm Giao mặc định
            route_pts_url.append(f"{pickup[0]},{pickup[1]}")
            for d in dropoffs:
                route_pts_url.append(f"{d[0]},{d[1]}")
                
        # Link chuẩn của Google Maps Directions
        gmaps_url = "https://www.google.com/maps/dir/" + "/".join(route_pts_url)
        
        with col_info:
            m1, m2, m3 = st.columns([1.2, 1, 1])
            dist = calculate_route_distance(locations, st.session_state.cod_route_indices)
            m1.metric("Trạng thái", "Đã Tối Ưu" if st.session_state.cod_route_indices else "Mặc định")
            m2.metric("Quãng đường", f"{dist:.2f} km")
            m3.metric("Điểm giao", f"{len(dropoffs)} điểm")
            st.markdown("<hr style='margin: 20px 0; border-color: #333;'>", unsafe_allow_html=True)
            st.markdown(f'<a href="{gmaps_url}" target="_blank" class="gmaps-btn" style="text-decoration:none; display:flex; justify-content:center; background:#1976D2; color:white; padding:12px; border-radius:8px; font-weight:bold;"><i class="fa-solid fa-map-location-dot" style="margin-right:8px;"></i> MỞ GOOGLE MAPS DẪN ĐƯỜNG</a>', unsafe_allow_html=True)
        
        with col_qr:
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=500x500&data={urllib.parse.quote(gmaps_url)}"
            # VIẾT HTML TRÊN 1 DÒNG ĐỂ Streamlit KHÔNG COI LÀ MARKDOWN CODE BLOCK
            html_qr = (
                '<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; background-color: #1A1C24; padding: 20px; border-radius: 10px; border: 1px solid #333;">'
                '<div style="color: #e0e0e0; font-size: 15px; font-weight: bold; margin-bottom: 12px;"><i class="fa-solid fa-qrcode" style="color:#FF4B4B;"></i> QR Quét lộ trình</div>'
                f'<img src="{qr_url}" style="width: 150px; border-radius: 8px; border: 3px solid white; margin-bottom: 15px;">'
                '<input type="checkbox" id="qr-toggle-cod" style="display: none;">'
                '<label for="qr-toggle-cod" class="open-btn" style="display: block; background: #262730; color: white; text-align: center; border-radius: 6px; cursor: pointer; font-weight: bold; border: 1px solid #444; width: 150px; font-size: 14px; padding: 10px 5px;">Phóng to QR</label>'
                '<div class="qr-overlay" style="display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.85); z-index: 999999; justify-content: center; align-items: center;">'
                '<style>#qr-toggle-cod:checked ~ .qr-overlay { display: flex !important; }</style>'
                '<div class="qr-popup" style="background: white; padding: 20px; border-radius: 15px; position: relative; text-align: center;">'
                '<label for="qr-toggle-cod" style="position: absolute; top: -15px; right: -15px; background: #FF4B4B; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; justify-content: center; align-items: center; cursor: pointer; font-size: 24px; font-weight: bold; border: 3px solid white;">×</label>'
                f'<img src="{qr_url}" style="width: 65vh; max-width: 600px; border-radius: 10px; border: 2px solid #333;">'
                '<h3 style="color: black; margin-top: 15px; font-weight: bold;"><i class="fa-solid fa-mobile-screen-button"></i> Quét mã mở Google Maps</h3>'
                '</div></div></div>'
            )
            st.markdown(html_qr, unsafe_allow_html=True)