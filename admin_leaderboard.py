import streamlit as st
import pandas as pd
import pyodbc
import math
from config import CONN_STR

# --- HÀM TÍNH KHOẢNG CÁCH (HAVERSINE) NGAY TRONG PYTHON ĐỂ TRÁNH QUÁ TẢI SQL ---
def calculate_distance_km(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2): return 0.0
    R = 6371.0 
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Lấy tọa độ kho (Chỉ chạy 1 lần)
@st.cache_data(ttl=3600)
def get_wh_coords():
    try:
        conn = pyodbc.connect(CONN_STR)
        df = pd.read_sql("SELECT lat, lon FROM WarehouseConfig WHERE id = 1", conn)
        conn.close()
        return df.iloc[0]['lat'], df.iloc[0]['lon']
    except: return 18.6601, 105.6942

# --- HÀM LẤY DỮ LIỆU & TÍNH TIỀN KHÁCH HÀNG ---
@st.cache_data(ttl=60)
def get_top_customers():
    try:
        wh_lat, wh_lon = get_wh_coords()
        conn = pyodbc.connect(CONN_STR)
        # Lấy danh sách kèm tọa độ để tự tính tiền
        query = """
            SELECT 
                ISNULL(u.fullname, p.created_by) as Fullname,
                p.created_by as Username,
                p.lat, p.lon
            FROM LogisticsPoints p
            LEFT JOIN userstable u ON p.created_by = u.username
            WHERE p.created_by IS NOT NULL AND p.created_by != 'admin'
        """
        df_raw = pd.read_sql(query, conn)
        conn.close()
        
        if df_raw.empty: return pd.DataFrame()
        
        # Vectorized tính tiền siêu tốc bằng Pandas
        df_raw['Distance'] = df_raw.apply(lambda row: calculate_distance_km(wh_lat, wh_lon, row['lat'], row['lon']), axis=1)
        df_raw['Fee'] = df_raw['Distance'].apply(lambda d: max(15000, int(d * 6000)))
        
        # Gom nhóm và tính tổng
        df_agg = df_raw.groupby(['Fullname', 'Username']).agg(
            TotalOrders=('Fee', 'count'),
            TotalSpent=('Fee', 'sum')
        ).reset_index()
        
        return df_agg.sort_values('TotalOrders', ascending=False).head(10)
    except Exception as e:
        return pd.DataFrame()

# --- HÀM LẤY DỮ LIỆU & TÍNH THU NHẬP TÀI XẾ ---
@st.cache_data(ttl=60)
def get_top_drivers():
    try:
        wh_lat, wh_lon = get_wh_coords()
        conn = pyodbc.connect(CONN_STR)
        # Tương tự, lấy danh sách đơn Đã hoàn thành kèm tọa độ
        query = """
            SELECT 
                ISNULL(u.fullname, p.driver_id) as Fullname,
                p.driver_id as Username,
                p.lat, p.lon
            FROM LogisticsPoints p
            LEFT JOIN userstable u ON p.driver_id = u.username
            WHERE p.delivery_status = N'Đã hoàn thành' AND p.driver_id IS NOT NULL
        """
        df_raw = pd.read_sql(query, conn)
        conn.close()
        
        if df_raw.empty: return pd.DataFrame()

        # Tính phí ship của đơn đó
        df_raw['Distance'] = df_raw.apply(lambda row: calculate_distance_km(wh_lat, wh_lon, row['lat'], row['lon']), axis=1)
        df_raw['OrderFee'] = df_raw['Distance'].apply(lambda d: max(15000, int(d * 6000)))
        # Giả sử tài xế được hưởng 80% phí ship
        df_raw['Earnings'] = df_raw['OrderFee'] * 0.8
        
        # Gom nhóm
        df_agg = df_raw.groupby(['Fullname', 'Username']).agg(
            TotalDelivered=('OrderFee', 'count'),
            TotalEarned=('Earnings', 'sum')
        ).reset_index()
        
        return df_agg.sort_values('TotalDelivered', ascending=False).head(10)
    except Exception as e:
        return pd.DataFrame()

