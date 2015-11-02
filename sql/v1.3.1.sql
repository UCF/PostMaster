set autocommit=0;
use postmaster;
start transaction;

ALTER TABLE manager_recipientgroup ADD created_at datetime;
ALTER TABLE manager_recipientgroup ADD updated_at timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL;

UPDATE
	manager_recipientgroup
SET
	created_at = CURRENT_TIMESTAMP,
	updated_at = CURRENT_TIMESTAMP;

ALTER TABLE manager_email ADD created_at datetime;
ALTER TABLE manager_email ADD updated_at timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL;

UPDATE
	manager_email
SET
	created_at = CURRENT_TIMESTAMP,
	updated_at = CURRENT_TIMESTAMP;

ALTER TABLE manager_email
  ADD COLUMN creator_id int(11) DEFAULT NULL,
  ADD CONSTRAINT FK_AUTH_USER_TABLE_CREATOR_ID FOREIGN KEY (creator_id)
  REFERENCES auth_user (id)

commit;