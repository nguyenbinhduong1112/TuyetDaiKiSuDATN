# Performance Optimization Plan

Ngay tao: 2026-05-08

Muc tieu: giam lag khi chay Streamlit app, giam thoi gian load trang, giam truy van SQL thua, va tranh viec tinh/toi uu lo trinh bi treo UI.

Ghi chu: file nay chua chay SQL vao database. Nen backup database truoc khi ap dung cac lenh index/alter ben duoi.

## Tong ket uu tien

Can lam truoc:

1. Bo viec load `MapManager()`/OSMnx khoi hot path cua trang tai xe.
2. Them index cho bang `LogisticsPoints`.
3. Sua query SQL de tranh `SELECT *`, `ISNULL(...)` trong `WHERE`, va loc du lieu ngay trong SQL.
4. Dung clear cache theo tung function thay vi `st.cache_data.clear()`.
5. Cache route OSRM theo danh sach toa do.
6. Thay "AI route" hien tai bang heuristic nhanh/on dinh hon.
7. Lazy-load du lieu theo menu/tab dang mo de giam lag khi chuyen tab.

## Trang thai ap dung Phase 1

Da sua trong code:

- `driver.py`: khong con load `MapManager()`/OSMnx khi mo trang tai xe; chi load model.
- `drivecod.py`: tach `MapManager()` thanh lazy fallback, chi load khi OSRM loi; dong thoi gan va loc `driver_id` khi tai xe nhan COD.
- `admin.py`, `admin_orders.py`, `driver.py`: doi cac query don chuoi sang `order_type = N'chuỗi'` va `delivery_status <> N'Đang chờ duyệt'`.
- `order_history.py`: loc theo role ngay trong SQL va chi lay `TOP (1000)` cot can hien thi.
- `customer.py`: bo SQL f-string o query don khach, chuyen sang parameter.
- `admin.py`, `admincod.py`, `customer.py`, `driver.py`: thay `st.cache_data.clear()` bang clear cache theo function.
- `PHASE1_DB_OPTIMIZATION.sql`: them script normalize NULL va tao index Phase 1.

Da ap dung truc tiep `PHASE1_DB_OPTIMIZATION.sql` vao SQL Server sau khi cai `pyodbc`.

## Trang thai ap dung Phase 2

Da sua trong code:

- `driver.py`, `drivecod.py`: cache OSRM route trong 30 phut theo danh sach toa do da sap xep; doi OSRM sang `https` va giam timeout network xuong 5 giay.
- `admin.py`: map dieu phoi chi lay `TOP (300)` don chuoi moi nhat de ve marker, them metric count rieng cho tong don cho gom, va gom marker don hang bang `MarkerCluster`.
- `admin_leaderboard.py`: thay `df.apply(axis=1)` tinh khoang cach bang vectorized NumPy cho bang xep hang khach hang/tai xe.

Da ap dung SQL Phase 1 vao database bang `PHASE1_DB_OPTIMIZATION.sql` sau khi cai `pyodbc`.

## Trang thai ap dung Phase 3

Da sua trong code:

- Them `route_optimizer.py`: thuat toan nearest-neighbor + 2-opt tinh route bang Haversine, khong phu thuoc Torch.
- `driver.py`, `drivecod.py`: bo import `torch`, `PointerNet`, `engine.solve_delivery_route`, va bo load `weights.pth` trong runtime.
- `driver.py`, `drivecod.py`: dung `route_optimizer.solve_delivery_route()` va `route_optimizer.route_distance_km()` chung, giam duplicate logic tinh quang duong.
- `requirements.txt`: bo `torch` khoi runtime dependencies de lan cai sau nhe hon.
- Them `requirements-ai.txt`: chi can cai khi muon chay lai `train_model.py` / PointerNet cu.

Ghi chu: UI van co chu "AI toi uu" de khong thay doi trai nghiem nguoi dung, nhung backend da chuyen sang heuristic TSP on dinh va de giai thich hon.

## Trang thai ap dung Phase 4 - giam lag khi chuyen tab/menu

Da sua trong code:

- `admin.py`: khong con load danh sach user, kho, marker map va count don cho gom truoc khi biet menu dang mo. Cac du lieu nang nay chi load khi vao `Ban do Dieu phoi`; header admin chi query fullname nhe.
- `driver.py`: khong con goi `fetch_real_data()` khi mo cac menu COD, giao thong, lich su hoac profile. Du lieu don chuoi chi load khi vao `Don hang chuoi`.
- `customer.py`: vi tri kho chi load khi vao man `Dat don hang`; cac menu COD, lich su va profile khong con query kho thua.
- `admin_orders.py`: thay `st.tabs` bang radio view de Streamlit khong render ca hai tab cung luc. Tach query count, pending va active; chi load dataframe cua view dang xem.
- `admincod.py`: tuong tu `admin_orders.py`, tach count/pending/active va chi render view dang chon.

