-- ============================================================
-- BinBuddy Smart Waste Management System
-- Complete MySQL Database Schema
-- ============================================================

CREATE DATABASE IF NOT EXISTS binbuddy_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE binbuddy_db;

-- ─── ZONES / WARDS ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS zones (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(100) NOT NULL,
  ward_number VARCHAR(20)  NOT NULL UNIQUE,
  city        VARCHAR(100) DEFAULT 'City',
  created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ward (ward_number)
) ENGINE=InnoDB;

-- ─── USERS ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(120)             NOT NULL,
  email       VARCHAR(200)             NOT NULL UNIQUE,
  password    VARCHAR(255)             NOT NULL,    -- bcrypt hash
  role        ENUM('admin','collector','citizen') DEFAULT 'citizen',
  phone       VARCHAR(20),
  zone_id     INT,
  is_approved TINYINT(1) DEFAULT 0,
  is_active   TINYINT(1) DEFAULT 1,
  points      INT DEFAULT 0,
  tier        VARCHAR(50) DEFAULT 'bronze',
  created_at  DATETIME   DEFAULT CURRENT_TIMESTAMP,
  last_login  DATETIME   NULL,
  FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE SET NULL,
  INDEX idx_email (email),
  INDEX idx_role  (role),
  INDEX idx_points (points)
) ENGINE=InnoDB;

-- ─── BINS ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bins (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  bin_code      VARCHAR(50)  NOT NULL UNIQUE,
  location_name VARCHAR(200),
  latitude      DECIMAL(10,7) NOT NULL,
  longitude     DECIMAL(10,7) NOT NULL,
  capacity_cm   INT           DEFAULT 100,
  fill_level    FLOAT         DEFAULT 0.0,
  distance_cm   FLOAT DEFAULT 0.0,   -- ADDED THIS new
  status        ENUM('empty','half','full','collected','maintenance') DEFAULT 'empty',
  zone_id       INT           NOT NULL,
  battery_level FLOAT         DEFAULT 100.0,
  device_id     VARCHAR(100)  UNIQUE,
  is_active     TINYINT(1)   DEFAULT 1,
  last_updated  DATETIME      DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  created_at    DATETIME      DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (zone_id) REFERENCES zones(id),
  INDEX idx_zone   (zone_id),
  INDEX idx_status (status),
  INDEX idx_device (device_id)
) ENGINE=InnoDB;

-- ─── COLLECTIONS ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS collections (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  bin_id              INT NOT NULL,
  collector_id        INT,
  collected_at        DATETIME  DEFAULT CURRENT_TIMESTAMP,
  fill_at_collection  FLOAT,
  notes               TEXT,
  verified            TINYINT(1) DEFAULT 0,
  FOREIGN KEY (bin_id)       REFERENCES bins(id),
  FOREIGN KEY (collector_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_bin       (bin_id),
  INDEX idx_collector (collector_id),
  INDEX idx_date      (collected_at)
) ENGINE=InnoDB;

-- ─── COMPLAINTS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS complaints (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  citizen_id   INT NOT NULL,
  bin_id       INT,
  category     ENUM('overflow','damage','missing','smell','other') DEFAULT 'overflow',
  description  TEXT,
  image_path   VARCHAR(300),
  status       ENUM('open','in_progress','resolved','closed') DEFAULT 'open',
  priority     ENUM('low','medium','high') DEFAULT 'medium',
  assigned_to  INT,
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  resolved_at  DATETIME NULL,
  FOREIGN KEY (citizen_id)  REFERENCES users(id),
  FOREIGN KEY (bin_id)      REFERENCES bins(id) ON DELETE SET NULL,
  FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_status   (status),
  INDEX idx_citizen  (citizen_id)
) ENGINE=InnoDB;

-- ─── NOTIFICATIONS ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT,
  title      VARCHAR(200),
  message    TEXT,
  type       ENUM('alert','info','warning','success') DEFAULT 'info',
  is_read    TINYINT(1) DEFAULT 0,
  created_at DATETIME   DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  INDEX idx_user   (user_id),
  INDEX idx_unread (is_read)
) ENGINE=InnoDB;

