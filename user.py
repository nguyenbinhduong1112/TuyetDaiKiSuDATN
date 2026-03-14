import streamlit as st

st.title("🛒 TRANG MUA SẮM (USER)")
st.info("Trang này sẽ phát triển sau: Xem sản phẩm, thêm vào giỏ hàng, theo dõi đơn hàng cá nhân...")

if st.button("🚪 Đăng xuất"):
    st.session_state.role = None
    st.rerun()