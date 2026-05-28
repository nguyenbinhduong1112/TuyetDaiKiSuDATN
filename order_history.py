import streamlit as st
import pandas as pd
import pyodbc
import folium
from streamlit_folium import st_folium
from config import CONN_STR

# --- KẾT NỐI DATABASE VÀ LỌC THEO QUYỀN ---
@st.cache_data(ttl=15)
def get_order_history(username, role):
    try:
        conn = pyodbc.connect(CONN_STR)

        columns = """
            point_id, order_type, created_by, driver_id, created_at,
            status, delivery_status, lat, lon, pickup_lat, pickup_lon
        """

        if role == '3':
            query = f"""
                SELECT TOP (1000) {columns}
                FROM LogisticsPoints
                WHERE created_by = ?
                ORDER BY created_at DESC
            """
            df = pd.read_sql(query, conn, params=[username])
        elif role == '2':
            query = f"""
                SELECT TOP (1000) {columns}
                FROM LogisticsPoints
                WHERE driver_id = ?
                ORDER BY created_at DESC
            """
            df = pd.read_sql(query, conn, params=[username])
        else:
            query = f"""
                SELECT TOP (1000) {columns}
                FROM LogisticsPoints
                ORDER BY created_at DESC
            """
            df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        return pd.DataFrame()


# --- LẤY VỊ TRÍ KHO ---
@st.cache_data(ttl=60)
def _get_warehouse_loc():
    try:
        conn = pyodbc.connect(CONN_STR)
        df = pd.read_sql("SELECT lat, lon FROM WarehouseConfig WHERE id = 1", conn)
        conn.close()
        if not df.empty:
            return [float(df.iloc[0]['lat']), float(df.iloc[0]['lon'])]
    except Exception:
        pass
    return [18.6601, 105.6942]


# --- LẤY VỊ TRÍ TÀI XẾ THỜI GIAN THỰC (KHÔNG CACHE ĐỂ TRACKING) ---
def _get_driver_location(driver_username):
    if not driver_username:
        return None, None
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        cursor.execute(
            "SELECT lat, lon, ISNULL(current_status, N'Ngoại tuyến') AS s, ISNULL(fullname, username) AS fn "
            "FROM userstable WHERE username = ?",
            (driver_username,)
        )
        row = cursor.fetchone(); conn.close()
        if row and row[0] is not None and row[1] is not None:
            return (float(row[0]), float(row[1])), {"status": row[2], "fullname": row[3]}
    except Exception:
        pass
    return None, None


def _is_active_status(status_value):
    """Đơn đang vận chuyển/đang xử lý (chưa hoàn thành/hủy)."""
    if not status_value:
        return False
    s = str(status_value).lower()
    if 'hoàn thành' in s or 'hủy' in s or 'từ chối' in s:
        return False
    return True