# --- HÀM VẼ THẺ TOP 3 VINH DANH ---
def render_top_3_cards(df, name_col, count_col, count_unit, money_col, money_label, icon):
    if len(df) == 0:
        st.info("Chưa có đủ dữ liệu để xếp hạng.")
        return
        
    c1, c2, c3 = st.columns(3)
    
    # Bạc (Hạng 2)
    with c1:
        if len(df) >= 2:
            st.markdown(f"""
            <div style="background: linear-gradient(145deg, #1A1C24, #21262d); border: 2px solid #C0C0C0; border-radius: 15px; padding: 20px; text-align: center; box-shadow: 0 5px 15px rgba(192, 192, 192, 0.2);">
                <div style="font-size: 40px; margin-bottom: 10px;">🥈</div>
                <h3 style="color: white; margin: 0; font-size: 18px;">{df.iloc[1][name_col]}</h3>
                <p style="color: #8b949e; font-size: 13px; margin: 5px 0;">@{df.iloc[1]['Username']}</p>
                <div style="color: #C0C0C0; font-size: 20px; font-weight: bold; margin-top: 10px;"><i class="fa-solid {icon}"></i> {df.iloc[1][count_col]} <span style="font-size: 12px;">{count_unit}</span></div>
                <div style="color: #28a745; font-size: 14px; margin-top: 5px; font-weight: bold;">{money_label}: {int(df.iloc[1][money_col]):,} VNĐ</div>
            </div>
            """, unsafe_allow_html=True)

    # Vàng (Hạng 1)
    with c2:
        if len(df) >= 1:
            st.markdown(f"""
            <div style="background: linear-gradient(145deg, #2b2510, #1A1C24); border: 3px solid #FFD700; border-radius: 15px; padding: 25px 20px; text-align: center; box-shadow: 0 5px 25px rgba(255, 215, 0, 0.3); transform: translateY(-10px);">
                <div style="font-size: 50px; margin-bottom: 10px; text-shadow: 0 0 10px rgba(255,215,0,0.5);">🏆</div>
                <h2 style="color: #FFD700; margin: 0; font-size: 22px; font-weight: 900;">{df.iloc[0][name_col]}</h2>
                <p style="color: #8b949e; font-size: 13px; margin: 5px 0;">@{df.iloc[0]['Username']}</p>
                <div style="color: white; font-size: 24px; font-weight: bold; margin-top: 10px;"><i class="fa-solid {icon}" style="color: #FFD700;"></i> {df.iloc[0][count_col]} <span style="font-size: 12px; color: #8b949e;">{count_unit}</span></div>
                <div style="color: #28a745; font-size: 16px; margin-top: 5px; font-weight: bold;">{money_label}: {int(df.iloc[0][money_col]):,} VNĐ</div>
            </div>
            """, unsafe_allow_html=True)

    # Đồng (Hạng 3)
    with c3:
        if len(df) >= 3:
            st.markdown(f"""
            <div style="background: linear-gradient(145deg, #1A1C24, #21262d); border: 2px solid #CD7F32; border-radius: 15px; padding: 20px; text-align: center; box-shadow: 0 5px 15px rgba(205, 127, 50, 0.2);">
                <div style="font-size: 40px; margin-bottom: 10px;">🥉</div>
                <h3 style="color: white; margin: 0; font-size: 18px;">{df.iloc[2][name_col]}</h3>
                <p style="color: #8b949e; font-size: 13px; margin: 5px 0;">@{df.iloc[2]['Username']}</p>
                <div style="color: #CD7F32; font-size: 20px; font-weight: bold; margin-top: 10px;"><i class="fa-solid {icon}"></i> {df.iloc[2][count_col]} <span style="font-size: 12px;">{count_unit}</span></div>
                <div style="color: #28a745; font-size: 14px; margin-top: 5px; font-weight: bold;">{money_label}: {int(df.iloc[2][money_col]):,} VNĐ</div>
            </div>
            """, unsafe_allow_html=True)

