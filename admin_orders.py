import streamlit as st
import pandas as pd
import pyodbc
import textwrap
from datetime import datetime
from config import CONN_STR

# --- LẤY DỮ LIỆU ĐƠN CHUỖI ---
@st.cache_data(ttl=10)
def get_chain_orders_data():
    try:
        conn = pyodbc.connect(CONN_STR)
        # 1. Yêu cầu tạo mới từ Khách hàng
        q_create = """
            SELECT point_id, lat, lon, created_by, created_at 
            FROM LogisticsPoints 
            WHERE status = N'Chờ Admin duyệt' AND order_type = N'chuỗi'
            ORDER BY created_at DESC
        """
        df_create = pd.read_sql(q_create, conn)
        
        # 2. Yêu cầu hoàn thành từ Tài xế
        q_complete = """
            SELECT point_id, lat, lon, created_by, created_at, ISNULL(driver_id, 'Unknown') as driver_id 
            FROM LogisticsPoints 
            WHERE delivery_status = N'Đang chờ duyệt' AND order_type = N'chuỗi'
            ORDER BY created_at DESC
        """
        df_complete = pd.read_sql(q_complete, conn)

        # 3. Đơn đang lưu thông
        q_active = """
            SELECT point_id, status, delivery_status, created_by, lat, lon, ISNULL(driver_id, 'Chưa nhận') as driver_id
            FROM LogisticsPoints 
            WHERE status = N'Chờ xử lý' AND delivery_status <> N'Đang chờ duyệt' AND order_type = N'chuỗi'
            ORDER BY created_at DESC
        """
        df_active = pd.read_sql(q_active, conn)
        
        conn.close()
        return df_create, df_complete, df_active
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=10)
def get_chain_pending_data():
    try:
        conn = pyodbc.connect(CONN_STR)
        q_create = """
            SELECT point_id, lat, lon, created_by, created_at
            FROM LogisticsPoints
            WHERE status = N'Chờ Admin duyệt' AND order_type = N'chuỗi'
            ORDER BY created_at DESC
        """
        df_create = pd.read_sql(q_create, conn)

        q_complete = """
            SELECT point_id, lat, lon, created_by, created_at, ISNULL(driver_id, 'Unknown') as driver_id
            FROM LogisticsPoints
            WHERE delivery_status = N'Đang chờ duyệt' AND order_type = N'chuỗi'
            ORDER BY created_at DESC
        """
        df_complete = pd.read_sql(q_complete, conn)
        conn.close()
        return df_create, df_complete
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=10)
def get_chain_active_data():
    try:
        conn = pyodbc.connect(CONN_STR)
        query = """
            SELECT point_id, status, delivery_status, created_by, lat, lon, ISNULL(driver_id, 'Chưa nhận') as driver_id
            FROM LogisticsPoints
            WHERE status = N'Chờ xử lý' AND delivery_status <> N'Đang chờ duyệt' AND order_type = N'chuỗi'
            ORDER BY created_at DESC
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=10)
def get_chain_order_counts():
    try:
        conn = pyodbc.connect(CONN_STR)
        query = """
            SELECT
                (
                    SELECT COUNT(*)
                    FROM (
                        SELECT created_by, DATEADD(minute, DATEDIFF(minute, 0, created_at), 0) AS time_group
                        FROM LogisticsPoints
                        WHERE status = N'Chờ Admin duyệt' AND order_type = N'chuỗi'
                        GROUP BY created_by, DATEADD(minute, DATEDIFF(minute, 0, created_at), 0)
                    ) AS create_groups
                ) AS create_count,
                (
                    SELECT COUNT(*)
                    FROM (
                        SELECT ISNULL(driver_id, 'Unknown') AS driver_id, DATEADD(minute, DATEDIFF(minute, 0, created_at), 0) AS time_group
                        FROM LogisticsPoints
                        WHERE delivery_status = N'Đang chờ duyệt' AND order_type = N'chuỗi'
                        GROUP BY ISNULL(driver_id, 'Unknown'), DATEADD(minute, DATEDIFF(minute, 0, created_at), 0)
                    ) AS complete_groups
                ) AS complete_count,
                (
                    SELECT COUNT(*)
                    FROM LogisticsPoints
                    WHERE status = N'Chờ xử lý' AND delivery_status <> N'Đang chờ duyệt' AND order_type = N'chuỗi'
                ) AS active_count
        """
        row = pd.read_sql(query, conn).iloc[0]
        conn.close()
        return tuple(0 if pd.isna(row[col]) else int(row[col]) for col in ["create_count", "complete_count", "active_count"])
    except Exception:
        return 0, 0, 0

def clear_chain_order_caches():
    get_chain_orders_data.clear()
    get_chain_pending_data.clear()
    get_chain_active_data.clear()
    get_chain_order_counts.clear()

# --- HÀM XỬ LÝ DATABASE ---
def execute_db_chain(query, params=()):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit(); conn.close()
        return True
    except: return False

# ==========================================
# GIAO DIỆN CHÍNH
# ==========================================
def render_page():
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 10px;">
            <i class="fa-solid fa-boxes-stacked" style="font-size: 40px; margin-right: 15px; color: #1976D2;"></i>
            <h1 style="margin: 0; font-size: 42px; font-weight: 700; color: white;">Trạm Điều Phối Đơn Chuỗi</h1>
        </div>
        <p style="color: #8b949e; font-size: 15px; margin-bottom: 20px;">Quản lý tập trung các yêu cầu gom tuyến và hoàn thành tuyến từ Khách hàng & Tài xế.</p>
        <hr style="border-color: #333; margin-bottom: 20px;">
    """, unsafe_allow_html=True)

    create_count, complete_count, active_count = get_chain_order_counts()

    # --- CHỈ SỐ KPI ---
    m1, m2, m3, m4 = st.columns(4)
    metrics = [
        ("Yêu cầu tạo mới", create_count, "#1976D2", "fa-plus-circle"),
        ("Chờ duyệt hoàn thành", complete_count, "#FF9800", "fa-check-double"),
        ("Tuyến đang chờ gom", active_count, "#4CAF50", "fa-route"),
        ("Tổng đơn hệ thống", create_count + complete_count + active_count, "#E91E63", "fa-cubes")
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
            div[data-testid="stTabs"] button[role="tab"]:nth-child(1) p::before { content: '\\f0f3 '; font-family: "Font Awesome 6 Free"; font-weight: 900; color: #1976D2; }
            div[data-testid="stTabs"] button[role="tab"]:nth-child(2) p::before { content: '\\f21c '; font-family: "Font Awesome 6 Free"; font-weight: 900; color: #4CAF50; }
        </style>
    """, unsafe_allow_html=True)

    selected_view = st.radio(
        "Chế độ xem đơn chuỗi",
        ["YÊU CẦU CHỜ DUYỆT", "THEO DÕI ĐƠN ĐANG CHẠY"],
        horizontal=True,
        label_visibility="collapsed",
    )

    # ================== TAB 1: YÊU CẦU CHỜ DUYỆT ==================
    if selected_view == "YÊU CẦU CHỜ DUYỆT":
        df_create, df_complete = get_chain_pending_data()

        # Nhóm dữ liệu để hiển thị dạng thẻ (Card)
        grouped_create, grouped_complete = [], []
        if not df_create.empty:
            df_create['time_group'] = pd.to_datetime(df_create['created_at'], errors='coerce').dt.floor('Min')
            grouped_create = df_create.groupby(['created_by', 'time_group'])
        if not df_complete.empty:
            df_complete['time_group'] = pd.to_datetime(df_complete['created_at'], errors='coerce').dt.floor('Min')
            grouped_complete = df_complete.groupby(['driver_id', 'time_group'])

        if df_create.empty and df_complete.empty:
            st.info("Hiện không có yêu cầu Đơn chuỗi nào cần xử lý.")
            if st.button("Làm mới dữ liệu", use_container_width=True):
                clear_chain_order_caches(); st.rerun()
        else:
            col_b1, col_b2, col_b3, _ = st.columns([1.5, 1.5, 1.5, 3.5])
            if not df_create.empty and col_b1.button("Duyệt Tất Cả (Tạo Mới)", type="primary", use_container_width=True):
                if execute_db_chain("UPDATE LogisticsPoints SET status = N'Chờ xử lý' WHERE status = N'Chờ Admin duyệt' AND order_type = N'chuỗi'"):
                    clear_chain_order_caches(); st.rerun()
            if not df_complete.empty and col_b2.button("Duyệt Tất Cả (Hoàn Thành)", type="primary", use_container_width=True):
                if execute_db_chain("UPDATE LogisticsPoints SET status = N'Đã hoàn thành', delivery_status = N'Đã hoàn thành' WHERE delivery_status = N'Đang chờ duyệt' AND order_type = N'chuỗi'"):
                    clear_chain_order_caches(); st.rerun()
            if col_b3.button("Làm mới", use_container_width=True):
                clear_chain_order_caches(); st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)
            cols = st.columns(2)
            idx = 0

            # 1. RENDER THẺ YÊU CẦU TẠO MỚI (Từ Khách Hàng)
            for (creator, t_grp), group in grouped_create:
                point_ids = group['point_id'].tolist()
                time_str = group.iloc[0]['created_at'].strftime("%H:%M - %d/%m/%Y")
                
                card_html = textwrap.dedent(f"""
                    <div style="background-color: #21262d; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 15px; border-bottom: 1px solid #30363d; padding-bottom: 10px;">
                            <span style="background: #1976D2; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; text-transform: uppercase;">
                                <i class="fa-solid fa-box-open"></i> Yêu Cầu Tạo Tuyến
                            </span>
                            <span style="color: #8b949e; font-size: 12px;"><i class="fa-solid fa-clock"></i> {time_str}</span>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <p style="margin: 0; color: #e0e0e0; font-size: 16px;"><i class="fa-solid fa-circle-user" style="color: #1E90FF;"></i> <b>Khách hàng:</b> {creator}</p>
                            <p style="margin: 5px 0 0 0; color: #8b949e; font-size: 14px;"><i class="fa-solid fa-layer-group" style="color: #1976D2;"></i> <b>Quy mô:</b> {len(point_ids)} đơn hàng</p>
                        </div>
                        <div style="background: #1A1C24; padding: 12px; border-radius: 8px; border-left: 4px solid #1976D2;">
                            <p style="margin:0; color: #1976D2; font-size: 12px; font-weight: bold;">DANH SÁCH MÃ ĐƠN TẠO MỚI</p>
                            <p style="margin:0; color: #e0e0e0; font-size: 13px;"><i class="fa-solid fa-hashtag"></i> {", ".join(map(str, point_ids))}</p>
                        </div>
                    </div>
                """)

                with cols[idx % 2]:
                    st.markdown(card_html, unsafe_allow_html=True)
                    btn_col1, btn_col2 = st.columns(2)
                    if btn_col1.button("Duyệt Đơn Mới", key=f"app_cr_{point_ids[0]}", use_container_width=True, type="primary"):
                        placeholders = ','.join(['?'] * len(point_ids))
                        if execute_db_chain(f"UPDATE LogisticsPoints SET status = N'Chờ xử lý' WHERE point_id IN ({placeholders})", point_ids):
                            clear_chain_order_caches(); st.rerun()
                    if btn_col2.button("Từ Chối Mới", key=f"rej_cr_{point_ids[0]}", use_container_width=True):
                        placeholders = ','.join(['?'] * len(point_ids))
                        if execute_db_chain(f"UPDATE LogisticsPoints SET status = N'Từ chối' WHERE point_id IN ({placeholders})", point_ids):
                            clear_chain_order_caches(); st.rerun()
                idx += 1

            # 2. RENDER THẺ YÊU CẦU HOÀN THÀNH (Từ Tài Xế)
            for (driver, t_grp), group in grouped_complete:
                point_ids = group['point_id'].tolist()
                time_str = group.iloc[0]['created_at'].strftime("%H:%M - %d/%m/%Y")
                
                card_html = textwrap.dedent(f"""
                    <div style="background-color: #21262d; border: 1px solid #30363d; border-radius: 12px; padding: 20px; margin-bottom: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 15px; border-bottom: 1px solid #30363d; padding-bottom: 10px;">
                            <span style="background: #FF9800; color: white; padding: 4px 10px; border-radius: 6px; font-size: 11px; font-weight: bold; text-transform: uppercase;">
                                <i class="fa-solid fa-check-double"></i> Yêu Cầu Hoàn Thành
                            </span>
                            <span style="color: #8b949e; font-size: 12px;"><i class="fa-solid fa-clock"></i> {time_str}</span>
                        </div>
                        <div style="margin-bottom: 15px;">
                            <p style="margin: 0; color: #e0e0e0; font-size: 16px;"><i class="fa-solid fa-id-badge" style="color: #FF9800;"></i> <b>Tài xế:</b> {driver}</p>
                            <p style="margin: 5px 0 0 0; color: #8b949e; font-size: 14px;"><i class="fa-solid fa-layer-group" style="color: #FF9800;"></i> <b>Đã giao:</b> {len(point_ids)} đơn hàng</p>
                        </div>
                        <div style="background: #1A1C24; padding: 12px; border-radius: 8px; border-left: 4px solid #FF9800;">
                            <p style="margin:0; color: #FF9800; font-size: 12px; font-weight: bold;">MÃ ĐƠN CHỜ CHỐT KPI</p>
                            <p style="margin:0; color: #e0e0e0; font-size: 13px;"><i class="fa-solid fa-hashtag"></i> {", ".join(map(str, point_ids))}</p>
                        </div>
                    </div>
                """)

                with cols[idx % 2]:
                    st.markdown(card_html, unsafe_allow_html=True)
                    btn_col1, btn_col2 = st.columns(2)
                    if btn_col1.button("Chốt Hoàn Thành", key=f"app_com_{point_ids[0]}", use_container_width=True, type="primary"):
                        placeholders = ','.join(['?'] * len(point_ids))
                        if execute_db_chain(f"UPDATE LogisticsPoints SET status = N'Đã hoàn thành', delivery_status = N'Đã hoàn thành' WHERE point_id IN ({placeholders})", point_ids):
                            clear_chain_order_caches(); st.rerun()
                    if btn_col2.button("Từ Chối Chốt", key=f"rej_com_{point_ids[0]}", use_container_width=True):
                        placeholders = ','.join(['?'] * len(point_ids))
                        if execute_db_chain(f"UPDATE LogisticsPoints SET delivery_status = N'Chờ xác nhận' WHERE point_id IN ({placeholders})", point_ids):
                            clear_chain_order_caches(); st.rerun()
                idx += 1

    # ================== TAB 2: ĐƠN ĐANG CHẠY ==================
    else:
        df_active = get_chain_active_data()

        st.markdown("### <i class='fa-solid fa-map-location-dot' style='color:#4CAF50;'></i> Danh sách điểm giao đang chờ gom", unsafe_allow_html=True)
        if df_active.empty:
            st.info("Hiện không có đơn chuỗi nào đang chờ tài xế nhận hoặc đang lưu thông.")
        else:
            df_display = df_active[['point_id', 'created_by', 'driver_id', 'status', 'lat', 'lon']].copy()
            df_display.columns = ['Mã Đơn', 'Người Đặt', 'Tài Xế Nhận', 'Trạng Thái', 'Vĩ độ', 'Kinh độ']
            def color_st(val):
                return f'color: {"#1976D2" if val == "Chờ xử lý" else "#4CAF50"}; font-weight: bold;'
            st.dataframe(df_display.style.applymap(color_st, subset=['Trạng Thái']), use_container_width=True, hide_index=True)
