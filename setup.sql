-- 1. Create the Leave Requests Table
CREATE TABLE leave_requests (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    student_name text NOT NULL,
    email text NOT NULL,
    department text NOT NULL,
    reason text NOT NULL,
    from_date date NOT NULL,
    to_date date NOT NULL,
    status text DEFAULT 'Pending', -- [Pending, HOD Approved, Principal Approved, Rejected]
    hod_remarks text,
    principal_remarks text,
    hod_email_body text,
    principal_email_body text,
    created_at timestamptz DEFAULT now()
);

-- 2. Disable Row Level Security (RLS) for testing
-- This allows the Flask app to call the API without complex Auth setup
ALTER TABLE leave_requests DISABLE ROW LEVEL SECURITY;

-- 3. Sample Insert Queries
INSERT INTO leave_requests (student_name, email, department, reason, from_date, to_date)
VALUES 
('Alice Smith', 'alice.smith@university.edu', 'Computer Science', 'Attending academic conference', '2026-05-10', '2026-05-12'),
('Bob Johnson', 'bob.johnson@university.edu', 'Mathematics', 'Personal medical emergency', '2026-05-15', '2026-05-20'),
('Carol White', 'carol.white@university.edu', 'Physics', 'Family event', '2026-06-01', '2026-06-02');
