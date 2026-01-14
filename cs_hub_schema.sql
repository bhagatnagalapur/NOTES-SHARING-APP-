USE cs_study_hub;

-- 1. DISABLE Safety Checks (Allows us to delete the table)
SET FOREIGN_KEY_CHECKS = 0;

-- 2. Drop the old table
DROP TABLE IF EXISTS users;

-- 3. Create the NEW, Correct Table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    uccms_number VARCHAR(20) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('student', 'admin') DEFAULT 'student',
    account_status ENUM('pending', 'approved', 'rejected', 'banned') DEFAULT 'approved',
    department VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL
);

-- 4. RE-ENABLE Safety Checks
SET FOREIGN_KEY_CHECKS = 1;

-- 5. Add your Admin Account back (Optional)
INSERT INTO users (uccms_number, full_name, password_hash, role, account_status)
VALUES ('12345', 'Admin User', SHA2('password', 256), 'admin', 'approved');