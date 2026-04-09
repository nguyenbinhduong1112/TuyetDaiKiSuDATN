import streamlit as st
import random
import requests
from datetime import datetime

# --- COMBINE API: THỜI TIẾT + CHẤT LƯỢNG KHÔNG KHÍ (AQI) ---
@st.cache_data(ttl=300) # Làm mới mỗi 5 phút
def get_ultimate_weather():
    try:
        # Tọa độ TP Vinh
        lat, lon = 18.6733, 105.6813
        
        # 1. API Thời tiết nâng cao (Lấy cả Tầm nhìn xa, Ngày/Đêm, Lượng mưa)
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,apparent_temperature,is_day,precipitation,weather_code,relative_humidity_2m,wind_speed_10m,visibility&timezone=Asia%2FBangkok"
        w_res = requests.get(w_url, timeout=5).json()
        current = w_res['current']
        
        temp = current['temperature_2m']
        feels_like = current['apparent_temperature']
        humid = current['relative_humidity_2m']
        wind = current['wind_speed_10m']
        w_code = current['weather_code']
        is_day = current['is_day']
        visibility = current.get('visibility', 10000) / 1000 # Chuyển mét sang km
        
        # 2. API Chất lượng không khí (AQI & Bụi mịn PM2.5)
        aqi_url = f"https://air-quality-api.open-meteo.com/v1/air-quality?latitude={lat}&longitude={lon}&current=us_aqi,pm2_5&timezone=Asia%2FBangkok"
        try:
            aqi_res = requests.get(aqi_url, timeout=5).json()
            aqi = aqi_res['current']['us_aqi']
            pm25 = aqi_res['current']['pm2_5']
        except:
            aqi, pm25 = 50, 15 # Mặc định nếu API AQI nghẽn

        # Logic AQI
        if aqi <= 50: aqi_text, aqi_color = "Tốt", "#00e400"
        elif aqi <= 100: aqi_text, aqi_color = "Trung bình", "#ffff00"
        elif aqi <= 150: aqi_text, aqi_color = "Kém", "#ff7e00"
        else: aqi_text, aqi_color = "Xấu", "#ff0000"

        # Logic Thời tiết & Icon UI xịn xò
        advice = "Đường xá thuận lợi, chúc tài xế thượng lộ bình an!"
        glow_color = "rgba(25, 118, 210, 0.4)" # Mặc định xanh dương
        
        if w_code in [0, 1]: 
            w_text = "Trời quang mây tạnh" if is_day else "Trời trong, trăng thanh"
            icon = "fa-sun" if is_day else "fa-moon"
            color = "#FFD700" if is_day else "#E0E0E0"
            glow_color = "rgba(255, 215, 0, 0.3)" if is_day else "rgba(224, 224, 224, 0.2)"
            if temp > 32: advice = "Nắng gắt đổ lửa, tài xế nhớ mặc áo chống nắng và uống nhiều nước!"
            
        elif w_code in [2, 3]: 
            w_text = "Nhiều mây rải rác"
            icon = "fa-cloud-sun" if is_day else "fa-cloud-moon"
            color = "#F0E68C"
        elif w_code in [45, 48]: 
            w_text = "Sương mù dày đặc"
            icon = "fa-smog"; color = "#B0C4DE"
            advice = "Sương mù che khuất tầm nhìn, bật đèn sương mù và đi chậm!"
            glow_color = "rgba(176, 196, 222, 0.3)"
        elif w_code in [51, 53, 55, 61, 63, 65]: 
            w_text = "Có mưa rả rích"
            icon = "fa-cloud-rain"; color = "#4DA6FF"
            advice = "Đường ướt trơn trượt, giảm tốc độ và bóp phanh sớm!"
            glow_color = "rgba(77, 166, 255, 0.4)"
        elif w_code in [80, 81, 82, 95, 96, 99]: 
            w_text = "Giông bão sấm chớp"
            icon = "fa-cloud-bolt"; color = "#9370DB"
            advice = "CẢNH BÁO BÃO: Tránh đỗ xe dưới gốc cây to, chú ý ngập lụt!"
            glow_color = "rgba(147, 112, 219, 0.5)"
        else: 
            w_text = "Nhiều mây"; icon = "fa-cloud"; color = "#A0AEC0"

        if aqi > 100: advice += " Bụi mịn PM2.5 cao, nhớ đeo khẩu trang!"

        return temp, feels_like, humid, wind, w_text, icon, color, visibility, aqi, aqi_text, aqi_color, advice, glow_color
    except Exception as e:
        return "--", "--", "--", "--", "Mất kết nối trạm", "fa-triangle-exclamation", "#FF4B4B", "--", "--", "Lỗi", "#FF4B4B", "Không lấy được dữ liệu thời tiết, lái xe cẩn thận!", "rgba(255, 75, 75, 0.2)"

