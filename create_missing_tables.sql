-- Alternative: Create only missing tables (don't drop existing ones)

-- Users table for authentication (only if not exists)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'caregiver', 'patient')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Patients table (only if not exists)
CREATE TABLE IF NOT EXISTS patients (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100),
    age INTEGER,
    condition TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Caregivers table (only if not exists)
CREATE TABLE IF NOT EXISTS caregivers (
    id SERIAL PRIMARY KEY,
    caregiver_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100),
    specialization VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Assignments table (linking patients to caregivers) (only if not exists)
CREATE TABLE IF NOT EXISTS assignments (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    caregiver_id VARCHAR(50) NOT NULL,
    assigned_at TIMESTAMP DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'inactive'))
);

-- Add foreign keys if they don't exist (this is tricky in PostgreSQL)
-- You may need to run these separately if the tables already exist

-- Breathing records table (only if not exists)
CREATE TABLE IF NOT EXISTS breathing_records (
    id SERIAL PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL,
    rr INTEGER NOT NULL, -- Respiratory rate in breaths per minute
    status VARCHAR(20) NOT NULL CHECK (status IN ('normal', 'low', 'high', 'borderline')),
    recorded_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes (these will be created only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_breathing_records_patient_id ON breathing_records(patient_id);
CREATE INDEX IF NOT EXISTS idx_breathing_records_recorded_at ON breathing_records(recorded_at);
CREATE INDEX IF NOT EXISTS idx_assignments_patient_id ON assignments(patient_id);
CREATE INDEX IF NOT EXISTS idx_assignments_caregiver_id ON assignments(caregiver_id);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);