-- ─── TRUCKS ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trucks (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  vehicle_number VARCHAR(50)  NOT NULL UNIQUE,
  driver_name    VARCHAR(120),
  zone_id        INT,
  status         ENUM('available','on_route','maintenance') DEFAULT 'available',
  last_lat       DECIMAL(10,7),
  last_lng       DECIMAL(10,7),
  last_seen      DATETIME,
  FOREIGN KEY (zone_id) REFERENCES zones(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ─── AUDIT LOGS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT,
  action     VARCHAR(200),
  entity     VARCHAR(100),
  entity_id  INT,
  details    TEXT,
  ip_address VARCHAR(50),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
  INDEX idx_user   (user_id),
  INDEX idx_action (action)
) ENGINE=InnoDB;

-- ─── REWARDS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rewards (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  name             VARCHAR(255) NOT NULL,
  description      TEXT,
  points_required  INT NOT NULL,
  category         VARCHAR(50),
  reward_type      ENUM('discount','voucher','gift','badge') DEFAULT 'voucher',
  value            VARCHAR(100),
  is_active        TINYINT(1) DEFAULT 1,
  created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_points (points_required)
) ENGINE=InnoDB;

-- ─── POINTS LEDGER ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS points_ledger (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  user_id      INT NOT NULL,
  complaint_id INT,
  points_earned INT NOT NULL,
  reason       VARCHAR(255),
  action_type  ENUM('complaint_filed','complaint_resolved','complaint_validated','early_resolve','quality_report') DEFAULT 'complaint_filed',
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (complaint_id) REFERENCES complaints(id) ON DELETE SET NULL,
  INDEX idx_user (user_id),
  INDEX idx_complaint (complaint_id),
  INDEX idx_date (created_at)
) ENGINE=InnoDB;

-- ─── USER REWARDS (Redemption History) ────────────────────────
CREATE TABLE IF NOT EXISTS user_rewards (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  user_id     INT NOT NULL,
  reward_id   INT NOT NULL,
  redeemed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  status      ENUM('pending','claimed','expired') DEFAULT 'pending',
  claim_code  VARCHAR(100) UNIQUE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (reward_id) REFERENCES rewards(id) ON DELETE CASCADE,
  INDEX idx_user (user_id),
  INDEX idx_status (status)
) ENGINE=InnoDB;

-- ============================================================
-- SEED DATA (Sample municipal data)
-- ============================================================

-- Zones / Wards
INSERT INTO zones (name, ward_number, city) VALUES
  ('Gandhi Nagar Ward',  'W01', 'Nashik'),
  ('Nehru Nagar Ward',   'W02', 'Nashik'),
  ('Panchavati Ward',    'W03', 'Nashik'),
  ('Satpur Ward',        'W04', 'Nashik'),
  ('Cidco Ward',         'W05', 'Nashik');

-- Admin user (password: admin123)
-- bcrypt hash of 'admin123' with 12 rounds
INSERT INTO users (name, email, password, role, is_approved) VALUES
  ('Municipal Admin',   'admin@municipal.gov.in',
   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TsCwjlg2dl68uNf6oP3cFJRRhUQC',
   'admin', 1);

-- Collector users
INSERT INTO users (name, email, password, role, phone, zone_id, is_approved) VALUES
  ('Ramesh Patil',  'ramesh@mc.gov.in',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TsCwjlg2dl68uNf6oP3cFJRRhUQC', 'collector', '9876543210', 1, 1),
  ('Sanjay Kumar',  'sanjay@mc.gov.in',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TsCwjlg2dl68uNf6oP3cFJRRhUQC', 'collector', '9876543211', 2, 1),
  ('Priya Sharma',  'priya@mc.gov.in',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TsCwjlg2dl68uNf6oP3cFJRRhUQC', 'collector', '9876543212', 3, 0);

-- Sample bins
INSERT INTO bins (bin_code, location_name, latitude, longitude, zone_id, fill_level, status, device_id) VALUES
  ('BIN-W01-001', 'Gandhi Chowk Main',  20.00590, 73.76670, 1, 92.0, 'full',  'ESP-001'),
  ('BIN-W01-002', 'Market Road Entry',  20.01200, 73.77100, 1, 55.0, 'half',  'ESP-002'),
  ('BIN-W01-003', 'Park Gate North',    20.00800, 73.76200, 1, 10.0, 'empty', 'ESP-003'),
  ('BIN-W02-001', 'Nehru Park South',   19.99900, 73.76400, 2, 88.0, 'full',  'ESP-004'),
  ('BIN-W02-002', 'College Road Stop',  20.02000, 73.75800, 2, 40.0, 'half',  'ESP-005'),
  ('BIN-W03-001', 'Central Bus Stand',  20.00800, 73.78000, 3, 75.0, 'half',  'ESP-006'),
  ('BIN-W03-002', 'Hospital Gate',      19.99500, 73.77200, 3,  5.0, 'empty', 'ESP-007'),
  ('BIN-W04-001', 'Satpur Industrial',  20.03000, 73.74000, 4, 60.0, 'half',  'ESP-008'),
  ('BIN-W05-001', 'CIDCO Sector 1',     20.01500, 73.78500, 5, 20.0, 'empty', 'ESP-009'),
  ('BIN-W05-002', 'CIDCO Sector 2',     20.01800, 73.79000, 5, 95.0, 'full',  'ESP-010');

-- Sample complaints
INSERT INTO complaints (citizen_id, bin_id, category, description, priority, status) VALUES
  (4, 1, 'overflow',  'Bin near Gandhi Chowk is overflowing since morning', 'high', 'open'),
  (4, 4, 'smell',     'Bad odour from bin on Nehru Park road',              'medium','in_progress'),
  (4, 2, 'damage',    'Lid of Market Road bin is broken',                   'low',   'resolved');

-- Sample collections today
INSERT INTO collections (bin_id, collector_id, fill_at_collection, notes) VALUES
  (3, 2, 98.0, 'Collected — bin was nearly full'),
  (7, 3, 85.0, 'Regular morning round');
