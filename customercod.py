import streamlit as st
import folium
from streamlit_folium import st_folium
import pyodbc
import math
import urllib.parse
import uuid
from datetime import datetime
from geopy.geocoders import Nominatim
from config import CONN_STR

geolocator = Nominatim(user_agent="umbrella_cod_user")

# --- HÀM TÍNH KHOẢNG CÁCH ---
def calculate_cod_distance(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]: return 0.0
    R = 6371.0 
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c * 1.3

# --- HÀM LƯU ĐƠN COD ĐA ĐIỂM VÀO DATABASE (ĐÃ CẬP NHẬT GROUP_ID) ---
def create_multi_cod_order(pickup, dropoffs, username):
    try:
        conn = pyodbc.connect(CONN_STR)
        cursor = conn.cursor()
        inserted_ids = []
        
        # 1. Tạo 1 mã Chuyến (Group ID) duy nhất cho cả cụm đơn này
        trip_group_id = "COD_" + str(uuid.uuid4())[:8].upper()
        
        # 2. Lấy 1 mốc thời gian duy nhất cho tất cả các điểm
        exact_time = datetime.now()
        
        for drop in dropoffs:
            cursor.execute("""
                INSERT INTO LogisticsPoints 
                (pickup_lat, pickup_lon, lat, lon, status, created_by, created_at, delivery_status, order_type, group_id) 
                OUTPUT INSERTED.point_id
                VALUES (?, ?, ?, ?, N'Chờ Admin duyệt', ?, ?, N'Chờ xếp xe', N'lẻ', ?)
            """, (pickup[0], pickup[1], drop[0], drop[1], username, exact_time, trip_group_id))
            new_id = cursor.fetchone()[0]
            inserted_ids.append(str(new_id))
            
        conn.commit()
        conn.close()
        return ", ".join(inserted_ids)
    except Exception as e:
        st.error(f"Lỗi tạo đơn: {e}")
        return None

