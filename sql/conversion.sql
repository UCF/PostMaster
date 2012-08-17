/*
	Upgrades the postmaster database schema from the beta
	version of the software to v1.0.0.

*/


# Drop the tables that are no longer used
DROP TABLE `mailer_emaillabelrecipientfieldmapping`;
DROP TABLE `mailer_recipientrole`;

# Rename all the app tables mailer -> manager
RENAME TABLE 
	`mailer_email` TO `manager_email`,
	`mailer_email_recipient_groups` TO `manager_email_recipient_groups`,
	`mailer_email_unsubscriptions` TO `manager_email_unsubscriptions`,
	`mailer_instance` TO `manager_instance`,
	`mailer_instanceopen` TO `manager_instanceopen`,
	`mailer_instancerecipientdetails` TO `manager_instancerecipientdetails`,
	`mailer_recipient` TO `manager_recipient`,
	`mailer_recipientgroup` TO `manager_recipientgroup`,
	`mailer_recipientgroup_recipients` TO `manager_recipientgroup_recipients`,
	`mailer_url` TO `manager_url`,
	`mailer_urlclick` TO `manager_urlclick`;

# Modify email table schema
ALTER TABLE `manager_email` DROP COLUMN `html`;
ALTER TABLE `manager_email` ADD COLUMN `send_time` TIME NOT NULL AFTER `start_date`;

# Copy send times from mailer_emailsendtime then drop
UPDATE `manager_email` email SET `send_time` = (SELECT send_time FROM `mailer_emailsendtime` WHERE email_id = email.id)
DROP TABLE `mailer_emailsendtime`;

# Create recipient attribute table
CREATE TABLE `manager_recipientattribute` (
	`id` INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY,
	`recipient_id` INT(11) NOT NULL,
	`name` VARCHAR(100) NOT NULL,
	`value` VARCHAR(1000) NOT NULL
)

# Copy values from manager_recipient column
INSERT INTO manager_recipientattribute (recipient_id, name, value)
	(
		SELECT
			id AS recipient_id,
			'first_name' AS name,
			first_name AS value
		FROM
			manager_recipient
		WHERE
			first_name IS NOT NULL

	)

INSERT INTO manager_recipientattribute (recipient_id, name, value)
	(
		SELECT
			id AS recipient_id,
			'last_name' AS name,
			last_name AS value
		FROM
			manager_recipient
		WHERE
			last_name IS NOT NULL

	)

INSERT INTO manager_recipientattribute (recipient_id, name, value)
	(
		SELECT
			id AS recipient_id,
			'preferred_name' AS name,
			preferred_name AS value
		FROM
			manager_recipient
		WHERE
			preferred_name IS NOT NULL
	)

# Drop columsn from manager_recipient
ALTER TABLE manager_recipient DROP COLUMN `first_name`, `last_name`, `preferred_name`;