# ==========================================
# SECTION: THEO DÕI ĐƠN TRÊN BẢN ĐỒ
# ==========================================
def _render_tracking_map(df_raw, role_str):
    """Render khu vực theo dõi đơn đang vận chuyển trên bản đồ."""
    if df_raw is None or df_raw.empty:
        return

    # Chỉ lấy các đơn đang còn vận chuyển/xử lý
    df_active = df_raw[df_raw['status'].apply(_is_active_status)].copy()
    if df_active.empty:
        return

    st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 10px; margin-top: 10px;">
            <i class="fa-solid fa-route" style="font-size: 26px; margin-right: 12px; color: #1E90FF;"></i>
            <h2 style="margin: 0; font-size: 26px; font-weight: 700; color: white;">Theo dõi đơn trên bản đồ</h2>
        </div>
        <p style="color:#8b949e; margin-top:0; margin-bottom:12px; font-size:13px;">
            Chọn một đơn đang vận chuyển để xem vị trí tài xế và lộ trình giao hàng.
        </p>
    """, unsafe_allow_html=True)

    # Build option labels
    def _fmt_label(row):
        otype = 'COD' if str(row.get('order_type')) == 'lẻ' else 'Chuỗi'
        st_short = str(row.get('status', ''))[:30]
        return f"#{row['point_id']} • {otype} • {st_short}"

    df_active['_label'] = df_active.apply(_fmt_label, axis=1)
    options = df_active['point_id'].tolist()
    labels = dict(zip(df_active['point_id'], df_active['_label']))

    col_pick, col_btn = st.columns([4, 1])
    with col_pick:
        selected_id = st.selectbox(
            "Đơn đang vận chuyển",
            options,
            format_func=lambda x: labels.get(x, str(x)),
            key="tracking_selected_order",
            label_visibility="collapsed",
        )
    with col_btn:
        if st.button("Làm mới", use_container_width=True, key="tracking_refresh_btn"):
            st.rerun()

    row = df_active[df_active['point_id'] == selected_id].iloc[0]
    is_cod = str(row.get('order_type')) == 'lẻ'

    wh_loc = _get_warehouse_loc()
    drop_loc = [float(row['lat']), float(row['lon'])] if pd.notna(row.get('lat')) and pd.notna(row.get('lon')) else None

    pickup_loc = None
    if is_cod and pd.notna(row.get('pickup_lat')) and pd.notna(row.get('pickup_lon')):
        pickup_loc = [float(row['pickup_lat']), float(row['pickup_lon'])]
    else:
        pickup_loc = wh_loc  # Đơn chuỗi: lấy từ kho

    driver_username = row.get('driver_id')
    driver_loc, driver_info = _get_driver_location(driver_username)

    # --- Thông tin tóm tắt ---
    status_txt = str(row.get('status', '—'))
    delivery_txt = str(row.get('delivery_status', '—'))
    drv_label = (driver_info or {}).get('fullname') or driver_username or 'Chờ phân công'
    drv_status = (driver_info or {}).get('status') or '—'

    info_cols = st.columns(4)
    info_cols[0].markdown(
        f"""<div style='background:rgba(30,144,255,0.1);border:1px solid rgba(30,144,255,0.3);
        padding:10px 14px;border-radius:10px;'>
        <div style='color:#8b949e;font-size:12px;'>MÃ ĐƠN</div>
        <div style='color:white;font-weight:700;font-size:18px;'>#{row['point_id']}</div></div>""",
        unsafe_allow_html=True,
    )
    info_cols[1].markdown(
        f"""<div style='background:rgba(255,193,7,0.1);border:1px solid rgba(255,193,7,0.3);
        padding:10px 14px;border-radius:10px;'>
        <div style='color:#8b949e;font-size:12px;'>TRẠNG THÁI</div>
        <div style='color:white;font-weight:700;font-size:14px;'>{status_txt}</div></div>""",
        unsafe_allow_html=True,
    )
    info_cols[2].markdown(
        f"""<div style='background:rgba(76,175,80,0.1);border:1px solid rgba(76,175,80,0.3);
        padding:10px 14px;border-radius:10px;'>
        <div style='color:#8b949e;font-size:12px;'>GIAO HÀNG</div>
        <div style='color:white;font-weight:700;font-size:14px;'>{delivery_txt}</div></div>""",
        unsafe_allow_html=True,
    )
    info_cols[3].markdown(
        f"""<div style='background:rgba(156,39,176,0.1);border:1px solid rgba(156,39,176,0.3);
        padding:10px 14px;border-radius:10px;'>
        <div style='color:#8b949e;font-size:12px;'>TÀI XẾ</div>
        <div style='color:white;font-weight:700;font-size:14px;'>{drv_label}</div>
        <div style='color:#8b949e;font-size:11px;'>{drv_status}</div></div>""",
        unsafe_allow_html=True,
    )

    # --- Render bản đồ ---
    center = driver_loc if driver_loc else (drop_loc if drop_loc else wh_loc)
    m = folium.Map(location=center, zoom_start=14, tiles="cartodbpositron")

    # Kho
    folium.Marker(
        location=wh_loc,
        icon=folium.DivIcon(html='<div style="color:white;background:#555;border-radius:50%;'
                                 'width:34px;height:34px;display:flex;align-items:center;justify-content:center;'
                                 'font-weight:bold;border:2px solid white;box-shadow:0 0 10px rgba(0,0,0,0.5);'
                                 'font-size:11px;">KHO</div>'),
        tooltip="Kho trung tâm",
    ).add_to(m)

    # Điểm lấy (chỉ vẽ riêng nếu là COD và khác kho)
    if is_cod and pickup_loc and pickup_loc != wh_loc:
        folium.Marker(
            location=pickup_loc,
            icon=folium.DivIcon(html='<div style="color:white;background:#FF9800;border-radius:50%;'
                                     'width:32px;height:32px;display:flex;align-items:center;justify-content:center;'
                                     'font-weight:bold;border:2px solid white;box-shadow:0 0 10px rgba(0,0,0,0.5);'
                                     'font-size:11px;">LẤY</div>'),
            tooltip="Điểm lấy hàng",
        ).add_to(m)

    # Điểm giao
    if drop_loc:
        folium.Marker(
            location=drop_loc,
            icon=folium.DivIcon(html='<div style="color:white;background:#28a745;border-radius:50%;'
                                     'width:32px;height:32px;display:flex;align-items:center;justify-content:center;'
                                     'font-weight:bold;border:2px solid white;box-shadow:0 0 10px rgba(0,0,0,0.5);'
                                     'font-size:11px;">GIAO</div>'),
            tooltip=f"Điểm giao - đơn #{row['point_id']}",
        ).add_to(m)

    # Lộ trình lấy → giao (đường mục tiêu)
    if pickup_loc and drop_loc:
        folium.PolyLine(
            locations=[pickup_loc, drop_loc],
            color="#1976D2", weight=3, dash_array="6,8", opacity=0.8,
            tooltip="Lộ trình dự kiến",
        ).add_to(m)

    # Vị trí tài xế + đoạn thẳng tới điểm giao
    if driver_loc:
        folium.Marker(
            location=list(driver_loc),
            icon=folium.Icon(color="blue", icon="truck", prefix="fa"),
            tooltip=f"Tài xế: {drv_label} ({drv_status})",
        ).add_to(m)
        if drop_loc:
            folium.PolyLine(
                locations=[list(driver_loc), drop_loc],
                color="#FF4B4B", weight=4, opacity=0.85,
                tooltip="Khoảng cách tài xế → điểm giao",
            ).add_to(m)
    else:
        st.info("Tài xế chưa cập nhật vị trí (đang ngoại tuyến hoặc chưa nhận đơn).")

    # Tự fit viewport
    pts = [p for p in [wh_loc, pickup_loc, drop_loc, list(driver_loc) if driver_loc else None] if p]
    if len(pts) >= 2:
        try:
            m.fit_bounds(pts, padding=(30, 30))
        except Exception:
            pass

    st_folium(m, width="100%", height=480, key=f"tracking_map_{selected_id}", returned_objects=[])

    st.markdown("<hr style='border-color:#333; margin: 25px 0 15px 0;'>", unsafe_allow_html=True)


