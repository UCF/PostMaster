set autocommit=0;
use postmaster;
start transaction;

ALTER TABLE manager_recipientgroup ADD created_at datetime;
ALTER TABLE manager_recipientgroup ADD updated_at datetime;

commit;