# ==========================================
# HÀM RENDER CHÍNH
# ==========================================
def render_leaderboard():
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px; z-index: 2; position: relative;">
            <i class="fa-solid fa-ranking-star" style="font-size: 38px; margin-right: 15px; color: #FFD700; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 40px; font-weight: 700; color: white;">BẢNG XẾP HẠNG (LEADERBOARD)</h1>
        </div>
        <p style="color: #8b949e; font-size: 15px;">Theo dõi và phân tích các cá nhân hoạt động tích cực nhất trong hệ thống.</p>
        <hr style="border-color: #333;">
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["KHÁCH HÀNG TIỀM NĂNG", "TÀI XẾ TIỀM NĂNG"])

    # ----------------------------------------
    # LUỒNG 1: KHÁCH HÀNG TIỀM NĂNG
    # ----------------------------------------
    with tab1:
        df_cust = get_top_customers()
        st.markdown("### <i class='fa-solid fa-crown' style='color:#1976D2;'></i> TOP KHÁCH HÀNG TIỀM NĂNG", unsafe_allow_html=True)
        render_top_3_cards(df_cust, 'Fullname', 'TotalOrders', 'đơn đã tạo', 'TotalSpent', 'Tổng chi tiêu', 'fa-box')
        
        st.write("")
        st.write("")
        if not df_cust.empty:
            c_chart, c_table = st.columns([2, 1.5])
            with c_chart:
                st.markdown("**Biểu đồ Khối lượng Đơn hàng:**")
                chart_data = df_cust.set_index('Fullname')['TotalOrders']
                st.bar_chart(chart_data, color="#1976D2")
            with c_table:
                st.markdown("**Danh sách Chi tiết (Top 10):**")
                df_cust.index = df_cust.index + 1 
                
                # Format cột tiền trước khi hiển thị
                df_display = df_cust[['Fullname', 'TotalOrders', 'TotalSpent']].copy()
                df_display['TotalSpent'] = df_display['TotalSpent'].apply(lambda x: f"{int(x):,} đ")
                df_display.columns = ['Họ Tên', 'Số Đơn', 'Tổng Chi Tiêu']
                
                st.dataframe(df_display, use_container_width=True)

    # ----------------------------------------
    # LUỒNG 2: TÀI XẾ TIỀM NĂNG
    # ----------------------------------------
    with tab2:
        df_drv = get_top_drivers()
        st.markdown("### <i class='fa-solid fa-medal' style='color:#28a745;'></i> TOP TÀI XẾ TIỀM NĂNG", unsafe_allow_html=True)
        
        if df_drv.empty:
            st.warning("⚠️ Chưa có dữ liệu tài xế hoàn thành đơn, hoặc Database chưa được thêm cột 'driver_id'.")
        else:
            render_top_3_cards(df_drv, 'Fullname', 'TotalDelivered', 'chuyến', 'TotalEarned', 'Ước tính thu nhập', 'fa-check-double')
            
            st.write("")
            st.write("")
            c_chart2, c_table2 = st.columns([2, 1.5])
            with c_chart2:
                st.markdown("**Biểu đồ Năng suất Giao hàng:**")
                chart_data2 = df_drv.set_index('Fullname')['TotalDelivered']
                st.bar_chart(chart_data2, color="#28a745")
            with c_table2:
                st.markdown("**Danh sách Chi tiết (Top 10):**")
                df_drv.index = df_drv.index + 1
                
                # Format cột tiền trước khi hiển thị
                df_display_drv = df_drv[['Fullname', 'TotalDelivered', 'TotalEarned']].copy()
                df_display_drv['TotalEarned'] = df_display_drv['TotalEarned'].apply(lambda x: f"{int(x):,} đ")
                df_display_drv.columns = ['Họ Tên', 'Số Chuyến', 'Thu Nhập (80%)']
                
                st.dataframe(df_display_drv, use_container_width=True)