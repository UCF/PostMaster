set autocommit=0;
use postmaster;
start transaction;

ALTER TABLE `manager_recipient` ADD COLUMN `disable` tinyint(1) NOT NULL DEFAULT '0' AFTER `email_address`;

commit;