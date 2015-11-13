use postmaster;
alter table manager_previewinstance modify column sent_html longtext;
alter table manager_previewinstance ENGINE=InnoDB;

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

ALTER TABLE manager_instanceopen
  ADD COLUMN is_reopen tinyint(1) NOT NULL

ALTER TABLE manager_instance
  ADD COLUMN send_terminate tinyint(1) NOT NULL