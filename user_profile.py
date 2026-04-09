import streamlit as st
import pandas as pd
import pyodbc
from config import CONN_STR

# --- CÁC HÀM TƯƠNG TÁC DATABASE ---
@st.cache_data(ttl=10)
def get_user_data(username):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        cursor.execute("SELECT username, ISNULL(fullname, username) as fullname, role, ISNULL(current_status, 'Ngoại tuyến') as status FROM userstable WHERE username=?", (username,))
        row = cursor.fetchone(); conn.close()
        return {"username": row[0], "fullname": row[1], "role": str(row[2]), "status": row[3]} if row else None
    except: return None

@st.cache_data(ttl=15)
def get_user_stats(username, role):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        if role == '3': # Khách hàng -> Đếm đơn đã đặt
            cursor.execute("SELECT COUNT(*) FROM LogisticsPoints WHERE created_by=?", (username,))
        elif role == '2': # Tài xế -> Đếm đơn đã giao
            cursor.execute("SELECT COUNT(*) FROM LogisticsPoints WHERE status=N'Đã hoàn thành'")
        else: # Admin -> Đếm tổng user
            cursor.execute("SELECT COUNT(*) FROM userstable")
        count = cursor.fetchone()[0]; conn.close()
        return count
    except: return 0

def update_password_or_name(username, new_name, new_pass):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        if new_pass:
            cursor.execute("UPDATE userstable SET fullname=?, password=? WHERE username=?", (new_name, new_pass, username))
        else:
            cursor.execute("UPDATE userstable SET fullname=? WHERE username=?", (new_name, username))
        conn.commit(); conn.close()
        return True
    except: return False

# --- HÀM CHO ADMIN (CRUD TOÀN HỆ THỐNG) ---
@st.cache_data(ttl=5)
def get_all_users_for_admin():
    try:
        conn = pyodbc.connect(CONN_STR)
        df = pd.read_sql("SELECT username, ISNULL(fullname, username) as fullname, role, is_locked FROM userstable", conn)
        df['role'] = df['role'].astype(str) 
        conn.close()
        return df
    except: return pd.DataFrame()

def admin_delete_user(username):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        cursor.execute("DELETE FROM userstable WHERE username=?", (username,))
        conn.commit(); conn.close()
        return True
    except: return False

def admin_update_lock_status(username, is_locked):
    try:
        conn = pyodbc.connect(CONN_STR); cursor = conn.cursor()
        cursor.execute("UPDATE userstable SET is_locked=? WHERE username=?", (is_locked, username))
        conn.commit(); conn.close()
        return True
    except: return False

