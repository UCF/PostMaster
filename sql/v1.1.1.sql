use postmasterqa;
ALTER TABLE manager_email ADD preview_est_time datetime AFTER preview_recipients;
ALTER TABLE manager_email ADD live_est_time datetime AFTER preview_recipients;
ALTER TABLE manager_email ADD send_override tinyint(3) NOT NULL DEFAULT 1 AFTER preview_recipients;