set autocommit=0;
use postmaster;
start transaction;

alter table `manager_instanceopen` add `is_reopen` tinyint(1) NOT NULL

commit;