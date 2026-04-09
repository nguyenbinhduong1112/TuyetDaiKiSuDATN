import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import pyodbc
from config import CONN_STR

# --- LẤY DỮ LIỆU ĐƠN CHỜ DUYỆT ---
@st.cache_data(ttl=10)
def get_pending_cod_orders():
    try:
        conn = pyodbc.connect(CONN_STR)
        query = """
            SELECT point_id, pickup_lat, pickup_lon, lat, lon, created_by, created_at
            FROM LogisticsPoints 
            WHERE status = N'Chờ Admin duyệt' AND order_type = N'lẻ'
            ORDER BY created_at DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()

# --- LẤY DỮ LIỆU ĐƠN ĐANG CHẠY ---
@st.cache_data(ttl=15)
def get_active_cod_orders():
    try:
        conn = pyodbc.connect(CONN_STR)
        query = """
            SELECT point_id, status, delivery_status, created_by 
            FROM LogisticsPoints 
            WHERE status IN (N'Chờ xử lý', N'Đang giao') AND order_type = N'lẻ'
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except: return pd.DataFrame()

# --- HÀM XỬ LÝ (DUYỆT / HỦY THEO NHÓM ID) ---
def approve_cod_group(point_ids):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(point_ids))
        sql = f"UPDATE LogisticsPoints SET status = N'Chờ xử lý' WHERE point_id IN ({placeholders})"
        cursor.execute(sql, point_ids)
        conn.commit(); conn.close()
        return True
    except: return False

def reject_cod_group(point_ids):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(point_ids))
        sql = f"UPDATE LogisticsPoints SET status = N'Đã hủy' WHERE point_id IN ({placeholders})"
        cursor.execute(sql, point_ids)
        conn.commit(); conn.close()
        return True
    except: return False

