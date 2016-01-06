use postmaster;
ALTER TABLE manager_email
CHANGE COLUMN updated_at updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;