# ==========================================
# HÀM RENDER CHÍNH
# ==========================================
def render_cod_page():
    if 'cod_pickup' not in st.session_state: st.session_state.cod_pickup = None
    if 'cod_dropoffs' not in st.session_state: st.session_state.cod_dropoffs = []
    if 'cod_ready_to_pay' not in st.session_state: st.session_state.cod_ready_to_pay = False
    if 'cod_show_qr' not in st.session_state: st.session_state.cod_show_qr = False
    if 'cod_created_ids' not in st.session_state: st.session_state.cod_created_ids = None
    if 'last_map_click' not in st.session_state: st.session_state.last_map_click = None

    username = st.session_state.get("customer", "Unknown")
    col_form, col_map = st.columns([1.3, 2.7], gap="large")

    with col_form:
        if st.session_state.cod_created_ids:
            st.markdown(f"""<div style="padding: 20px; border-radius: 12px; background-color: rgba(40, 167, 69, 0.15); border: 1px solid #28a745; text-align: center; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
<i class="fa-solid fa-truck-fast" style="font-size: 50px; color: #28a745; margin-bottom: 15px;"></i>
<h3 style="color: #28a745; margin: 0;">ĐẶT HỎA TỐC THÀNH CÔNG!</h3>
<p style="color: white; font-size: 16px; margin-top: 15px;">Mã vận đơn: <b style="font-size: 20px; color: #FF4B4B;">#{st.session_state.cod_created_ids}</b></p>
<p style="color: #8b949e; font-size: 13px;">Đơn hàng đã được ghi nhận vào hệ thống.</p>
</div>""", unsafe_allow_html=True)
            if st.button("Tạo đơn Hỏa tốc mới", use_container_width=True, type="primary"):
                st.session_state.cod_created_ids = None
                st.session_state.cod_pickup = None
                st.session_state.cod_dropoffs = []
                st.session_state.cod_ready_to_pay = False
                st.session_state.cod_show_qr = False
                st.rerun()

        else:
            step1_color = "#FF9800" if st.session_state.cod_pickup else "#555"
            step2_color = "#4CAF50" if len(st.session_state.cod_dropoffs) > 0 else "#555"
            step3_color = "#1E90FF" if st.session_state.cod_ready_to_pay else "#555"
            
            st.markdown(f"""<div style="background-color: #1A1C24; padding: 20px; border-radius: 12px; border: 1px solid #333; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
<h4 style="margin-top: 0; color: white; border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 15px;">
<i class="fa-solid fa-route" style="color:#FF4B4B;"></i> Quy trình tạo đơn
</h4>
<div style="display: flex; align-items: center; margin-bottom: 15px;">
<div style="background: {step1_color}; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 10px;">1</div>
<span style="color: {'white' if not st.session_state.cod_pickup else '#8b949e'}; font-weight: {'bold' if not st.session_state.cod_pickup else 'normal'};">Chọn Điểm Lấy</span>
</div>
<div style="display: flex; align-items: center; margin-bottom: 15px;">
<div style="background: {step2_color}; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 10px;">2</div>
<span style="color: {'white' if (st.session_state.cod_pickup and not st.session_state.cod_ready_to_pay) else '#8b949e'}; font-weight: {'bold' if (st.session_state.cod_pickup and not st.session_state.cod_ready_to_pay) else 'normal'};">Chọn các Điểm Giao</span>
</div>
<div style="display: flex; align-items: center;">
<div style="background: {step3_color}; color: white; width: 30px; height: 30px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; margin-right: 10px;">3</div>
<span style="color: {'white' if st.session_state.cod_ready_to_pay else '#8b949e'}; font-weight: {'bold' if st.session_state.cod_ready_to_pay else 'normal'};">Thanh toán</span>
</div>
</div>""", unsafe_allow_html=True)

            # BƯỚC 1: CHỌN ĐIỂM LẤY
            if st.session_state.cod_pickup is None:
                st.markdown("""<div style="background-color: rgba(255, 152, 0, 0.15); border-left: 4px solid #FF9800; padding: 12px 15px; border-radius: 5px; margin-bottom: 15px;"><span style="color: #FF9800; font-weight: bold; font-size: 14px;">BƯỚC 1: Nhập địa chỉ LẤY HÀNG hoặc bấm lên bản đồ.</span></div>""", unsafe_allow_html=True)
                addr_pickup = st.text_input("Tìm địa chỉ Lấy hàng:", key="search_pickup")
                if st.button("Ghim Điểm Lấy", use_container_width=True):
                    with st.spinner("Đang tìm..."):
                        loc = geolocator.geocode(addr_pickup)
                        if loc: 
                            st.session_state.cod_pickup = (loc.latitude, loc.longitude)
                            st.rerun()
                        else: st.error("Không tìm thấy địa chỉ!")

            # BƯỚC 2: CHỌN CÁC ĐIỂM GIAO
            elif not st.session_state.cod_ready_to_pay:
                st.markdown("""<div style="background-color: rgba(76, 175, 80, 0.15); border-left: 4px solid #4CAF50; padding: 12px 15px; border-radius: 5px; margin-bottom: 15px;"><span style="color: #4CAF50; font-weight: bold; font-size: 14px;">BƯỚC 2: Nhập địa chỉ GIAO hoặc bấm lên bản đồ để thêm điểm.</span></div>""", unsafe_allow_html=True)
                
                addr_drop = st.text_input("Thêm địa chỉ Giao hàng:", key="search_dropoff")
                if st.button("Thêm Điểm Giao", use_container_width=True):
                    with st.spinner("Đang định vị..."):
                        loc = geolocator.geocode(addr_drop)
                        if loc:
                            st.session_state.cod_dropoffs.append((loc.latitude, loc.longitude))
                            st.rerun()
                        else: st.error("Không tìm thấy địa chỉ!")

                if len(st.session_state.cod_dropoffs) > 0:
                    st.write(f"---")
                    st.success(f"Đã chọn {len(st.session_state.cod_dropoffs)} điểm giao.")
                    col_btn1, col_btn2 = st.columns(2)
                    if col_btn1.button("XÁC NHẬN Tuyến", type="primary", use_container_width=True):
                        st.session_state.cod_ready_to_pay = True
                        st.rerun()
                    if col_btn2.button("Xóa điểm cuối", use_container_width=True):
                        if st.session_state.cod_dropoffs: st.session_state.cod_dropoffs.pop()
                        st.rerun()
                
                st.write("---")
                if st.button("Chọn lại Điểm Lấy", use_container_width=True):
                    st.session_state.cod_pickup = None; st.session_state.cod_dropoffs = []; st.rerun()

            # BƯỚC 3: THANH TOÁN
            elif st.session_state.cod_ready_to_pay:
                total_dist_km = 0
                prev_point = st.session_state.cod_pickup
                for drop in st.session_state.cod_dropoffs:
                    total_dist_km += calculate_cod_distance(prev_point[0], prev_point[1], drop[0], drop[1])
                    prev_point = drop
                shipping_fee = max(20000, int(total_dist_km * 8000)) 
                
                st.markdown(f"""<div style="padding: 15px; border: 1px solid #1E90FF; border-radius: 12px; margin-bottom: 15px; background: rgba(30, 144, 255, 0.05); box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
<h4 style="color:white; margin-top:0; margin-bottom: 15px;"><i class="fa-solid fa-file-invoice-dollar" style="color:#1E90FF;"></i> Tổng kết Hỏa tốc</h4>
<div style="display:flex; justify-content: space-between; margin-bottom:8px;"><span style="color:#8b949e;">Số điểm giao:</span><b style="color:white;">{len(st.session_state.cod_dropoffs)} điểm</b></div>
<div style="display:flex; justify-content: space-between; margin-bottom:12px; border-bottom: 1px dashed #444; padding-bottom: 10px;"><span style="color:#8b949e;">Tổng quãng đường:</span><b style="color:white;">{total_dist_km:.1f} km</b></div>
<div style="display:flex; justify-content: space-between; align-items:center;"><span style="color:#8b949e; font-size: 15px;"><b>Tổng cước:</b></span><b style="color:#FF4B4B; font-size: 24px;">{shipping_fee:,} đ</b></div>
</div>""", unsafe_allow_html=True)
                
                if not st.session_state.cod_show_qr:
                    if st.button("TIẾN HÀNH THANH TOÁN", type="primary", use_container_width=True):
                        st.session_state.cod_show_qr = True; st.rerun()
                    if st.button("Chỉnh sửa lại điểm", use_container_width=True):
                        st.session_state.cod_ready_to_pay = False; st.rerun()
                else:
                    qr_url = f"https://img.vietqr.io/image/MB-0987654321-compact2.png?amount={shipping_fee}&addInfo=COD_{username}&accountName=UMBRELLA"
                    st.markdown(f"""<div style="text-align:center; padding: 15px; border: 2px dashed #28a745; border-radius: 8px; margin-bottom: 15px; background: rgba(40, 167, 69, 0.05);">
<b style="color:#28a745;"><i class="fa-solid fa-qrcode"></i> Thanh toán vận đơn</b><br>
<img src="{qr_url}" style="width:180px; border-radius:10px; margin: 10px 0;">
</div>""", unsafe_allow_html=True)
                    if st.button("ĐÃ CHUYỂN KHOẢN - TẠO ĐƠN", type="primary", use_container_width=True):
                        with st.spinner("Đang tạo đơn..."):
                            ids = create_multi_cod_order(st.session_state.cod_pickup, st.session_state.cod_dropoffs, username)
                            if ids: st.session_state.cod_created_ids = ids; st.rerun()
                    if st.button("Quay lại", use_container_width=True):
                        st.session_state.cod_show_qr = False; st.rerun()

    with col_map:
        center = list(st.session_state.cod_pickup) if st.session_state.cod_pickup else [18.6601, 105.6942]
        m_cod = folium.Map(location=center, zoom_start=13, tiles="cartodbpositron")
        
        if st.session_state.cod_pickup:
            folium.Marker(st.session_state.cod_pickup, icon=folium.DivIcon(html='<div style="color:white; background:#FF9800; border-radius:50%; width:35px; height:35px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5);">LẤY</div>')).add_to(m_cod)

        route_pts = [st.session_state.cod_pickup] if st.session_state.cod_pickup else []
        for i, drop in enumerate(st.session_state.cod_dropoffs):
            folium.Marker(drop, icon=folium.DivIcon(html=f'<div style="color:white; background:#4CAF50; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white;">G{i+1}</div>')).add_to(m_cod)
            route_pts.append(drop)

        if len(route_pts) > 1:
            folium.PolyLine(locations=route_pts, color="#9C27B0", weight=4, dash_array="10", opacity=0.7).add_to(m_cod)

        # Trả về tọa độ click nếu chưa xác nhận thanh toán
        ret_obj = [] if st.session_state.cod_ready_to_pay else ["last_clicked"]
        map_data = st_folium(m_cod, width="100%", height=650, key="multi_cod_map_v2", returned_objects=ret_obj)
        
        if map_data and map_data.get("last_clicked"):
            curr_click = (map_data["last_clicked"]["lat"], map_data["last_clicked"]["lng"])
            if st.session_state.last_map_click != curr_click:
                st.session_state.last_map_click = curr_click
                if st.session_state.cod_pickup is None:
                    st.session_state.cod_pickup = curr_click
                elif not st.session_state.cod_ready_to_pay:
                    st.session_state.cod_dropoffs.append(curr_click)
                st.rerun()