Ly do: Streamlit rerun ca file moi khi doi widget/menu. `st.tabs` khong lazy-load, nen moi lan doi tab van chay code cua tat ca tab. Phase 4 cat bot phan query/render khong nam trong man dang hien thi.

## Trang thai ap dung Phase 5 - fix trang trang sau login va giam payload UI

Da sua trong code:

- `login.py`: bo `login_placeholder.empty()` ngay truoc `st.rerun()`. Doan nay gay loi frontend Streamlit `'setIn' cannot be called on an ElementNode`, lam man hinh trang sau khi dang nhap.
- Tao anh toi uu trong `img/`:
  - `logo_optimized.webp`: 8.6 MB -> 15 KB.
  - `watermark_optimized.webp`: 3.2 MB -> 58 KB.
  - `favicon_optimized.png`: 2.1 MB -> 7 KB.
- `login.py`, `admin.py`, `driver.py`, `customer.py`: doi base64 logo/background sang anh toi uu.
- `main.py`: doi `page_icon` sang favicon toi uu.

Ket qua do bang Playwright:

- HTML login giam tu khoang `15,836,995` ky tu xuong `123,673`.
- Dang nhap admin render sau click khoang `0.36s`, khong con trang man.
- Chuyen menu admin khoang `0.82s - 1.18s`.
- Dang nhap tai xe/khach hang khoang `1.0s`; chuyen menu tai xe/khach hang khoang `0.58s - 1.43s`.

## 1. Bottleneck lon: OSMnx/MapManager bi load qua som

### Hien trang

- `driver.py`:
  - `load_all()` tao `PointerNet()` va `MapManager()`.
  - Trang driver chinh dang dung OSRM public API de lay duong.
  - `map_mgr` gan nhu khong duoc dung trong `driver.py`.

- `drivecod.py`:
  - `load_all_cod()` cung tao `MapManager()`.
  - `map_mgr` chi can khi OSRM loi va can fallback bang graph noi bo.

- `map_utils.py`:
  - `MapManager.__init__()` goi:

```python
ox.graph_from_point((18.6601, 105.6942), dist=3000, network_type='drive')
ox.project_graph(G)
```

Day la tac vu nang, phu thuoc internet/cache OSM, co the lam trang tai xe mo rat lau.

### Giai phap

Quick win:

- Trong `driver.py`, sua `load_all()` chi load model, khong load `MapManager`.
- Trong `drivecod.py`, sua `load_all_cod()` chi load model.
- Chi khoi tao `MapManager()` khi OSRM fail va that su can fallback.

Vi du:

```python
@st.cache_resource
def load_model():
    model = PointerNet()
    if os.path.exists("weights.pth"):
        model.load_state_dict(torch.load("weights.pth", map_location="cpu"))
    model.eval()
    return model

@st.cache_resource
def load_map_manager():
    return MapManager()
```

Trong route fallback:

```python
if actual_route:
    st.session_state.cod_actual_path = actual_route
else:
    map_mgr = load_map_manager()
    node_ids = map_mgr.get_nearest_nodes(np.array(locations))
    ordered_nodes = [node_ids[i] for i in st.session_state.cod_route_indices]
    st.session_state.cod_actual_path = map_mgr.get_route_coords(ordered_nodes)
```

Tac dong ky vong: giam thoi gian mo trang tai xe/COD, vi khong tai graph duong neu khong can.

## 2. SQL dang thieu index cho cac man hinh chinh

### Hien trang

Bang `LogisticsPoints` chi co primary key tren `point_id`. Trong code lai query nhieu theo:

- `status`
- `delivery_status`
- `order_type`
- `created_by`
- `driver_id`
- `group_id`
- `created_at DESC`

Neu du lieu tang len vai nghin/vai chuc nghin dong, cac man Admin, Driver, History, Leaderboard se cham.

### SQL index de xuat

Chay tren SQL Server sau khi backup DB:

```sql
USE LogisticsDB;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_LP_ChainStatus'
      AND object_id = OBJECT_ID('dbo.LogisticsPoints')
)
CREATE NONCLUSTERED INDEX IX_LP_ChainStatus
ON dbo.LogisticsPoints (status, delivery_status, created_at DESC)
INCLUDE (point_id, lat, lon, created_by, driver_id)
WHERE order_type = N'chuỗi';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_LP_CodStatusGroup'
      AND object_id = OBJECT_ID('dbo.LogisticsPoints')
)
CREATE NONCLUSTERED INDEX IX_LP_CodStatusGroup
ON dbo.LogisticsPoints (status, group_id, created_at DESC)
INCLUDE (point_id, pickup_lat, pickup_lon, lat, lon, created_by, delivery_status, driver_id)
WHERE order_type = N'lẻ';
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_LP_CustomerHistory'
      AND object_id = OBJECT_ID('dbo.LogisticsPoints')
)
CREATE NONCLUSTERED INDEX IX_LP_CustomerHistory
ON dbo.LogisticsPoints (created_by, created_at DESC)
INCLUDE (point_id, order_type, status, delivery_status, lat, lon, driver_id);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_LP_DriverHistory'
      AND object_id = OBJECT_ID('dbo.LogisticsPoints')
)
CREATE NONCLUSTERED INDEX IX_LP_DriverHistory
ON dbo.LogisticsPoints (driver_id, created_at DESC)
INCLUDE (point_id, order_type, status, delivery_status, lat, lon, created_by);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE name = 'IX_Userstable_RoleStatus'
      AND object_id = OBJECT_ID('dbo.userstable')
)
CREATE NONCLUSTERED INDEX IX_Userstable_RoleStatus
ON dbo.userstable (role, current_status, is_locked)
INCLUDE (username, fullname, lat, lon);
GO
```

### Nen doi query de an index tot hon

Dang co nhieu query dung:

```sql
ISNULL(order_type, '') != N'lẻ'
ISNULL(delivery_status, '') != N'Đang chờ duyệt'
```

Cach nay lam SQL Server kho dung index. Nen chuan hoa du lieu va query ro rang:

```sql
UPDATE dbo.LogisticsPoints
SET order_type = N'chuỗi'
WHERE order_type IS NULL;

UPDATE dbo.LogisticsPoints
SET delivery_status = N'Chờ xử lý'
WHERE delivery_status IS NULL;
```

Sau do trong Python doi thanh:

```sql
order_type = N'chuỗi'
delivery_status <> N'Đang chờ duyệt'
```

Neu chac chan cot khong can NULL nua, co the doi schema:

```sql
ALTER TABLE dbo.LogisticsPoints
ALTER COLUMN order_type NVARCHAR(20) NOT NULL;

ALTER TABLE dbo.LogisticsPoints
ALTER COLUMN delivery_status NVARCHAR(50) NOT NULL;
```

Chi chay `ALTER COLUMN` sau khi da kiem tra khong con NULL.

## 3. `order_history.py` dang keo qua nhieu du lieu

### Hien trang

`order_history.py` dang:

```python
query = "SELECT * FROM LogisticsPoints ORDER BY created_at DESC"
df = pd.read_sql(query, conn)
```

Sau do moi loc theo role trong Pandas. Viec nay gay cham va keo du lieu khong can thiet.

### Giai phap

Loc ngay trong SQL va chi lay cot can hien thi:

```python
BASE_COLUMNS = """
    point_id, order_type, created_by, driver_id, created_at,
    status, delivery_status, lat, lon
"""

if role == "3":
    query = f"""
        SELECT TOP (1000) {BASE_COLUMNS}
        FROM LogisticsPoints
        WHERE created_by = ?
        ORDER BY created_at DESC
    """
    df = pd.read_sql(query, conn, params=[username])
elif role == "2":
    query = f"""
        SELECT TOP (1000) {BASE_COLUMNS}
        FROM LogisticsPoints
        WHERE driver_id = ?
        ORDER BY created_at DESC
    """
    df = pd.read_sql(query, conn, params=[username])
else:
    query = f"""
        SELECT TOP (1000) {BASE_COLUMNS}
        FROM LogisticsPoints
        ORDER BY created_at DESC
    """
    df = pd.read_sql(query, conn)
```

Tac dong ky vong: History load nhanh hon ro khi DB lon.

## 4. Admin dashboard dang query COUNT nhieu lan

### Hien trang

`admin.py:get_pending_orders()` dang goi 4 cau `SELECT COUNT(*)` rieng.

### Giai phap

Gom thanh 1 query:

```sql
SELECT
    SUM(CASE WHEN delivery_status = N'Đang chờ duyệt' AND order_type = N'chuỗi' THEN 1 ELSE 0 END) AS chain_driver_done,
    SUM(CASE WHEN status = N'Chờ Admin duyệt' AND order_type = N'chuỗi' THEN 1 ELSE 0 END) AS chain_user_create,
    SUM(CASE WHEN delivery_status = N'Đang chờ duyệt' AND order_type = N'lẻ' THEN 1 ELSE 0 END) AS cod_driver_done,
    SUM(CASE WHEN status = N'Chờ Admin duyệt' AND order_type = N'lẻ' THEN 1 ELSE 0 END) AS cod_user_create
FROM dbo.LogisticsPoints
WHERE status = N'Chờ Admin duyệt'
   OR delivery_status = N'Đang chờ duyệt';
```

Trong Python:

```python
row = pd.read_sql(query, conn).iloc[0]
return (
    int(row["chain_driver_done"] or 0),
    int(row["chain_user_create"] or 0),
    int(row["cod_driver_done"] or 0),
    int(row["cod_user_create"] or 0),
)
```

Tac dong ky vong: giam round-trip toi SQL Server moi lan render Admin.

## 5. Khong nen dung `st.cache_data.clear()` qua rong

### Hien trang

Nhieu file goi:

```python
st.cache_data.clear()
```

Lenh nay xoa toan bo cache data cua app. Sau mot thao tac nho, tat ca trang khac co the phai load lai DB, anh base64, count, map data.

### Giai phap

Clear dung function can reset:

```python
get_active_points.clear()
get_pending_orders.clear()
fetch_real_data.clear()
get_customer_active_points.clear()
```

De xuat theo file:

- `admin.py`: thay `st.cache_data.clear()` bang `get_active_points.clear()`, `get_all_users.clear()`, `get_pending_orders.clear()`, `get_warehouse_loc.clear()` tuy thao tac.
- `driver.py`: khi dong bo don hang, clear `fetch_real_data` va `get_pending_count`.
- `customer.py`: sau khi tao don, clear `get_customer_active_points` va co the `get_warehouse_loc` neu sua kho.
- `admincod.py`: clear `get_pending_cod_orders`, `get_active_cod_orders`.

Tac dong ky vong: tranh load lai ca app sau moi click.

## 6. OSRM route dang goi network dong bo va chua cache

### Hien trang

`driver.py` va `drivecod.py` goi:

```python
requests.get(url, timeout=10)
```

Moi lan kich hoat toi uu route, UI phai cho request xong. Neu OSRM public server cham, app se lag.

### Giai phap

Cache route theo danh sach toa do da sap xep:

```python
@st.cache_data(ttl=1800, show_spinner=False)
def get_osrm_route_cached(ordered_locs_tuple):
    coords_str = ";".join([f"{lon},{lat}" for lat, lon in ordered_locs_tuple])
    url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}?overview=full&geometries=geojson"
    response = requests.get(url, timeout=5)
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok":
        return None
    return [[coord[1], coord[0]] for coord in data["routes"][0]["geometry"]["coordinates"]]
```

Luu y:

- Doi `http://` sang `https://`.
- Giam timeout tu 10s xuong 5s.
- Neu route nhieu diem, can gioi han so diem gui OSRM hoac chia chunk.
- Neu demo offline, nen uu tien duong thang fallback thay vi doi network qua lau.

## 7. Folium map bi rebuild moi rerun

### Hien trang

Moi lan click map hoac bam nut, Streamlit rerun va tao lai `folium.Map`, marker, popup.

### Giai phap

Quick win:

- Chi return object can thiet:
  - Page chi xem map: `returned_objects=[]`.
  - Page can click: `returned_objects=["last_clicked"]`.
- Khong `st.rerun()` neu click cung toa do cu.
- Khi so marker lon, dung `MarkerCluster` thay vi ve tat ca marker rieng le.
- Gioi han list active points hien tren map, vi du chi lay 300 don moi nhat hoac don dang active.

SQL de gioi han:

```sql
SELECT TOP (300)
    point_id, lat, lon, created_by, created_at, delivery_status
FROM dbo.LogisticsPoints
WHERE status = N'Chờ xử lý'
  AND order_type = N'chuỗi'
ORDER BY created_at DESC;
```

## 8. "AI route" hien tai co the vua cham vua khong toi uu

### Hien trang

- `train_model.py` train model bang input random va loss `mean(logits**2)`.
- `engine.py` moi buoc goi lai model tu dau, khong dung `current_node`.
- Ket qua route khong dam bao ngan hon.

### Giai phap nhanh hon

Thay bang nearest-neighbor + 2-opt:

- Khong can Torch.
- Ket qua on dinh, de giai thich trong do an.
- Voi so diem giao nho/vua, chay rat nhanh.

Pseudo:

```python
def nearest_neighbor_route(points, start=0):
    unvisited = set(range(len(points)))
    route = [start]
    unvisited.remove(start)
    while unvisited:
        last = route[-1]
        nxt = min(unvisited, key=lambda i: haversine(points[last], points[i]))
        route.append(nxt)
        unvisited.remove(nxt)
    route.append(start)
    return route
```

Sau do chay 2-opt de doi canh neu tong quang duong giam.

Tac dong ky vong: route tinh nhanh hon, khong load `weights.pth`, khong can Torch tren hot path.

## 9. Leaderboard dang tinh distance bang `df.apply`

### Hien trang

`admin_leaderboard.py` dung:

```python
df_raw['Distance'] = df_raw.apply(lambda row: calculate_distance_km(...), axis=1)
```

Voi du lieu lon, `apply(axis=1)` cham.

### Giai phap

Lua chon 1: vectorize bang NumPy.

Lua chon 2: luu `shipping_fee` khi tao don, khong tinh lai moi lan xem leaderboard.

De xuat schema:

```sql
ALTER TABLE dbo.LogisticsPoints ADD shipping_fee INT NULL;
ALTER TABLE dbo.LogisticsPoints ADD distance_km FLOAT NULL;
```

Khi tao don trong `customer.py`/`customercod.py`, ghi luon fee vao DB. Leaderboard chi can `SUM(shipping_fee)`.

## 10. Anh base64 va CSS inline qua lon

### Hien trang

Cac page doc anh, chuyen base64, roi nhung vao CSS/HTML. Du cache function, HTML render ra trinh duyet van rat lon, nhat la background/logo.

### Giai phap

- Nen resize/compress anh trong `img`.
- Dung anh static path neu co the, tranh nhung base64 lon vao moi page.
- Tach CSS dung chung thanh mot file hoac function, tranh lap CSS dai trong `admin.py`, `driver.py`, `customer.py`, `login.py`.

## 11. Ket noi DB nen gom helper

### Hien trang

Moi file tu mo/close `pyodbc.connect(CONN_STR)`. Neu co exception giua chung, connection co the khong dong dung cach.

### Giai phap

Tao `db.py`:

```python
from contextlib import contextmanager
import pandas as pd
import pyodbc
from config import CONN_STR

@contextmanager
def get_conn():
    conn = pyodbc.connect(CONN_STR)
    try:
        yield conn
    finally:
        conn.close()

def read_df(query, params=None):
    with get_conn() as conn:
        return pd.read_sql(query, conn, params=params)

def execute(query, params=()):
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
```

Sau do cac file dung chung helper, de toi uu/tune connection sau nay de hon.

## Thu tu ap dung de nhanh thay ket qua

### Phase 1 - nhanh, it rui ro

1. Sua `driver.py`/`drivecod.py` de lazy-load `MapManager`.
2. Them index SQL cho `LogisticsPoints`.
3. Doi query `order_type` tu `ISNULL(...) != N'lẻ'` sang `order_type = N'chuỗi'`.
4. Sua `order_history.py` de loc theo role ngay trong SQL.
5. Doi cac `st.cache_data.clear()` thanh clear theo function.

### Phase 2 - cai thien ro khi dung nhieu

1. Cache OSRM route.
2. Gop 4 count trong `admin.py` thanh 1 query.
3. Gioi han so marker tren map hoac dung cluster.
4. Vectorize/tien tinh leaderboard.

### Phase 3 - refactor lon

1. Thay route optimizer Torch bang nearest-neighbor + 2-opt hoac OR-Tools.
2. Tach `db.py`, `geo_utils.py`, `assets.py`.
3. Tach CSS/component UI dung chung.
4. Luu `shipping_fee`, `distance_km`, `completed_at` vao DB de report nhanh.

## Checklist do hieu qua

Truoc va sau khi sua, do cac moc:

- Thoi gian mo trang Login.
- Thoi gian mo trang Driver lan dau.
- Thoi gian bam "Dong bo don hang moi".
- Thoi gian bam "Kich hoat toi uu lo trinh".
- Thoi gian mo Admin dashboard.
- Thoi gian mo History voi 1,000+ don.

Co the them do thoi gian don gian:

```python
import time

t0 = time.perf_counter()
# query/render heavy block
st.caption(f"debug: {time.perf_counter() - t0:.2f}s")
```

Khi on dinh thi xoa debug caption.
