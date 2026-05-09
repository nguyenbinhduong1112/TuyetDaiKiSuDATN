# Code Review

Ngay uu tien: 2026-05-08

## Ket luan nhanh

Repo hien khong loi cu phap Python khi chay `python -m compileall -q .`. Cac diem nen toi uu nhat khong nam o style, ma nam o phan quyen COD, bao mat dang nhap, truy van SQL, va chat luong thuat toan "AI" toi uu lo trinh.

## Findings uu tien cao

### 1. Tai xe COD co the thay/hoan thanh don cua tai xe khac

- File: `drivecod.py`
- Vi tri: `get_my_active_cod_order(driver_username)` va `assign_cod_group_to_driver(point_ids, driver_username)`
- Van de:
  - `get_my_active_cod_order()` nhan `driver_username` nhung khong dung bien nay trong SQL.
  - `assign_cod_group_to_driver()` chi set `status = N'Dang giao'`, khong ghi `driver_id`.
  - He qua la bat ky tai xe nao vao man COD cung co the thay don dang giao, va lich su/leaderboard khong gan dung tai xe.
- De xuat:
  - Khi nhan chuyen, update ca `driver_id = ?`.
  - Khi lay don dang giao, them dieu kien `driver_id = ?`.
  - Them dieu kien tranh 2 tai xe nhan cung mot chuyen:

```sql
UPDATE LogisticsPoints
SET status = N'Dang giao', driver_id = ?
WHERE point_id IN (...)
  AND status = N'Cho xu ly'
  AND order_type = N'le'
  AND driver_id IS NULL;
```

### 2. Mat khau dang luu plaintext

- File: `login.py`, `user_profile.py`, `LogisticsDB.sql`
- Van de:
  - Dang nhap so sanh truc tiep `username/password`.
  - Tai khoan seed co mat khau yeu nhu `admin/123`, `taixe/123`.
  - Doi mat khau trong `user_profile.py` cung ghi plaintext vao DB.
- De xuat:
  - Dung `bcrypt` hoac `argon2-cffi`.
  - Tao cot `password_hash`, migrate password cu sang hash.
  - Bo mat khau mac dinh khoi code va SQL dump.

### 3. SQL injection o truy van don khach hang

- File: `customer.py`
- Vi tri: `get_customer_active_points(username)`
- Van de:
  - SQL noi chuoi truc tiep:

```python
WHERE created_by = '{username}'
```

  - Username co ky tu `'` co the lam hong query hoac bi khai thac.
- De xuat:

```python
query = """
    SELECT point_id, lat, lon, status
    FROM LogisticsPoints
    WHERE created_by = ?
      AND order_type = N'chuoi'
      AND status IN (N'Cho Admin duyet', N'Cho xu ly')
"""
df = pd.read_sql(query, conn, params=[username])
```

### 4. Phan "AI toi uu lo trinh" chua thuc su toi uu

- File: `engine.py`, `model.py`, `train_model.py`
- Van de:
  - `train_model.py` train tren input random va loss `mean(logits**2)`, khong toi uu tong quang duong.
  - `solve_delivery_route()` moi vong lap goi lai model tu dau va khong dung `current_node`.
  - Ket qua co the kem hon heuristic don gian.
- De xuat:
  - Neu can on dinh cho do an/demo: thay bang nearest-neighbor + 2-opt.
  - Neu muon nghiem tuc hon: dung OR-Tools cho TSP/VRP.
  - Van co the giu UI label "toi uu lo trinh", nhung backend nen la thuat toan co metric ro rang.

### 5. Lich su don hang keo du lieu qua rong

- File: `order_history.py`
- Vi tri: `get_order_history(username, role)`
- Van de:
  - Dang `SELECT * FROM LogisticsPoints ORDER BY created_at DESC` roi moi loc theo role trong Python.
  - Voi du lieu lon se cham va keo du du lieu nhay cam ve app.
- De xuat:
  - Role khach hang: SQL `WHERE created_by = ?`.
  - Role tai xe: SQL `WHERE driver_id = ?`.
  - Role admin: moi lay tat ca.
  - Chi select cac cot can hien thi.

### 6. Secret va cau hinh DB hardcode

- File: `config.py`, `main.py`, `login.py`
- Van de:
  - `SERVER_NAME`, `DATABASE_NAME`, `CONN_STR`, `SECRET_KEY` dang nam trong source.
  - Khi deploy/chia se code rat de lo secret hoac bi sai moi truong.
- De xuat:
  - Chuyen sang bien moi truong hoac `st.secrets`.
  - Tao mot module cau hinh tap trung, tranh lap `SECRET_KEY` o nhieu file.

## Toi uu nen lam tiep

### Tach helper chung

Nhieu file lap lai cac ham:

- `get_base64_of_bin_file`
- `calculate_distance_km`
- `execute_db`
- `get_warehouse_loc`

Nen tao cac module nhu:

- `db.py`: ket noi DB, execute query, read DataFrame.
- `geo_utils.py`: tinh khoang cach, OSRM route.
- `assets.py`: doc anh/base64.
- `auth.py`: JWT, hash password, login.

### Giam HTML/CSS inline

`admin.py`, `driver.py`, `customer.py`, `login.py` co cac block HTML/CSS rat dai. Nen tach thanh:

- `styles.py` hoac file `.css` doc vao Streamlit.
- Cac function render component nho: sidebar, header, user popover, metric card.

Loi ich: code ngan hon, it loi khi sua UI, de review hon.

### Cai thien quan ly cache

Hien co nhieu cho goi `st.cache_data.clear()` lam xoa toan bo cache, co the anh huong cac page khac. Nen uu tien clear tung function cache:

- `get_chain_orders_data.clear()`
- `get_available_cod_orders.clear()`
- `get_customer_active_points.clear()`

Chi dung clear toan bo khi that su can.

### Dong connection an toan hon

Nhieu ham mo connection roi close thu cong. Nen dung helper/context manager de dam bao loi giua chung van dong connection:

```python
from contextlib import contextmanager
import pyodbc

@contextmanager
def get_conn():
    conn = pyodbc.connect(CONN_STR)
    try:
        yield conn
    finally:
        conn.close()
```

## Thu tu sua de it rui ro

1. Sua phan quyen COD `driver_id`.
2. Sua SQL injection trong `customer.py`.
3. Doi `order_history.py` sang loc trong SQL.
4. Tach `SECRET_KEY` va config DB ra env/secrets.
5. Hash password va migrate user.
6. Thay route optimizer bang nearest-neighbor + 2-opt hoac OR-Tools.
7. Refactor helper/UI sau khi logic on dinh.

## Kiem tra da chay

```powershell
python -m compileall -q .
```

Ket qua: khong co loi cu phap Python.
