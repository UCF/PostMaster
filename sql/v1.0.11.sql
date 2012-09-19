set autocommit=0;
use postmaster;
start transaction;

ALTER TABLE `manager_email` CHANGE `source_uri` `source_html_uri` VARCHAR(200) NOT NULL;
ALTER TABLE `manager_email` ADD COLUMN `source_text_uri` VARCHAR(200) NULL DEFAULT NULL AFTER `source_html_uri`;

commit;