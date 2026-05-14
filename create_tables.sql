-- Create tables for SRMS (Smart Respiratory Monitoring System)
-- This script will drop existing tables and recreate them

-- Drop tables in reverse order of dependencies
DROP TABLE IF EXISTS breathing_records;
DROP TABLE IF EXISTS assignments;
DROP TABLE IF EXISTS patients;
DROP TABLE IF EXISTS caregivers;
DROP TABLE IF EXISTS users;

-- Users table for authentication
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'caregiver', 'patient')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Patients table
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100),
    age INTEGER,
    condition TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Caregivers table
CREATE TABLE caregivers (
    id SERIAL PRIMARY KEY,
    caregiver_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100),
    specialization VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Assignments table (linking patients to caregivers)
CREATE TABLE assignments (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    caregiver_id VARCHAR(50) NOT NULL,
    assigned_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    FOREIGN KEY (patient_id) REFERENCES patients(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (caregiver_id) REFERENCES caregivers(caregiver_id) ON DELETE CASCADE
);

-- Breathing records table
CREATE TABLE breathing_records (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    rr INTEGER NOT NULL, -- Respiratory rate in breaths per minute
    status VARCHAR(20) NOT NULL CHECK (status IN ('normal', 'low', 'high', 'borderline')),
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for better performance
DROP INDEX IF EXISTS idx_breathing_records_patient_id;
DROP INDEX IF EXISTS idx_breathing_records_recorded_at;
DROP INDEX IF EXISTS idx_assignments_patient_id;
DROP INDEX IF EXISTS idx_assignments_caregiver_id;
DROP INDEX IF EXISTS idx_users_username;

CREATE INDEX idx_breathing_records_patient_id ON breathing_records(patient_id);
CREATE INDEX idx_breathing_records_recorded_at ON breathing_records(recorded_at);
CREATE INDEX idx_assignments_patient_id ON assignments(patient_id);
CREATE INDEX idx_assignments_caregiver_id ON assignments(caregiver_id);
CREATE INDEX idx_users_username ON users(username);