def render_page():
    st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px; z-index: 2; position: relative;">
            <i class="fa-solid fa-map-location-dot" style="font-size: 38px; margin-right: 15px; color: white; z-index: 2; position: relative;"></i>
            <h1 style="margin: 0; font-size: 40px; font-weight: 700; color: white;">Trạm thông tin Điều hướng</h1>
        </div>
    """, unsafe_allow_html=True)

    col_weather, col_map_traffic = st.columns([1.2, 2.5], gap="large")

    # GỌI DATA
    temp, feels_like, humid, wind, w_text, w_icon, w_color, vis, aqi, aqi_text, aqi_color, advice, glow_color = get_ultimate_weather()
    current_time = datetime.now().strftime("%H:%M - %d/%m/%Y")

    with col_weather:
        # UI CỰC ĐỈNH - GLASSMORPHISM WIDGET CAO CẤP
        html_weather = (
            f'<div style="background: rgba(20, 24, 36, 0.85); padding: 25px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 10px 30px rgba(0,0,0,0.5), inset 0 0 40px {glow_color}; text-align: center; position: relative; z-index: 2; backdrop-filter: blur(15px);">'
            # Header
            '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;">'
            '<span style="color: white; font-weight: bold; font-size: 16px;"><i class="fa-solid fa-location-crosshairs" style="color: #FF4B4B;"></i> TP. Vinh</span>'
            f'<span style="color: #8b949e; font-size: 13px;"><i class="fa-regular fa-clock"></i> {current_time}</span>'
            '</div>'
            
            # Main Temp
            f'<i class="fa-solid {w_icon}" style="font-size: 70px; color: {w_color}; filter: drop-shadow(0 0 15px {w_color}); margin-bottom: 10px;"></i>'
            f'<h1 style="color: white; font-size: 65px; margin: 0; font-weight: 900; letter-spacing: -2px;">{temp}°</h1>'
            f'<p style="color: #e0e0e0; font-size: 18px; margin-top: 5px; font-weight: 600; letter-spacing: 1px;">{w_text}</p>'
            f'<p style="color: #8b949e; font-size: 14px; margin-top: -10px; margin-bottom: 25px;">Cảm giác thực tế: <b style="color: white;">{feels_like}°C</b></p>'
            
            # Metrics Grid (4 Ô vuông)
            '<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">'
                # Ô Độ ẩm
                '<div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 12px; text-align: left; border: 1px solid rgba(255,255,255,0.05);">'
                    '<i class="fa-solid fa-droplet" style="color: #4DA6FF; margin-bottom: 5px; font-size: 16px;"></i>'
                    '<div style="color: #8b949e; font-size: 12px;">Độ ẩm</div>'
                    f'<div style="color: white; font-size: 16px; font-weight: bold;">{humid}%</div>'
                '</div>'
                # Ô Sức Gió
                '<div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 12px; text-align: left; border: 1px solid rgba(255,255,255,0.05);">'
                    '<i class="fa-solid fa-wind" style="color: #A0AEC0; margin-bottom: 5px; font-size: 16px;"></i>'
                    '<div style="color: #8b949e; font-size: 12px;">Sức gió</div>'
                    f'<div style="color: white; font-size: 16px; font-weight: bold;">{wind} km/h</div>'
                '</div>'
                # Ô Tầm nhìn
                '<div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 12px; text-align: left; border: 1px solid rgba(255,255,255,0.05);">'
                    '<i class="fa-solid fa-eye" style="color: #FFD700; margin-bottom: 5px; font-size: 16px;"></i>'
                    '<div style="color: #8b949e; font-size: 12px;">Tầm nhìn</div>'
                    f'<div style="color: white; font-size: 16px; font-weight: bold;">{vis} km</div>'
                '</div>'
                # Ô AQI
                '<div style="background: rgba(0,0,0,0.3); padding: 12px; border-radius: 12px; text-align: left; border: 1px solid rgba(255,255,255,0.05);">'
                    f'<i class="fa-solid fa-lungs" style="color: {aqi_color}; margin-bottom: 5px; font-size: 16px;"></i>'
                    '<div style="color: #8b949e; font-size: 12px;">AQI (Bụi mịn)</div>'
                    f'<div style="color: {aqi_color}; font-size: 16px; font-weight: bold;">{aqi} - {aqi_text}</div>'
                '</div>'
            '</div>'
            
            # Lời khuyên động
            '<div style="background: rgba(255, 75, 75, 0.15); border-left: 4px solid #FF4B4B; padding: 12px; border-radius: 8px; text-align: left;">'
            f'<span style="color: white; font-size: 13px; font-weight: 500;"><i class="fa-solid fa-bullhorn" style="color: #FF4B4B; margin-right: 5px;"></i> {advice}</span>'
            '</div>'
            
            '</div>'
        )
        st.markdown(html_weather, unsafe_allow_html=True)

    with col_map_traffic:
        st.markdown("""
        <div style="border-radius: 20px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); z-index: 2; position: relative; height: 570px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
            <div style="background: #1A1C24; padding: 12px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.05);">
                <span style="color: white; font-weight: bold; font-size: 15px;"><i class="fa-solid fa-satellite-dish" style="color: #FF4B4B;"></i> Radar Giao thông Waze Live</span>
                <span style="color: #00FF00; font-size: 12px; font-weight: bold;"><i class="fa-solid fa-circle-dot fa-fade"></i> ONLINE</span>
            </div>
            <iframe 
                src="https://embed.waze.com/iframe?zoom=14&lat=18.6733&lon=105.6813&ct=livemap&color=dark"
                width="100%" 
                height="100%" 
                style="border:0;" 
                allowfullscreen="">
            </iframe>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; margin-top: 15px; z-index: 2; position: relative; padding: 0 5px;">
            <span style="color: #8b949e; font-size: 12px;"><i class="fa-solid fa-server"></i> Máy chủ dữ liệu khí tượng Open-Meteo & Cơ sở Dữ liệu AQI Toàn cầu.</span>
            <span style="color: #8b949e; font-size: 12px;"><i class="fa-solid fa-shield-halved"></i> Dữ liệu làm mới tự động ngầm.</span>
        </div>
        """, unsafe_allow_html=True)