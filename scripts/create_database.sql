-- MySQL 8.4 Database Setup Script for AODA Compliance Checker
-- This script creates the database and user for the application

-- Create database
CREATE DATABASE IF NOT EXISTS aoda_checker
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Create user (change password in production!)
CREATE USER IF NOT EXISTS 'aoda_user'@'%' IDENTIFIED BY 'aoda_password';

-- Grant privileges
GRANT ALL PRIVILEGES ON aoda_checker.* TO 'aoda_user'@'%';

-- Flush privileges
FLUSH PRIVILEGES;

-- Use the database
USE aoda_checker;

-- Show created database
SELECT 'Database created successfully!' AS message;
SHOW DATABASES LIKE 'aoda_checker';

