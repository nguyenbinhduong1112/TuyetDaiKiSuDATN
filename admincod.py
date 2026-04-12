import streamlit as st
import pandas as pd
import pyodbc
import textwrap
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
    except Exception:
        return pd.DataFrame()

# --- LẤY DỮ LIỆU ĐƠN ĐANG CHẠY ---
@st.cache_data(ttl=15)
def get_active_cod_orders():
    try:
        conn = pyodbc.connect(CONN_STR)
        query = """
            SELECT point_id, status, delivery_status, created_by, lat, lon 
            FROM LogisticsPoints 
            WHERE status IN (N'Chờ xử lý', N'Đang giao') AND order_type = N'lẻ'
            ORDER BY created_at DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except: return pd.DataFrame()

# --- HÀM XỬ LÝ DATABASE ---
def execute_db_cod(query, params=()):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit(); conn.close()
        return True
    except: return False

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
def render_cod_admin_page():
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <i class="fa-solid fa-bolt-lightning" style="font-size: 40px; margin-right: 15px; color: #FFD700;"></i>
            <h1 style="margin: 0; font-size: 42px; font-weight: 700; color: white;">Trạm Điều Phối Hỏa Tốc (COD)</h1>
        </div>
        <p style="color: #8b949e; font-size: 15px; margin-bottom: 20px;">Duyệt và quản lý các yêu cầu giao hàng đa điểm tức thời.</p>
        <hr style="border-color: #333; margin-bottom: 20px;">
    """, unsafe_allow_html=True)

    df_pending = get_pending_cod_orders()
    df_active = get_active_cod_orders()

    num_trips = 0
    grouped_pending = []
    if not df_pending.empty:
        df_pending['time_group'] = pd.to_datetime(df_pending['created_at'], errors='coerce').dt.floor('Min')
        grouped_pending = df_pending.groupby(['pickup_lat', 'pickup_lon', 'created_by', 'time_group'])
        num_trips = len(grouped_pending)

    # --- CHỈ SỐ KPI ---
    m1, m2, m3, m4 = st.columns(4)
    metrics = [
        ("Chuyến chờ duyệt", num_trips, "#FF9800", "fa-hourglass-start"),
        ("Chờ Tài xế nhận", len(df_active[df_active['status'] == 'Chờ xử lý']) if not df_active.empty else 0, "#1E90FF", "fa-motorcycle"),
        ("Đang đi giao", len(df_active[df_active['status'] == 'Đang giao']) if not df_active.empty else 0, "#4CAF50", "fa-truck-fast"),
        ("Tổng đơn lẻ", len(df_pending) + len(df_active), "#E91E63", "fa-boxes-stacked")
    ]
    
    for col, (label, val, color, icon) in zip([m1, m2, m3, m4], metrics):
        col.markdown(f"""
            <div style="background: #1A1C24; padding: 15px; border-radius: 10px; border-left: 5px solid {color}; border: 1px solid #333;">
                <p style="color:#8b949e; margin:0; font-size: 13px; font-weight: bold; text-transform: uppercase;"><i class="fa-solid {icon}"></i> {label}</p>
                <h2 style="color:white; margin:5px 0 0 0;">{val}</h2>
            </div>
        """, unsafe_allow_html=True)

    st.write("")
    
    # CSS ICON CHO TABS
    st.markdown("""
        <style>
            div[data-testid="stTabs"] button[role="tab"]:nth-child(1) p::before { content: '\\f0f3 '; font-family: "Font Awesome 6 Free"; font-weight: 900; color: #FF9800; }
            div[data-testid="stTabs"] button[role="tab"]:nth-child(2) p::before { content: '\\f21c '; font-family: "Font Awesome 6 Free"; font-weight: 900; color: #1E90FF; }
        </style>
    """, unsafe_allow_html=True)

    tab1, tab2 = st.tabs([" CHỜ DUYỆT", " ĐƠN ĐANG CHẠY"])

    with tab1:
        if df_pending.empty:
            st.info("Hiện không có chuyến Hỏa tốc nào cần duyệt.")
        else:
            col_b1, col_b2, _ = st.columns([1.5, 1.5, 5])
            if col_b1.button("Duyệt Tất Cả", type="primary", use_container_width=True):
                if execute_db_cod("UPDATE LogisticsPoints SET status = N'Chờ xử lý' WHERE status = N'Chờ Admin duyệt' AND order_type = N'lẻ'"):
                    st.cache_data.clear(); st.rerun()
            if col_b2.button("Làm mới", use_container_width=True):
                st.cache_data.clear(); st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            cols = st.columns(2)
            idx = 0

            for (p_lat, p_lon, creator, t_grp), group in grouped_pending:
                point_ids = group['point_id'].tolist()
                time_str = group.iloc[0]['created_at'].strftime("%H:%M - %d/%m/%Y")
                
                # SỬ DỤNG DEDENT ĐỂ XÓA KHOẢNG TRẮNG ĐẦU DÒNG GÂY LỖI LÒI CODE
                card_html = textwrap.dedent(f"""
                    <div style="background-color: #21262d; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 15px; border-bottom: 1px solid #30363d; padding-bottom: 10px;">
                            <span style="background: #9C27B0; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; text-transform: uppercase;">
                                <i class="fa-solid fa-route"></i> Chuyến Đa Điểm
                            </span>
                            <span style="color: #8b949e; font-size: 12px;"><i class="fa-solid fa-clock"></i> {time_str}</span>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <p style="margin: 0; color: #e0e0e0; font-size: 16px;"><i class="fa-solid fa-circle-user" style="color: #1E90FF;"></i> <b>Khách:</b> {creator}</p>
                            <p style="margin: 5px 0 0 0; color: #8b949e; font-size: 14px;"><i class="fa-solid fa-layer-group" style="color: #4CAF50;"></i> <b>Quy mô:</b> {len(point_ids)} địa điểm giao</p>
                        </div>
                        <div style="background: #1A1C24; padding: 12px; border-radius: 8px; border-left: 4px solid #FF9800;">
                            <p style="margin:0; color: #FF9800; font-size: 12px; font-weight: bold;">ĐỊA ĐIỂM LẤY HÀNG</p>
                            <p style="margin:0; color: #e0e0e0; font-size: 13px;"><i class="fa-solid fa-map-pin"></i> Tọa độ: {p_lat:.4f}, {p_lon:.4f}</p>
                        </div>
                        <div style="background: #1A1C24; padding: 12px; border-radius: 8px; border-left: 4px solid #4CAF50; margin-top: 10px;">
                            <p style="margin:0; color: #4CAF50; font-size: 12px; font-weight: bold;">DANH SÁCH MÃ ĐƠN GIAO</p>
                            <p style="margin:0; color: #e0e0e0; font-size: 13px;"><i class="fa-solid fa-hashtag"></i> {", ".join(map(str, point_ids))}</p>
                        </div>
                    </div>
                """)

                with cols[idx % 2]:
                    st.markdown(card_html, unsafe_allow_html=True)
                    btn_col1, btn_col2 = st.columns(2)
                    if btn_col1.button("Duyệt Tuyến", key=f"ap_{point_ids[0]}", use_container_width=True, type="primary"):
                        placeholders = ','.join(['?'] * len(point_ids))
                        if execute_db_cod(f"UPDATE LogisticsPoints SET status = N'Chờ xử lý' WHERE point_id IN ({placeholders})", point_ids):
                            st.cache_data.clear(); st.rerun()
                    if btn_col2.button("Hủy Tuyến", key=f"re_{point_ids[0]}", use_container_width=True):
                        placeholders = ','.join(['?'] * len(point_ids))
                        if execute_db_cod(f"UPDATE LogisticsPoints SET status = N'Đã hủy' WHERE point_id IN ({placeholders})", point_ids):
                            st.cache_data.clear(); st.rerun()
                idx += 1

    with tab2:
        st.markdown("### <i class='fa-solid fa-satellite-dish' style='color:#1E90FF;'></i> Giám sát đơn lẻ đang lưu thông", unsafe_allow_html=True)
        if df_active.empty:
            st.info("Hiện không có đơn lẻ nào đang hoạt động.")
        else:
            df_display = df_active[['point_id', 'created_by', 'status', 'lat', 'lon']].copy()
            df_display.columns = ['Mã Đơn', 'Khách Hàng', 'Trạng Thái', 'Vĩ độ', 'Kinh độ']
            def color_st(val):
                return f'color: {"#FF9800" if val == "Chờ xử lý" else "#4CAF50"}; font-weight: bold;'
            st.dataframe(df_display.style.applymap(color_st, subset=['Trạng Thái']), use_container_width=True, hide_index=True)