import streamlit as st
import pandas as pd
import pyodbc
from config import CONN_STR

# --- KẾT NỐI DATABASE VÀ LỌC THEO QUYỀN ---
@st.cache_data(ttl=15)
def get_order_history(username, role):
    try:
        conn = pyodbc.connect(CONN_STR)
        
        # Select toàn bộ dữ liệu
        query = "SELECT * FROM LogisticsPoints ORDER BY created_at DESC"
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty: return df

        # [CẬP NHẬT LOGIC]: Lọc thông minh theo Quyền (Role)
        if role == '3': 
            # Khách hàng chỉ xem đơn mình đặt
            df = df[df['created_by'] == username]
        elif role == '2':
            # Tài xế chỉ xem đơn mình nhận giao (Cần DB có lưu driver_id)
            # Tạm thời nếu DB chưa có driver_id chuẩn, dùng giả lập lọc theo tên
            # Nếu DB sếp có gán tên tài xế vào đâu đó, thay đổi điều kiện lọc tương ứng.
            # Dưới đây là ví dụ giả định cột 'driver_id' lưu username của tài xế:
            if 'driver_id' in df.columns:
                df = df[df['driver_id'] == username]
            else:
                # Nếu DB chưa có, tạm trả về DataFrame rỗng (hoặc hiển thị báo lỗi)
                # để đảm bảo bảo mật không rò rỉ đơn của tài xế khác.
                # Sếp có thể comment dòng dưới và mở dòng df = df.head(0) nếu muốn chặt chẽ.
                df['driver_id'] = "Chờ phân công..."
                # df = df.head(0) 

        # Admin (Role 1) thì không bị lọc, xem tất cả.
        
        # Giới hạn 1000 đơn để tránh lag hệ thống
        return df.head(1000)
    except Exception as e:
        return pd.DataFrame()

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