# ==========================================
# HÀM RENDER CHÍNH (GỌI TỪ CÁC FILE CÀNH)
# ==========================================
def render_history(username, role_str):
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px; z-index: 2; position: relative;">
            <i class="fa-solid fa-clock-rotate-left" style="font-size: 38px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 40px; font-weight: 700; color: white;">Lịch sử Giao dịch</h1>
        </div>
    """, unsafe_allow_html=True)

    df = get_order_history(username, role_str)
    
    if df.empty:
        if role_str == '2':
            st.info("Chưa có dữ liệu lịch sử nhận chuyến của bạn. (Lưu ý: Hệ thống cần có cột dữ liệu phân công để định danh tài xế).")
        else:
            st.info("Chưa có dữ liệu đơn hàng nào trong lịch sử.")
        return

    # --- THEO DÕI ĐƠN TRÊN BẢN ĐỒ (dùng dữ liệu thô trước khi format HTML) ---
    _render_tracking_map(df, role_str)

    # --- XỬ LÝ DỮ LIỆU ---
    if 'driver_id' not in df.columns: df['driver_id'] = "Chờ phân công..."
    if 'admin_id' not in df.columns: df['admin_id'] = "Hệ thống tự động"

    # [FIX LOGIC QUAN TRỌNG]: Ép đồng bộ trạng thái Hủy/Từ chối
    # Nếu hệ thống đã Hủy/Từ chối, trạng thái giao hàng không thể là "Chờ xếp xe"
    mask_cancelled = df['status'].str.lower().str.contains('hủy|từ chối', na=False)
    df.loc[mask_cancelled, 'delivery_status'] = 'Đã hủy'

    # Format thời gian & Loại đơn
    df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%H:%M - %d/%m/%Y')
    df['order_type'] = df['order_type'].apply(lambda x: '<i class="fa-solid fa-bolt" style="color:#FFC107;"></i> Hỏa tốc (COD)' if str(x) == 'lẻ' else ('<i class="fa-solid fa-cubes" style="color:#1976D2;"></i> Đơn Chuỗi' if str(x) == 'chuỗi' else 'Mặc định'))
    
    # Hàm gắn FontAwesome tự động theo trạng thái
    def map_status_fa(status):
        s = str(status).lower()
        if 'hoàn thành' in s: return f'<span style="color:#28a745; font-weight:bold;"><i class="fa-solid fa-circle-check"></i> {status}</span>'
        elif 'từ chối' in s or 'hủy' in s: return f'<span style="color:#FF4B4B; font-weight:bold;"><i class="fa-solid fa-circle-xmark"></i> {status}</span>'
        elif 'chờ' in s: return f'<span style="color:#FFC107; font-weight:bold;"><i class="fa-solid fa-hourglass-half"></i> {status}</span>'
        elif 'đang' in s: return f'<span style="color:#1E90FF; font-weight:bold;"><i class="fa-solid fa-truck-fast"></i> {status}</span>'
        return f'<span style="color:#A0AEC0;"><i class="fa-solid fa-thumbtack"></i> {status}</span>'

    df['status'] = df['status'].apply(map_status_fa)
    df['delivery_status'] = df['delivery_status'].apply(map_status_fa)

    # --- TÍNH TOÁN KPI THỐNG KÊ ---
    total = len(df)
    completed = len(df[df['status'].str.contains('fa-circle-check', na=False)])
    pending = total - completed

    # --- VẼ GIAO DIỆN THẺ KPI (BẰNG FONTAWESOME) ---
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"""
        <div style="background: rgba(25, 118, 210, 0.15); border: 1px solid rgba(25, 118, 210, 0.3); padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <h4 style="color: #8b949e; margin: 0; font-size: 13px; font-weight: bold; letter-spacing: 1px;"><i class="fa-solid fa-layer-group"></i> TỔNG SỐ ĐƠN</h4>
            <h2 style="color: #4DA6FF; margin: 5px 0 0 0; font-size: 35px; font-weight: 900;">{total}</h2>
        </div>
    """, unsafe_allow_html=True)
    c2.markdown(f"""
        <div style="background: rgba(40, 167, 69, 0.15); border: 1px solid rgba(40, 167, 69, 0.3); padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <h4 style="color: #8b949e; margin: 0; font-size: 13px; font-weight: bold; letter-spacing: 1px;"><i class="fa-solid fa-clipboard-check"></i> ĐÃ HOÀN THÀNH</h4>
            <h2 style="color: #28a745; margin: 5px 0 0 0; font-size: 35px; font-weight: 900;">{completed}</h2>
        </div>
    """, unsafe_allow_html=True)
    c3.markdown(f"""
        <div style="background: rgba(255, 193, 7, 0.15); border: 1px solid rgba(255, 193, 7, 0.3); padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
            <h4 style="color: #8b949e; margin: 0; font-size: 13px; font-weight: bold; letter-spacing: 1px;"><i class="fa-solid fa-spinner fa-spin"></i> ĐANG XỬ LÝ</h4>
            <h2 style="color: #ffc107; margin: 5px 0 0 0; font-size: 35px; font-weight: 900;">{pending}</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("") # Dãn dòng

    # --- CHIA CỘT HIỂN THỊ TÙY QUYỀN ---
    if role_str == '3':
        # Khách hàng: KHÔNG CÓ cột Admin
        cols_to_show = [('point_id', 'Mã Đơn'), ('order_type', 'Loại'), ('created_by', 'Khách hàng'), ('driver_id', 'Tài xế'), ('created_at', 'Thời gian'), ('status', 'Trạng thái HT'), ('delivery_status', 'Trạng thái Giao')]
    else:
        # Admin & Tài xế: Có thêm cột Admin duyệt
        cols_to_show = [('point_id', 'Mã Đơn'), ('order_type', 'Loại'), ('created_by', 'Khách hàng'), ('driver_id', 'Tài xế'), ('admin_id', 'Admin duyệt'), ('created_at', 'Thời gian'), ('status', 'Trạng thái HT'), ('delivery_status', 'Trạng thái Giao')]

    # --- HÀM RENDER BẢNG HTML ---
    def render_custom_table(dataframe):
        html = """
        <style>
            .glass-table { width: 100%; border-collapse: collapse; background: rgba(26, 28, 36, 0.6); border-radius: 10px; overflow: hidden; color: white; text-align: left; font-size: 14px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.05); }
            .glass-table th { background: rgba(0, 0, 0, 0.4); padding: 15px 12px; color: #8b949e; font-weight: bold; text-transform: uppercase; border-bottom: 1px solid rgba(255,255,255,0.1); font-size: 12px; }
            .glass-table td { padding: 15px 12px; border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.2s; }
            .glass-table tr:hover td { background: rgba(255, 255, 255, 0.05); }
        </style>
        <table class="glass-table"><thead><tr>
        """
        for _, col_name in cols_to_show:
            html += f"<th>{col_name}</th>"
        html += "</tr></thead><tbody>"
        
        for _, row in dataframe.iterrows():
            html += "<tr>"
            for col_key, _ in cols_to_show:
                val = row.get(col_key, "N/A")
                html += f"<td>{val}</td>"
            html += "</tr>"
            
        html += "</tbody></table>"
        return html

    # --- CHIA TAB DỮ LIỆU ---
    t1, t2, t3 = st.tabs(["TẤT CẢ GIAO DỊCH", "ĐANG XỬ LÝ & CHỜ DUYỆT", "ĐÃ HOÀN TẤT"])
    
    with t1:
        st.markdown(render_custom_table(df), unsafe_allow_html=True)
    with t2:
        df_pending = df[~df['status'].str.contains('fa-circle-check', na=False)]
        if not df_pending.empty: st.markdown(render_custom_table(df_pending), unsafe_allow_html=True)
        else: st.success("Tuyệt vời! Không có đơn hàng nào đang tồn đọng.")
    with t3:
        df_done = df[df['status'].str.contains('fa-circle-check', na=False)]
        if not df_done.empty: st.markdown(render_custom_table(df_done), unsafe_allow_html=True)
        else: st.info("Chưa có đơn hàng nào được hoàn thành.")

    # --- FOOTER CẢNH BÁO CHỈ ĐỌC ---
    role_name = 'Quản trị viên' if role_str == '1' else ('Tài xế' if role_str == '2' else 'Khách hàng')
    st.markdown(f"""
        <div style="background-color: rgba(255, 255, 255, 0.05); padding: 12px 15px; border-radius: 8px; margin-top: 20px; border-left: 4px solid #8b949e;">
            <span style="color: #e0e0e0; font-size: 13px;"><i class="fa-solid fa-shield-halved" style="color: #8b949e; margin-right: 5px;"></i> Dữ liệu được bảo vệ bằng mã hóa. Chế độ xem hiện tại: <b>{role_name}</b> (Read Only). Lịch sử giao dịch không thể chỉnh sửa hay xóa bỏ.</span>
        </div>
    """, unsafe_allow_html=True)