def approve_all_cod():
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        cursor.execute("UPDATE LogisticsPoints SET status = N'Chờ xử lý' WHERE status = N'Chờ Admin duyệt' AND order_type = N'lẻ'")
        conn.commit(); conn.close()
        return True
    except: return False

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
def render_cod_admin_page():
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px; z-index: 2; position: relative;">
            <i class="fa-solid fa-clipboard-check" style="font-size: 40px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 42px; font-weight: 700; color: white;">Trạm kiểm duyệt COD</h1>
        </div>
        <hr style="margin-top: 5px; border-color: #333; z-index: 2; position: relative; margin-bottom: 20px;">
    """, unsafe_allow_html=True)

    df_pending = get_pending_cod_orders()
    df_active = get_active_cod_orders()

    # Nhóm các đơn có cùng người đặt, cùng điểm lấy và cùng thời gian thành 1 CHUYẾN XE
    num_trips = 0
    if not df_pending.empty:
        # Làm tròn thời gian đến phút để gom nhóm chính xác hơn, phòng sai số mili-giây
        df_pending['time_group'] = pd.to_datetime(df_pending['created_at']).dt.floor('Min')
        grouped_pending = df_pending.groupby(['pickup_lat', 'pickup_lon', 'created_by', 'time_group'])
        num_trips = len(grouped_pending)

    # --- METRICS TỔNG QUAN ---
    m1, m2, m3 = st.columns(3)
    m1.markdown(f"""<div style="background: #1A1C24; padding: 15px; border-radius: 10px; border: 1px solid #333; border-left: 4px solid #FF9800;">
        <p style="color:#8b949e; margin:0; font-size: 14px;">Chuyến xe chờ duyệt</p>
        <h2 style="color:white; margin:0;">{num_trips}</h2>
    </div>""", unsafe_allow_html=True)
    
    m2.markdown(f"""<div style="background: #1A1C24; padding: 15px; border-radius: 10px; border: 1px solid #333; border-left: 4px solid #1E90FF;">
        <p style="color:#8b949e; margin:0; font-size: 14px;">Chuyến chờ Tài xế</p>
        <h2 style="color:white; margin:0;">{len(df_active[df_active['status'] == 'Chờ xử lý']) if not df_active.empty else 0}</h2>
    </div>""", unsafe_allow_html=True)
    
    m3.markdown(f"""<div style="background: #1A1C24; padding: 15px; border-radius: 10px; border: 1px solid #333; border-left: 4px solid #4CAF50;">
        <p style="color:#8b949e; margin:0; font-size: 14px;">Điểm đang giao</p>
        <h2 style="color:white; margin:0;">{len(df_active[df_active['status'] == 'Đang giao']) if not df_active.empty else 0}</h2>
    </div>""", unsafe_allow_html=True)

    st.write("")

    col_list, col_map = st.columns([1.5, 2.5], gap="large")

    # ================== CỘT DANH SÁCH CHỜ DUYỆT ==================
    with col_list:
        st.markdown("### <i class='fa-solid fa-list' style='color:#FF4B4B;'></i> Tuyến xe mới", unsafe_allow_html=True)
        
        if df_pending.empty:
            st.info("Hiện không có tuyến Hỏa tốc nào cần duyệt.")
            if st.button("Làm mới trang", use_container_width=True):
                get_pending_cod_orders.clear(); st.rerun()
        else:
            if st.button("✅ DUYỆT TẤT CẢ CÁC TUYẾN", type="primary", use_container_width=True):
                with st.spinner("Đang duyệt toàn bộ..."):
                    if approve_all_cod():
                        get_pending_cod_orders.clear()
                        get_active_cod_orders.clear()
                        st.success("Đã duyệt tất cả! Đã đẩy sang app Tài xế.")
                        st.rerun()
            
            st.markdown("<hr style='margin: 15px 0; border-color: #333;'>", unsafe_allow_html=True)
            
            # ĐÃ SỬA LỖI: HIỂN THỊ THEO TỪNG NHÓM (CHUYẾN XE) THAY VÌ TỪNG DÒNG DB
            for (p_lat, p_lon, creator, t_grp), group in grouped_pending:
                point_ids = group['point_id'].tolist()
                id_strs = ", ".join(map(str, point_ids))
                time_str = group.iloc[0]['created_at'].strftime("%H:%M %d/%m/%Y") if isinstance(group.iloc[0]['created_at'], pd.Timestamp) else str(group.iloc[0]['created_at'])
                
                st.markdown(f"""
                <div style="background: rgba(30, 144, 255, 0.05); border: 1px solid #333; border-left: 4px solid #9C27B0; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                    <div style="display:flex; justify-content: space-between; margin-bottom: 5px;">
                        <b style="color: #9C27B0; font-size: 16px;"><i class="fa-solid fa-motorcycle"></i> Tuyến đa điểm</b>
                        <span style="color: #e0e0e0; font-size: 14px;"><i class="fa-solid fa-user"></i> {creator}</span>
                    </div>
                    <div style="font-size: 13px; color: #e0e0e0; margin-bottom: 5px;">
                        <b>Các mã đơn:</b> #{id_strs} <span style="background:#4CAF50; color:white; padding: 2px 6px; border-radius: 10px; font-size: 10px; margin-left: 5px;">{len(point_ids)} điểm giao</span>
                    </div>
                    <div style="font-size: 12px; color: #8b949e;">
                        <i class="fa-solid fa-clock"></i> {time_str}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                # Nút duyệt truyền vào danh sách các IDs
                if c1.button("Duyệt Tuyến", key=f"app_{point_ids[0]}", use_container_width=True, type="primary"):
                    if approve_cod_group(point_ids):
                        get_pending_cod_orders.clear(); get_active_cod_orders.clear(); st.rerun()
                if c2.button("Hủy Tuyến", key=f"rej_{point_ids[0]}", use_container_width=True):
                    if reject_cod_group(point_ids):
                        get_pending_cod_orders.clear(); st.rerun()
                st.write("") # Margin bottom

    # ================== CỘT BẢN ĐỒ TỔNG QUAN ==================
    with col_map:
        st.markdown("### <i class='fa-solid fa-map-location-dot' style='color:#FF4B4B;'></i> Bản đồ tuyến Hỏa tốc chờ duyệt", unsafe_allow_html=True)
        
        center_loc = [18.6601, 105.6942] # Mặc định Vinh
        if not df_pending.empty and df_pending.iloc[0]['pickup_lat'] is not None:
            center_loc = [df_pending.iloc[0]['pickup_lat'], df_pending.iloc[0]['pickup_lon']]
            
        m_admin = folium.Map(location=center_loc, zoom_start=13, tiles="cartodbpositron")
        
        # Vẽ các tuyến đường chờ duyệt lên bản đồ (cũng vẽ theo nhóm cho đẹp)
        if not df_pending.empty:
            for (p_lat, p_lon, creator, t_grp), group in grouped_pending:
                if pd.notna(p_lat) and pd.notna(p_lon):
                    # Marker Điểm lấy
                    folium.Marker([p_lat, p_lon], icon=folium.DivIcon(html=f'<div style="color:white; background:#FF9800; border-radius:50%; width:30px; height:30px; display:flex; align-items:center; justify-content:center; font-weight:bold; border:2px solid white; box-shadow: 0 0 10px rgba(0,0,0,0.5); font-size: 10px; z-index:900;">LẤY</div>'), tooltip=f"Lấy hàng - Khách: {creator}").add_to(m_admin)
                    
                    # Marker Điểm giao và Line
                    for _, row in group.iterrows():
                        d_lat, d_lon = row['lat'], row['lon']
                        if pd.notna(d_lat) and pd.notna(d_lon):
                            folium.Marker([d_lat, d_lon], icon=folium.Icon(color="green", icon="arrow-down", prefix="fa"), tooltip=f"Giao - Mã #{row['point_id']}").add_to(m_admin)
                            folium.PolyLine(locations=[[p_lat, p_lon], [d_lat, d_lon]], color="#9C27B0", weight=3, opacity=0.6, dash_array="5").add_to(m_admin)

        st_folium(m_admin, width="100%", height=550, key="admin_cod_map", returned_objects=[])