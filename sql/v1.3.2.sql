use postmaster;
alter table manager_url add href varchar(2000);
update manager_url set href = name;