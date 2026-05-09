USE LogisticsDB;
GO

SET NOCOUNT ON;
GO

/* Phase 1 data normalization.
   The Python code now uses direct predicates such as:
   - order_type = N'chuỗi'
   - delivery_status <> N'Đang chờ duyệt'
   Normalize older NULL rows first so existing records keep their previous behavior.
*/

UPDATE dbo.LogisticsPoints
SET order_type = N'chuỗi'
WHERE order_type IS NULL;
GO

UPDATE dbo.LogisticsPoints
SET delivery_status = N'Chờ xử lý'
WHERE delivery_status IS NULL;
GO

UPDATE dbo.LogisticsPoints
SET status = N'Chờ xử lý'
WHERE status IS NULL;
GO

/* Main app indexes. These are idempotent and safe to rerun. */

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_LP_ChainStatus'
      AND object_id = OBJECT_ID('dbo.LogisticsPoints')
)
CREATE NONCLUSTERED INDEX IX_LP_ChainStatus
ON dbo.LogisticsPoints (status, delivery_status, created_at DESC)
INCLUDE (point_id, lat, lon, created_by, driver_id)
WHERE order_type = N'chuỗi';
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_LP_CodStatusGroup'
      AND object_id = OBJECT_ID('dbo.LogisticsPoints')
)
CREATE NONCLUSTERED INDEX IX_LP_CodStatusGroup
ON dbo.LogisticsPoints (status, group_id, created_at DESC)
INCLUDE (point_id, pickup_lat, pickup_lon, lat, lon, created_by, delivery_status, driver_id)
WHERE order_type = N'lẻ';
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_LP_CustomerHistory'
      AND object_id = OBJECT_ID('dbo.LogisticsPoints')
)
CREATE NONCLUSTERED INDEX IX_LP_CustomerHistory
ON dbo.LogisticsPoints (created_by, created_at DESC)
INCLUDE (point_id, order_type, status, delivery_status, lat, lon, driver_id);
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_LP_DriverHistory'
      AND object_id = OBJECT_ID('dbo.LogisticsPoints')
)
CREATE NONCLUSTERED INDEX IX_LP_DriverHistory
ON dbo.LogisticsPoints (driver_id, created_at DESC)
INCLUDE (point_id, order_type, status, delivery_status, lat, lon, created_by);
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE name = 'IX_Userstable_RoleStatus'
      AND object_id = OBJECT_ID('dbo.userstable')
)
CREATE NONCLUSTERED INDEX IX_Userstable_RoleStatus
ON dbo.userstable (role, current_status, is_locked)
INCLUDE (fullname, lat, lon);
GO

/* Quick verification */
SELECT
    SUM(CASE WHEN order_type IS NULL THEN 1 ELSE 0 END) AS null_order_type,
    SUM(CASE WHEN delivery_status IS NULL THEN 1 ELSE 0 END) AS null_delivery_status,
    SUM(CASE WHEN status IS NULL THEN 1 ELSE 0 END) AS null_status
FROM dbo.LogisticsPoints;
GO

SELECT name
FROM sys.indexes
WHERE object_id IN (OBJECT_ID('dbo.LogisticsPoints'), OBJECT_ID('dbo.userstable'))
  AND name IN (
      'IX_LP_ChainStatus',
      'IX_LP_CodStatusGroup',
      'IX_LP_CustomerHistory',
      'IX_LP_DriverHistory',
      'IX_Userstable_RoleStatus'
  )
ORDER BY name;
GO
