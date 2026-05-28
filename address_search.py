"""
Module nhập địa chỉ có cấu trúc cho TuyetDaiKiSu Logistics.

Quy trình nhập:
    1. Dropdown 1: chọn Tỉnh/Thành phố (63 tỉnh) — gõ để tìm.
    2. Dropdown 2: chỉ load Phường/Xã thuộc tỉnh đã chọn — gõ để tìm.
    3. Ô text: nhập tên đường + số nhà (ô duy nhất gõ tự do).
    4. Bấm "Xác nhận địa chỉ" → geocode "đường, phường, tỉnh" → trả lat/lon.

Đặc điểm:
    - Toàn bộ form đặt trong @st.fragment → khi đổi dropdown chỉ rerun fragment,
      popover/expander chứa form không bị đóng lại.
    - st.selectbox sẵn có tìm kiếm: bấm dropdown rồi gõ là tự lọc.

Nguồn dữ liệu hành chính: https://provinces.open-api.vn (free, không key).
Geocoding: Photon (komoot) → fallback Nominatim.

API:
    pick = address_form(key="addr_admin_order")
    if pick:
        lat, lon = pick["lat"], pick["lon"]
        full   = pick["label"]
"""
from __future__ import annotations

import requests
import streamlit as st


_PROVINCES_URL = "https://provinces.open-api.vn/api/v1/p/"
_PROVINCE_DETAIL_URL = "https://provinces.open-api.vn/api/v1/p/{code}?depth=3"

_PHOTON_URL = "https://photon.komoot.io/api"
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_BROWSER_UA = "Mozilla/5.0 UmbrellaLogistics/1.0"

# Tâm TP Vinh dùng làm bias geocoder
_BIAS_LAT = 18.6601
_BIAS_LON = 105.6942

# BBox tỉnh/thành phố hardcode cho các khu vực phổ biến để tránh phải gọi
# Nominatim (rate-limit 1req/s). Tự động fallback sang API nếu không có ở đây.
_HARDCODED_DISTRICT_BBOX = {
    # ("Tỉnh", "Huyện/Thành phố"): (lat_min, lat_max, lon_min, lon_max)
    ("Tỉnh Nghệ An", "Thành phố Vinh"): (18.620, 18.730, 105.620, 105.770),
    ("Thành phố Hà Nội", "Quận Hoàn Kiếm"): (21.015, 21.045, 105.840, 105.870),
    ("Thành phố Hồ Chí Minh", "Quận 1"): (10.760, 10.795, 106.680, 106.715),
}
_HARDCODED_PROVINCE_BBOX = {
    "Tỉnh Nghệ An": (18.55, 20.10, 103.90, 105.85),
    "Thành phố Hà Nội": (20.55, 21.40, 105.30, 106.05),
    "Thành phố Hồ Chí Minh": (10.35, 11.20, 106.35, 107.05),
}


# ---------------- LẤY DANH SÁCH HÀNH CHÍNH ----------------

