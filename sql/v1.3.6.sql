use postmaster;
alter table manager_previewinstance modify column sent_html longtext;
alter table manager_previewinstance ENGINE=InnoDB;