# ==========================================
# HÀM RENDER CHÍNH (ĐƯỢC GỌI TỪ CÁC FILE KHÁC)
# ==========================================
def render_profile(username, role_str):
    user_info = get_user_data(username)
    if not user_info:
        st.error("Không tìm thấy dữ liệu người dùng!")
        return

    stats_count = get_user_stats(username, role_str)

    # ĐỊNH DẠNG THEO QUYỀN
    role_map = {
        '1': {"name": "Quản trị viên Hệ thống", "color": "#FF4B4B", "icon": "fa-user-shield", "stat_label": "Tổng tài khoản Database"},
        '2': {"name": "Tài xế Vận hành", "color": "#1976D2", "icon": "fa-id-badge", "stat_label": "Chuyến đã hoàn thành"},
        '3': {"name": "Khách hàng Đối tác", "color": "#28a745", "icon": "fa-user", "stat_label": "Đơn hàng đã tạo"}
    }
    r_data = role_map.get(role_str, {"name": "Unknown", "color": "#8b949e", "icon": "fa-user", "stat_label": "Dữ liệu"})

    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px; z-index: 2; position: relative;">
            <i class="fa-solid fa-address-card" style="font-size: 38px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 40px; font-weight: 700; color: white;">Hồ sơ Cá nhân</h1>
        </div>
    """, unsafe_allow_html=True)

    col_card, col_action = st.columns([1.2, 2.5], gap="large")

    # 1. THẺ CĂN CƯỚC SỐ (DÙNG CHUNG CHO MỌI QUYỀN)
    with col_card:
        st.markdown(f"""
        <div style="background: linear-gradient(145deg, rgba(26,28,36,0.9) 0%, rgba(18,20,28,0.9) 100%); border-radius: 20px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 15px 35px rgba(0,0,0,0.5); text-align: center; position: relative; overflow: hidden;">
            <div style="position: absolute; top: -50px; left: -50px; width: 100px; height: 100px; background: {r_data['color']}; filter: blur(50px); opacity: 0.3;"></div>
            <div style="width: 100px; height: 100px; border-radius: 50%; background: #2A2D3E; border: 3px solid {r_data['color']}; margin: 0 auto 15px auto; display: flex; align-items: center; justify-content: center; box-shadow: 0 0 20px {r_data['color']}40;">
                <i class="fa-solid {r_data['icon']}" style="font-size: 45px; color: {r_data['color']};"></i>
            </div>
            <h2 style="color: white; margin: 0; font-size: 24px; font-weight: 800;">{user_info['fullname']}</h2>
            <p style="color: #8b949e; font-size: 14px; margin-top: 5px; font-family: monospace;">@{user_info['username']}</p>
            <div style="background: rgba(255,255,255,0.05); padding: 5px 15px; border-radius: 30px; display: inline-block; border: 1px solid {r_data['color']}50; margin-bottom: 20px;">
                <span style="color: {r_data['color']}; font-weight: bold; font-size: 13px;">{r_data['name']}</span>
            </div>
            <div style="display: flex; justify-content: space-around; border-top: 1px solid rgba(255,255,255,0.05); padding-top: 15px;">
                <div>
                    <div style="color: #8b949e; font-size: 12px; text-transform: uppercase;">{r_data['stat_label']}</div>
                    <div style="color: white; font-size: 22px; font-weight: 900;">{stats_count}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 2. KHU VỰC THAO TÁC (TÙY BIẾN THEO QUYỀN)
    with col_action:
        # ==============================================================
        # GIAO DIỆN ADMIN (QUYỀN 1)
        # ==============================================================
        if role_str == '1':
            tabs = st.tabs(["THÔNG TIN CỦA TÔI", "QUẢN TRỊ DATABASE ĐỊNH DANH"])
            
            with tabs[0]: 
                # [GIẢI PHÁP]: Thay thế Form bằng Container thông thường
                with st.container(border=True):
                    st.markdown("### <i class='fa-solid fa-user-pen' style='color:#FF4B4B;'></i> Cập nhật thông tin", unsafe_allow_html=True)
                    new_fn = st.text_input("Họ và Tên:", value=user_info['fullname'], key="admin_fn")
                    
                    with st.expander("Thay đổi mật khẩu đăng nhập"):
                        st.markdown("<small style='color:#8b949e;'>Để trống nếu bạn không muốn đổi mật khẩu.</small>", unsafe_allow_html=True)
                        new_pw = st.text_input("Mật khẩu mới:", type="password", key="admin_pw1")
                        confirm_pw = st.text_input("Xác nhận lại mật khẩu mới:", type="password", key="admin_pw2")
                        
                    st.write("") 
                    if st.button("LƯU THAY ĐỔI CÁ NHÂN", type="primary", key="admin_save"):
                        if new_pw or confirm_pw:
                            if new_pw != confirm_pw:
                                st.error("Mật khẩu xác nhận không khớp! Vui lòng thử lại.")
                            else:
                                if update_password_or_name(username, new_fn, new_pw):
                                    get_user_data.clear(); st.success("Cập nhật thành công!"); st.rerun()
                                else: st.error("Lỗi cập nhật Database!")
                        else:
                            if update_password_or_name(username, new_fn, None):
                                get_user_data.clear(); st.success("Cập nhật thành công!"); st.rerun()
                            else: st.error("Lỗi cập nhật Database!")

            with tabs[1]:
                st.markdown("### <i class='fa-solid fa-server' style='color:#FF4B4B;'></i> Phân hệ Quản trị Tài khoản", unsafe_allow_html=True)
                df_all = get_all_users_for_admin()
                df_all['Trạng thái'] = df_all['is_locked'].apply(lambda x: 'Bị Khóa' if x == 1 else 'Hoạt động')
                
                sub_tabs = st.tabs(["QUẢN TRỊ VIÊN", "TÀI XẾ", "KHÁCH HÀNG"])
                
                with sub_tabs[0]:
                    st.markdown("#### <i class='fa-solid fa-user-shield' style='color:#FF4B4B;'></i> Lực lượng Quản trị", unsafe_allow_html=True)
                    df_admins = df_all[df_all['role'] == '1'] 
                    st.dataframe(df_admins[['username', 'fullname', 'Trạng thái']], use_container_width=True, hide_index=True)
                    st.info("⚠️ Chế độ Chỉ xem (Read-Only): Admin không thể tự Khóa hay Xóa tài khoản đồng cấp.")

                with sub_tabs[1]:
                    st.markdown("#### <i class='fa-solid fa-truck-fast' style='color:#1976D2;'></i> Đối tác Vận hành", unsafe_allow_html=True)
                    df_drivers = df_all[df_all['role'] == '2'] 
                    st.dataframe(df_drivers[['username', 'fullname', 'Trạng thái']], use_container_width=True, hide_index=True)
                    
                    if not df_drivers.empty:
                        st.markdown("##### <i class='fa-solid fa-sliders' style='color:#8b949e;'></i> Thao tác Tài khoản", unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        with c1:
                            target_driver = st.selectbox("Chọn Tài xế:", df_drivers['username'].tolist(), key="sel_drv")
                            current_lock_drv = df_drivers[df_drivers['username'] == target_driver]['is_locked'].values[0]
                        with c2:
                            st.write(""); st.write("") 
                            col_btn1, col_btn2 = st.columns(2)
                            lock_btn_label = "MỞ KHÓA" if current_lock_drv == 1 else "KHÓA TÀI KHOẢN"
                            if col_btn1.button(lock_btn_label, use_container_width=True, key="lock_drv"):
                                new_state = 0 if current_lock_drv == 1 else 1
                                if admin_update_lock_status(target_driver, new_state):
                                    get_all_users_for_admin.clear(); st.rerun()
                                    
                            with col_btn2.popover("XÓA", use_container_width=True):
                                st.warning(f"Xác nhận xóa vĩnh viễn @{target_driver}?")
                                if st.button("XÓA NGAY", type="primary", use_container_width=True, key="del_drv"):
                                    if admin_delete_user(target_driver):
                                        get_all_users_for_admin.clear(); get_user_stats.clear(); st.rerun()

                with sub_tabs[2]:
                    st.markdown("#### <i class='fa-solid fa-users' style='color:#28a745;'></i> Khách hàng", unsafe_allow_html=True)
                    df_customers = df_all[df_all['role'] == '3'] 
                    st.dataframe(df_customers[['username', 'fullname', 'Trạng thái']], use_container_width=True, hide_index=True)
                    
                    if not df_customers.empty:
                        st.markdown("##### <i class='fa-solid fa-sliders' style='color:#8b949e;'></i> Thao tác Tài khoản", unsafe_allow_html=True)
                        c3, c4 = st.columns(2)
                        with c3:
                            target_cust = st.selectbox("Chọn Khách hàng:", df_customers['username'].tolist(), key="sel_cust")
                            current_lock_cust = df_customers[df_customers['username'] == target_cust]['is_locked'].values[0]
                        with c4:
                            st.write(""); st.write("") 
                            col_btn3, col_btn4 = st.columns(2)
                            lock_btn_label_c = "MỞ KHÓA" if current_lock_cust == 1 else "KHÓA TÀI KHOẢN"
                            if col_btn3.button(lock_btn_label_c, use_container_width=True, key="lock_cust"):
                                new_state = 0 if current_lock_cust == 1 else 1
                                if admin_update_lock_status(target_cust, new_state):
                                    get_all_users_for_admin.clear(); st.rerun()
                                    
                            with col_btn4.popover("XÓA", use_container_width=True):
                                st.warning(f"Xác nhận xóa vĩnh viễn @{target_cust}?")
                                if st.button("XÓA NGAY", type="primary", use_container_width=True, key="del_cust"):
                                    if admin_delete_user(target_cust):
                                        get_all_users_for_admin.clear(); get_user_stats.clear(); st.rerun()

        # ==============================================================
        # GIAO DIỆN TÀI XẾ & KHÁCH HÀNG (QUYỀN 2 & 3)
        # ==============================================================
        else:
            # [GIẢI PHÁP]: Thay thế Form bằng Container thông thường
            with st.container(border=True):
                st.markdown("### <i class='fa-solid fa-user-pen' style='color:#FF4B4B;'></i> Cài đặt bảo mật", unsafe_allow_html=True)
                new_fn = st.text_input("Tên hiển thị trên hệ thống:", value=user_info['fullname'], key="user_fn")
                
                with st.expander("Thay đổi mật khẩu đăng nhập"):
                    st.markdown("<small style='color:#8b949e;'>Để trống nếu bạn không muốn đổi mật khẩu.</small>", unsafe_allow_html=True)
                    new_pw = st.text_input("Mật khẩu mới:", type="password", key="user_pw1")
                    confirm_pw = st.text_input("Xác nhận lại mật khẩu mới:", type="password", key="user_pw2")

                st.write("") 
                if st.button("LƯU THAY ĐỔI CÁ NHÂN", type="primary", use_container_width=True, key="user_save"):
                    if new_pw or confirm_pw:
                        if new_pw != confirm_pw:
                            st.error("Mật khẩu xác nhận không khớp! Vui lòng thử lại.")
                        else:
                            if update_password_or_name(username, new_fn, new_pw):
                                get_user_data.clear(); st.success("Cập nhật thành công!"); st.rerun()
                            else: st.error("Lỗi cập nhật Database!")
                    else:
                        if update_password_or_name(username, new_fn, None):
                            get_user_data.clear(); st.success("Cập nhật thành công!"); st.rerun()
                        else: st.error("Lỗi cập nhật Database!")