@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _get_provinces() -> list:
    """63 tỉnh/thành. Trả về list[{name, code}]."""
    try:
        resp = requests.get(_PROVINCES_URL, timeout=10)
        if resp.status_code != 200:
            return []
        data = resp.json() or []
        return [{"name": p["name"], "code": p["code"]} for p in data]
    except Exception:
        return []


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _get_wards_of_province(province_code: int) -> list:
    """Tất cả phường/xã của tỉnh (gộp từ các huyện). Đã sort."""
    try:
        resp = requests.get(
            _PROVINCE_DETAIL_URL.format(code=province_code),
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        data = resp.json() or {}
    except Exception:
        return []

    wards = []
    for d in data.get("districts", []):
        d_name = d.get("name", "")
        for w in d.get("wards", []):
            wards.append({
                "name": w.get("name", ""),
                "code": w.get("code"),
                "district": d_name,
            })
    wards.sort(key=lambda x: (x["district"], x["name"]))
    return wards


# ---------------- GEOCODING ----------------

def _normalize_admin_name(name: str) -> str:
    """Bỏ tiền tố 'Tỉnh ', 'Thành phố ', 'TP ', 'Phường ', 'Xã ' để so khớp dễ hơn."""
    if not name:
        return ""
    n = name.strip().lower()
    for prefix in (
        "thành phố ", "tp. ", "tp ",
        "tỉnh ",
        "phường ", "xã ", "thị trấn ",
        "huyện ", "quận ", "thị xã ",
    ):
        if n.startswith(prefix):
            n = n[len(prefix):]
    return n.strip()


def _nominatim_search(query: str, viewbox: tuple | None = None,
                      bounded: bool = False, limit: int = 5) -> list:
    params = {
        "q": query,
        "format": "json",
        "limit": limit,
        "addressdetails": 1,
        "accept-language": "vi",
    }
    if viewbox:
        # viewbox = (lat_min, lat_max, lon_min, lon_max) → "lon_min,lat_max,lon_max,lat_min"
        lat_min, lat_max, lon_min, lon_max = viewbox
        params["viewbox"] = f"{lon_min},{lat_max},{lon_max},{lat_min}"
        if bounded:
            params["bounded"] = 1
    try:
        resp = requests.get(
            _NOMINATIM_URL,
            params=params,
            headers={"User-Agent": "umbrella_logistics_address_form/1.0"},
            timeout=8,
        )
        if resp.status_code != 200:
            return []
        return resp.json() or []
    except Exception:
        return []


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _geocode_province(province_name: str) -> dict | None:
    """Lấy tâm + bbox tỉnh. Cache 24h."""
    hard = _HARDCODED_PROVINCE_BBOX.get(province_name)
    if hard:
        return {
            "lat": (hard[0] + hard[1]) / 2,
            "lon": (hard[2] + hard[3]) / 2,
            "bbox": hard,
            "label": province_name,
        }

    queries = [
        f"{province_name}, Việt Nam",
        f"{_normalize_admin_name(province_name)}, Việt Nam",
    ]
    for q in queries:
        items = _nominatim_search(q, limit=3)
        for it in items:
            addr = it.get("address", {})
            atype = it.get("addresstype") or it.get("type")
            if atype not in (
                "state", "province", "administrative", "city",
                "municipality", "region",
            ):
                continue
            try:
                lat = float(it["lat"]); lon = float(it["lon"])
            except Exception:
                continue
            bbox = it.get("boundingbox")
            bbox_t = None
            if bbox and len(bbox) == 4:
                try:
                    bbox_t = (float(bbox[0]), float(bbox[1]),
                              float(bbox[2]), float(bbox[3]))
                except Exception:
                    pass
            return {"lat": lat, "lon": lon, "bbox": bbox_t,
                    "label": it.get("display_name", "")}
    return None


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _geocode_district(district_name: str, province_name: str) -> dict | None:
    """Lấy tâm + bbox quận/huyện/thị xã/thành phố. Cache 24h."""
    # Bbox hardcode cho khu vực phổ biến → khỏi gọi API
    hard = _HARDCODED_DISTRICT_BBOX.get((province_name, district_name))
    if hard:
        return {
            "lat": (hard[0] + hard[1]) / 2,
            "lon": (hard[2] + hard[3]) / 2,
            "bbox": hard,
            "label": f"{district_name}, {province_name}",
        }

    target_prov_norm = _normalize_admin_name(province_name)
    queries = [
        f"{district_name}, {province_name}, Việt Nam",
        f"{_normalize_admin_name(district_name)}, {province_name}, Việt Nam",
    ]
    for q in queries:
        items = _nominatim_search(q, limit=5)
        for it in items:
            addr = it.get("address", {})
            state = addr.get("state") or ""
            if target_prov_norm not in _normalize_admin_name(state):
                continue
            atype = it.get("addresstype") or it.get("type", "")
            if atype not in (
                "city", "municipality", "administrative", "town",
                "county", "district",
            ):
                continue
            try:
                lat = float(it["lat"]); lon = float(it["lon"])
            except Exception:
                continue
            bbox = it.get("boundingbox")
            bbox_t = None
            if bbox and len(bbox) == 4:
                try:
                    bbox_t = (float(bbox[0]), float(bbox[1]),
                              float(bbox[2]), float(bbox[3]))
                except Exception:
                    pass
            return {"lat": lat, "lon": lon, "bbox": bbox_t,
                    "label": it.get("display_name", "")}
    return None


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _geocode_ward(ward_name: str, district_name: str, province_name: str) -> dict | None:
    """
    Lấy toạ độ + bbox phường/xã. Cache 24h.

    Lưu ý: Sau sáp nhập 1/7/2025 nhiều phường mới chưa có trên OSM.
    Hàm sẽ thử nhiều biến thể: có/không tiền tố, kèm/không huyện…
    Nếu không tìm thấy, trả None để pipeline fallback sang tâm tỉnh + bbox tỉnh.
    """
    target_prov_norm = _normalize_admin_name(province_name)
    ward_clean = _normalize_admin_name(ward_name)
    district_clean = _normalize_admin_name(district_name)

    queries = [
        f"{ward_name}, {district_name}, {province_name}, Việt Nam",
        f"{ward_name}, {province_name}, Việt Nam",
        f"{ward_clean}, {district_clean}, {province_name}, Việt Nam",
        f"{ward_clean}, {province_name}, Việt Nam",
    ]

    best = None
    for q in queries:
        items = _nominatim_search(q, limit=5)
        for it in items:
            addr = it.get("address", {})
            state = addr.get("state") or ""
            if target_prov_norm not in _normalize_admin_name(state):
                continue
            # Chấp nhận nếu type là phường/xã/quận/huyện/village/town
            atype = it.get("addresstype") or it.get("type", "")
            if atype not in (
                "village", "town", "suburb", "neighbourhood",
                "city", "municipality", "administrative", "ward",
            ):
                continue
            try:
                lat = float(it["lat"]); lon = float(it["lon"])
            except Exception:
                continue
            bbox = it.get("boundingbox")
            bbox_t = None
            if bbox and len(bbox) == 4:
                try:
                    bbox_t = (float(bbox[0]), float(bbox[1]),
                              float(bbox[2]), float(bbox[3]))
                except Exception:
                    pass
            cand = {"lat": lat, "lon": lon, "bbox": bbox_t,
                    "label": it.get("display_name", "")}
            # Ưu tiên ward khớp tên chính xác
            disp = (it.get("display_name") or "").lower()
            if ward_clean and ward_clean in disp:
                return cand
            if best is None:
                best = cand
        if best:
            return best
    return None


def _photon_search(query: str, bbox: tuple | None = None,
                    bias_lat: float = _BIAS_LAT, bias_lon: float = _BIAS_LON,
                    limit: int = 8, only_streets: bool = False) -> list:
    """Photon: nhanh, không rate-limit gắt. Hỗ trợ bbox để filter."""
    params = {"q": query, "limit": limit, "lat": bias_lat, "lon": bias_lon}
    if bbox:
        # bbox = (lat_min, lat_max, lon_min, lon_max)
        # photon: bbox=lon_min,lat_min,lon_max,lat_max
        lat_min, lat_max, lon_min, lon_max = bbox
        params["bbox"] = f"{lon_min},{lat_min},{lon_max},{lat_max}"
    if only_streets:
        # Photon: filter theo osm_tag để chỉ trả highway (đường phố)
        params["osm_tag"] = "highway"
    try:
        resp = requests.get(
            _PHOTON_URL,
            params=params,
            headers={"User-Agent": _BROWSER_UA},
            timeout=5,
        )
        if resp.status_code != 200:
            return []
        return (resp.json() or {}).get("features") or []
    except Exception:
        return []


def _geocode_street_in_ward(street: str, ward_info: dict, province_name: str) -> tuple[float, float] | None:
    """
    Tìm đường giới hạn trong bbox (phường / huyện / tỉnh).
    Dùng Photon (không rate-limit gắt).
    """
    if not street or not street.strip():
        return None
    if not ward_info:
        return None

    bbox = ward_info.get("bbox")
    target_prov_norm = _normalize_admin_name(province_name)

    # Tâm bbox để bias kết quả
    if bbox:
        bias_lat = (bbox[0] + bbox[1]) / 2
        bias_lon = (bbox[2] + bbox[3]) / 2
    else:
        bias_lat, bias_lon = _BIAS_LAT, _BIAS_LON

    queries = [
        f"{street.strip()}, {province_name}",
        street.strip(),
    ]
    for q in queries:
        # Pass 1: chỉ tìm đường (highway)
        feats = _photon_search(q, bbox=bbox, bias_lat=bias_lat, bias_lon=bias_lon,
                                limit=10, only_streets=True)
        # Pass 2 (fallback): mọi loại địa điểm
        if not feats:
            feats = _photon_search(q, bbox=bbox, bias_lat=bias_lat, bias_lon=bias_lon,
                                    limit=10)
        for feat in feats:
            try:
                lon, lat = feat["geometry"]["coordinates"][:2]
            except Exception:
                continue
            props = feat.get("properties", {})
            state = props.get("state") or ""
            country = props.get("country") or ""
            if "việt nam" not in country.lower() and country.lower() != "vietnam":
                continue
            # Khớp tỉnh nếu Photon trả state
            if state and target_prov_norm not in _normalize_admin_name(state):
                continue
            # Validate trong bbox (cho dù photon đã filter)
            if bbox:
                lat_min, lat_max, lon_min, lon_max = bbox
                if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
                    continue
            return (float(lat), float(lon))
    return None


@st.cache_data(ttl=24 * 3600, show_spinner=False)
def _resolve_address(province_name: str, ward_name: str, district_name: str,
                     street: str) -> dict | None:
    """
    Pipeline ưu tiên độ chính xác từ cao xuống thấp:
        1. Đường trong bbox phường (nếu phường có trên OSM).
        2. Đường trong bbox huyện/thành phố (luôn có trên OSM, bbox nhỏ).
        3. Đường trong bbox tỉnh (cuối cùng).
        4. Tâm phường / huyện / tỉnh — chỉ là cứu cánh.

    OPTIMIZATION: nếu district có hardcoded bbox (Vinh, HCM, HN…) thì SKIP
    bước ward (vốn chậm 3-6s do Nominatim rate-limit + phường mới sáp nhập
    không có trên OSM). Bbox huyện ~5-10km đã đủ hẹp để Photon match đường
    chính xác.

    source codes:
        'street'        : khớp đường trong phường.
        'street-dist'   : khớp đường trong huyện/thành phố.
        'street-prov'   : khớp đường trong tỉnh.
        'ward'/'district'/'province' : tâm hành chính tương ứng.
    """
    has_hardcoded_district = (province_name, district_name) in _HARDCODED_DISTRICT_BBOX
    dist_info = _geocode_district(district_name, province_name)
    prov_info = _geocode_province(province_name)

    # 1. Đường trong bbox phường — CHỈ KHI không có hardcoded district bbox
    #    (vì _geocode_ward chậm và phường mới chưa có trên OSM).
    if not has_hardcoded_district:
        ward_info = _geocode_ward(ward_name, district_name, province_name)
        if ward_info:
            coord = _geocode_street_in_ward(street, ward_info, province_name)
            if coord:
                return {"lat": coord[0], "lon": coord[1], "source": "street"}
    else:
        ward_info = None

    # 2. Đường trong bbox huyện/thành phố (đường đi nhanh, chính xác)
    if dist_info:
        coord = _geocode_street_in_ward(street, dist_info, province_name)
        if coord:
            return {"lat": coord[0], "lon": coord[1], "source": "street-dist"}

    # 3. Đường trong bbox tỉnh
    if prov_info:
        coord = _geocode_street_in_ward(street, prov_info, province_name)
        if coord:
            return {"lat": coord[0], "lon": coord[1], "source": "street-prov"}

    # 4. Tâm hành chính (ưu tiên nhỏ → lớn)
    if ward_info:
        return {"lat": ward_info["lat"], "lon": ward_info["lon"], "source": "ward"}
    if dist_info:
        return {"lat": dist_info["lat"], "lon": dist_info["lon"], "source": "district"}
    if prov_info:
        return {"lat": prov_info["lat"], "lon": prov_info["lon"], "source": "province"}
    return None


# ---------------- FRAGMENT FORM ----------------

@st.fragment
def _address_form_inner(key: str, button_label: str):
    """
    Render bên trong fragment.
    - Đổi dropdown / gõ ô text → chỉ rerun fragment, popover stay open.
    - Bấm nút Xác nhận → ghi kết quả vào session_state rồi gọi st.rerun()
      (toàn app, để parent xử lý geocode + map).
    """
    sel_prov_key = f"_addr_form_prov_{key}"
    sel_ward_key = f"_addr_form_ward_{key}"
    street_key = f"_addr_form_street_{key}"
    submit_key = f"_addr_form_submit_{key}"
    submit_signal_key = f"_addr_form_submit_signal_{key}"

    provinces = _get_provinces()
    if not provinces:
        st.error("Không tải được danh sách Tỉnh/Thành. Kiểm tra Internet rồi thử lại.")
        return

    st.markdown(
        "<div style='color:#FF4B4B; font-weight:600; margin-bottom:10px;'>"
        "<i class='fa-solid fa-location-dot'></i> Nhập địa chỉ"
        "</div>"
        # CSS: nâng z-index dropdown lên cao + tăng độ rộng popover/expander để
        # không bị các widget bên dưới (text_input, button) che dropdown.
        "<style>"
        "[data-testid='stPopoverBody'], [data-testid='stExpanderDetails'] {"
        " min-width: 380px !important;"
        "}"
        "div[data-baseweb='popover'] {"
        " z-index: 99999 !important;"
        "}"
        "div[data-baseweb='select'] > div {"
        " z-index: 100 !important;"
        "}"
        ".addr-form-spacer { height: 6px; }"
        "</style>",
        unsafe_allow_html=True,
    )

    # ---- Dropdown Tỉnh (full width) ----
    prov_options = [None] + provinces
    prov_idx = st.selectbox(
        "Tỉnh/Thành phố *",
        options=list(range(len(prov_options))),
        format_func=lambda i: "— Chọn Tỉnh/Thành —" if prov_options[i] is None else prov_options[i]["name"],
        key=sel_prov_key,
        placeholder="— Chọn Tỉnh/Thành —",
    )
    prov_obj = prov_options[prov_idx] if prov_idx else None

    # Khi đổi tỉnh → reset ward
    prev_prov_track = f"_addr_form_prev_prov_idx_{key}"
    if st.session_state.get(prev_prov_track) != prov_idx:
        st.session_state[prev_prov_track] = prov_idx
        if sel_ward_key in st.session_state:
            del st.session_state[sel_ward_key]

    # Load wards theo tỉnh
    wards: list = []
    if prov_obj:
        with st.spinner("Đang tải Phường/Xã..."):
            wards = _get_wards_of_province(prov_obj["code"])

    # Spacer giữa 2 dropdown
    st.markdown("<div class='addr-form-spacer'></div>", unsafe_allow_html=True)

    # ---- Dropdown Phường/Xã (full width) ----
    if not prov_obj:
        st.selectbox(
            "Phường/Xã *",
            options=["(Hãy chọn Tỉnh/Thành trước)"],
            key=sel_ward_key,
            disabled=True,
        )
        ward_obj = None
    elif not wards:
        st.selectbox(
            "Phường/Xã *",
            options=["(Không tải được dữ liệu)"],
            key=sel_ward_key,
            disabled=True,
        )
        ward_obj = None
    else:
        ward_options = [None] + wards
        ward_idx = st.selectbox(
            "Phường/Xã *",
            options=list(range(len(ward_options))),
            format_func=lambda i: (
                "— Chọn Phường/Xã —" if ward_options[i] is None
                else f"{ward_options[i]['name']} - {ward_options[i]['district']}"
            ),
            key=sel_ward_key,
            placeholder="— Chọn Phường/Xã —",
        )
        ward_obj = ward_options[ward_idx] if ward_idx else None

    # Spacer rõ ràng để dropdown bung xuống không che ô text bên dưới
    st.markdown(
        "<div style='height:14px;'></div>"
        "<hr style='border:0;border-top:1px solid rgba(255,255,255,0.08);margin:0 0 10px 0;'>",
        unsafe_allow_html=True,
    )

    # ---- Ô text đường ----
    street = st.text_input(
        "Tên đường, số nhà *",
        key=street_key,
        placeholder="VD: 1 Lê Hồng Phong",
    )

    # ---- Preview ----
    full_label = ""
    if prov_obj and ward_obj and street.strip():
        full_label = f"{street.strip()}, {ward_obj['name']}, {prov_obj['name']}"
        st.markdown(
            f"<div style='background:rgba(40,167,69,0.1); border-left:3px solid #28a745;"
            f"padding:8px 12px; border-radius:4px; margin-top:8px; font-size:13px; color:#e0e0e0;'>"
            f"<b style='color:#28a745;'><i class='fa-solid fa-check'></i> Địa chỉ đầy đủ:</b><br>"
            f"<span style='color:white;'>{full_label}</span></div>",
            unsafe_allow_html=True,
        )

    # ---- Nút submit ----
    submitted = st.button(
        button_label,
        key=submit_key,
        type="primary",
        use_container_width=True,
    )

    if not submitted:
        return

    # Validate
    errors = []
    if not prov_obj:
        errors.append("Vui lòng chọn Tỉnh/Thành phố.")
    if not ward_obj:
        errors.append("Vui lòng chọn Phường/Xã.")
    if not street.strip():
        errors.append("Vui lòng nhập Tên đường / Số nhà.")
    if errors:
        for e in errors:
            st.error(e)
        return

    # Geocode (trong fragment để spinner hiển thị tại form)
    with st.spinner("Đang xác định toạ độ..."):
        result = _resolve_address(
            province_name=prov_obj["name"],
            ward_name=ward_obj["name"],
            district_name=ward_obj["district"],
            street=street.strip(),
        )

    if not result:
        st.error(
            "Không xác định được toạ độ phường/xã. Hãy thử chọn phường khác "
            "hoặc dùng tab 'Chọn trên Map'."
        )
        return

    src = result.get("source")
    src_msg = {
        "street": ("✅ Tìm thấy đường trong phường", "success"),
        "street-dist": (f"✅ Tìm thấy đường trong {ward_obj['district']}", "success"),
        "street-prov": (
            f"⚠️ Không khớp đường trong {ward_obj['district']}, đã ghim "
            f"trong tỉnh — vui lòng kiểm tra lại trên Map.", "warning"
        ),
        "ward": (
            f"ℹ️ Không tìm thấy đường '{street.strip()}' trong {ward_obj['name']}. "
            f"Đã ghim tâm phường — bạn có thể tinh chỉnh trên Map.", "info"
        ),
        "district": (
            f"⚠️ Không tìm thấy đường '{street.strip()}' trong "
            f"{ward_obj['district']}. Đã ghim tâm huyện/thành phố — "
            f"vui lòng chỉnh lại trên Map.", "warning"
        ),
        "province": (
            f"⚠️ Không tìm thấy phường/huyện trên bản đồ "
            f"(có thể do dữ liệu OSM chưa cập nhật sau sáp nhập). "
            f"Đã ghim tâm {prov_obj['name']} — vui lòng chỉnh lại trên Map.", "warning"
        ),
    }
    msg, level = src_msg.get(src, ("", "info"))
    if msg:
        getattr(st, level)(msg)

    # Lưu kết quả ra session để parent (ngoài fragment) lấy ở rerun kế tiếp
    st.session_state[submit_signal_key] = {
        "label": full_label,
        "lat": result["lat"],
        "lon": result["lon"],
        "raw": {
            "province": prov_obj["name"],
            "ward": ward_obj["name"],
            "district": ward_obj["district"],
            "street": street.strip(),
            "geocode_source": result["source"],
        },
    }
    # Rerun toàn app để parent ghi DB + cập nhật map.
    st.rerun()


# ---------------- WIDGET PUBLIC ----------------

def address_form(key: str, button_label: str = "Xác nhận địa chỉ") -> dict | None:
    """
    Widget chính. Trả về dict {label, lat, lon, raw} đúng MỘT lần ngay sau
    khi user bấm "Xác nhận địa chỉ" và geocode thành công.
    """
    submit_signal_key = f"_addr_form_submit_signal_{key}"

    # Lấy 1-shot kết quả (nếu fragment vừa submit ở rerun trước)
    pending = st.session_state.pop(submit_signal_key, None)
    if pending is not None:
        return pending

    # Render fragment (chứa form + dropdowns + nút)
    with st.container(border=True):
        _address_form_inner(key, button_label)

    return None
