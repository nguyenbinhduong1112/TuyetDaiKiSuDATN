import streamlit as st
import os
import jwt

# Khóa bí mật để giải mã Token (Tuyệt đối giữ kín, hai bên khóa phải giống nhau)
SECRET_KEY = "umbrella_logistics_super_secret_key_2026"

def main():
    jwt_error = None # Biến để cất thông báo lỗi, khoan in ra vội

    # ==========================================
    # 1. BỘ GIẢI MÃ TOKEN (CHỐNG VĂNG KHI F5)
    # ==========================================
    # Việc này xử lý ngầm (không in ra UI), nên hoàn toàn hợp lệ khi đặt trước set_page_config
    if "token" in st.query_params:
        encrypted_token = st.query_params["token"]
        try:
            # Giải mã token lấy dữ liệu
            decoded_data = jwt.decode(encrypted_token, SECRET_KEY, algorithms=["HS256"])
            
            # Khôi phục trí nhớ cho RAM (Session State) từ dữ liệu an toàn đã giải mã
            if "role" not in st.session_state:
                st.session_state.role = decoded_data.get("role")
            if "customer" not in st.session_state:
                st.session_state.customer = decoded_data.get("username")
                
        except jwt.ExpiredSignatureError:
            jwt_error = "Phiên đăng nhập đã hết hạn (Quá 30 ngày). Vui lòng đăng nhập lại."
            st.query_params.clear() # Xóa URL rác
        except jwt.InvalidTokenError:
            jwt_error = "Cảnh báo bảo mật: Link không hợp lệ hoặc đã bị can thiệp!"
            st.query_params.clear()

    # Ép kiểu về chuỗi (string) để so sánh cho chắc chắn
    current_role = str(st.session_state.get("role", "")) if st.session_state.get("role") else None

    # ==========================================
    # 2. ĐẶT TÊN TAB THEO TỪNG QUYỀN TRUY CẬP
    # ==========================================
    if current_role == "1":
        dynamic_title = "Quản trị viên | VinhUmbrella"
    elif current_role == "2":
        dynamic_title = "Tài xế vận hành | VinhUmbrella"
    elif current_role == "3":
        dynamic_title = "Khách hàng | VinhUmbrella"
    else:
        dynamic_title = "Đăng nhập hệ thống | VinhUmbrella"

    # [QUAN TRỌNG]: Lệnh set_page_config NẰM Ở ĐÂY để nhận được dynamic_title
    st.set_page_config(
        layout="wide", 
        page_title=dynamic_title, 
        page_icon=os.path.join("img", "4D5185D2-0AD7-49AC-B7B2-4E94C13DB13C.png")
    )

    # Xả cái lỗi lúc nãy ra màn hình (nếu có) sau khi UI đã được khởi tạo an toàn
    if jwt_error:
        st.error(jwt_error)

    # ==========================================
    # 3. BỘ ĐỊNH TUYẾN (ROUTER) SIÊU TỐC
    # ==========================================
    if current_role == "1":
        # Load trang Admin
        import admin 
        admin.render_page()
        
    elif current_role == "2":
        # Load trang Driver (Tài xế)
        import driver
        driver.render_page()
        
    elif current_role == "3":
        # Load trang Customer (Khách hàng)
        import customer
        customer.render_page()
        
    else:
        # Nếu chưa đăng nhập hoặc token sai -> Xóa sạch biến rác và gọi Login
        st.session_state.role = None
        st.session_state.customer = None
        import login
        login.render_page()

if __name__ == "__main__":
    main()