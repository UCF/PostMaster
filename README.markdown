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
- Modify the following variables in settings_local.py based on the the deployment environment
	- PROJECT_URL
	- DATABASES
		- default
		- rds_wharehouse
	- AMAZON_SMTP
	- MANAGERS
	- PROCESSING_INTERVAL_DURATION
	- TEST_EMAIL_RECIPIENT
	- TEST_EMAIL_SOURCE_URI
- Schedule the mailer-process management command to run based on the PROCCESSING_INVERVAL DURATION variable
- Schedule the recipient-importers to run based on the availabiliy of their external data sources