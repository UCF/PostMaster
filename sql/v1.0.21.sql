set autocommit=0;
use postmaster;
start transaction;
ALTER TABLE `manager_instance` DROP COLUMN `in_progress`;

ALTER TABLE `manager_instance` ADD COLUMN `requested_start` TIME NULL AFTER `sent_html`;
UPDATE `manager_instance` JOIN `manager_email` ON `manager_instance`.`email_id` = `manager_email`.`id` SET `manager_instance`.`requested_start` = `manager_email`.`send_time`;
ALTER TABLE `manager_instance` MODIFY COLUMN `requested_start` TIME NOT NULL;

ALTER TABLE `manager_instance` DROP COLUMN `sent`;

ALTER TABLE `manager_instance` ADD COLUMN `success` TINYINT(1) NULL DEFAULT NULL AFTER `end`;
UPDATE `manager_instance` SET `manager_instance`.`success` = 1;

ALTER TABLE `manager_instancerecipientdetails` DROP COLUMN `exception_type`;
ALTER TABLE `manager_instancerecipientdetails` MODIFY COLUMN `when` DATETIME NULL DEFAULT NULL;

commit;