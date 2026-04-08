import streamlit as st
import os

# 1. CẤU HÌNH GLOBAL (Chỉ được gọi 1 lần duy nhất ở file chạy lệnh)
st.set_page_config(
    layout="wide", 
    page_title="Hệ thống quản lý logistics", 
    page_icon=os.path.join("img", "4D5185D2-0AD7-49AC-B7B2-4E94C13DB13C.png")
)

def main():
    # 2. Bắt ngay URL trước khi bất cứ giao diện nào kịp hiện ra
    query_params = st.query_params

    # Nếu phát hiện F5 (URL vẫn còn param), lập tức "bơm" vào session_state
    if "customer" in query_params and "role" in query_params:
        st.session_state.customer = query_params["customer"]
        st.session_state.role = str(query_params["role"])

    # 3. BỘ ĐỊNH TUYẾN (ROUTER) SIÊU TỐC
    current_role = st.session_state.get("role", None)

    if current_role == "1":
        # Load trang Admin
        import admin 
        admin.render_page()
        
    elif current_role == "2":
        # Load trang Driver (Tài xế)
        import driver
        driver.render_page()
        
    elif current_role == "3":
        # [MỚI THÊM]: Load trang Customer (Khách hàng)
        import customer
        customer.render_page()
        
    else:
        # Xóa các biến rác nếu có và cho hiện màn hình Login
        st.session_state.role = None
        st.session_state.customer = None
        import login
        login.render_page()

if __name__ == "__main__":
    main()