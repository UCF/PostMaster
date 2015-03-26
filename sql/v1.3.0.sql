use postmaster;
alter table manager_instance add litmus_id varchar(100);

### ADD locked_content and sent_html
alter table manager_previewinstance add sent_html text;
alter table manager_previewinstance add lock_content tinyint(1) not null default 0;
