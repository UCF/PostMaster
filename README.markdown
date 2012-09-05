Postmaster Emailer System
=========================
An application for sending emails with remote content to arbitrary recipients. Utilizes the Amazon Web Service's Simple Email Service.

Requirements
------------
- Python 2.7+
- Django 1.4+
- MySQL Python

Configuration
----------
- Be sure the application can read and write to logs/application.log
- Modify the following variables in settings_local.py based on the the deployment environment. An explanation of each is included in the file.
	- PROJECT_URL
	- DATABASES
		- default
		- rds_wharehouse
	- AMAZON_SMTP
	- MANAGERS
	- PROCESSING_INTERVAL_DURATION
	- TEST_EMAIL_RECIPIENT
	- TEST_EMAIL_SOURCE_HTML_URI
	- TEST_EMAIL_SOURCE_TEXT_URI
- Schedule the mailer-process management command to run based on the PROCCESSING_INVERVAL DURATION variable (PRODUCTION ONLY)
- Schedule the recipient-importers to run based on the availabiliy of their external data sources (PRODUCTION ONLY)

Testing
-------
1. Be sure the TEST_EMAIL_RECIPIENT, TEST_EMAIL_SOURCE_HTML_URI, and TEXT_EMAIL_SOURCE_TEXT_URI variables are set appropriately
2. Be sure the application's database credentials have CREATE DATABASE privileges. This is needed because separate test databases are created during the testing process.
3. Be sure the application can connect out to Amazon Web Services.
4. From the command line, run `python manage.py test manager` in the project's root directory.

Upgrading
---------
- To v1.0.21
	- Remove `manager_instance.in_progress` column
	- Create `manager_instance.requested_start` column with the following definitions: `TIME NOT NULL AFTER send_html`
	- Run the following SQL query: `UPDATE manager_instance JOIN manager_email ON manager_instance.email_id = manager_email.id SET manager_instance.requested_start = manager_email.send_time`
	- Remove `manager_instance.sent` column
	- Create `manager_instance.success` column with the followign defintion: `TINYINT(1) NULL DEFAULT NULL AFTER end`
	- Run the following SQL query: `UPDATE manager_instance SET success = 1;`
- To v1.0.11
	- Rename `manager_email.source_uri` column to `manager_email.source_html_uri`
	- Create `manager_email.source_text_uri` column with the following definition: `VARCHAR(200) NULL DEFAULT NULL AFTER source_html_uri`
	- Rename `TEST_EMAIL_SOURCE_URI` to `TEST_EMAIL_SOURCE_HTML_URI` in settings_local.py
	- Add `TEST_EMAIL_SOURCE_TEXT_URI` setting to settings_local.py (see settings_local.template.py)