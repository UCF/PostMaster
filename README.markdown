Postmaster Emailer System
=========================
An application for sending emails with remote content to arbitrary recipients. Utilizes the Amazon Web Service's Simple Email Service.

Requirements
------------
- Python 2.7+
- Django 1.4+
- MySQL Python
- Python LDAP
- Python Requests
- node v0.10.22+
- gulp v3.9.0+

Configuration
----------
- Be sure the application can read and write to logs/application.log or, if using, the Windows event logger (see settings_local.py) be sure the win32 Python extensions are installed. They can be downloaded here: http://sourceforge.net/projects/pywin32/
- Modify the following variables in settings_local.py based on the the deployment environment. An explanation of each is included in the file.
	- PROJECT_URL
	- DATABASES
		- default
		- rds_wharehouse
	- AMAZON_SMTP
	- MANAGERS
	- PROCESSING_INTERVAL_DURATION
	- MINIMUM_IMPORT_EMAIL_COUNT
	- TEST_EMAIL_RECIPIENT
	- TEST_EMAIL_SOURCE_HTML_URI
	- TEST_EMAIL_SOURCE_TEXT_URI
- Make sure to set the default value for Recipient disable on the DB to False (https://code.djangoproject.com/ticket/470)
- Schedule the mailer-process management command to run based on the PROCCESSING_INVERVAL DURATION variable (PRODUCTION ONLY)
- Schedule the recipient-importers to run based on the availabiliy of their external data sources (PRODUCTION ONLY)
- Settings are used for setting global value across the application
	- office_hours_contact_info: displays next to the office hours section on the home page when logged in
	- after_hours_contact_info: displays next to the after hours section on the home page when logged in

Setup Python Environment
-------
- virtualenv postmaster
- cd postmaster/
- git clone git@github.com:UCF/PostMaster.git src
- source bin/activate
- cd src/
- pip install -r requirements.txt
- Due to a bug with this particular version of virtualenv you may need to reactivate
	- deactivate
	- source ../bin/activate
- create database defined in settings_local.py
- python manage.py syncdb
- npm install
- python manage.py runserver - to run webserver

2.0.0 Upgrade
-------
- Ensure virtual environment is using python 2.7+
- Pull down 2.0.0 code
- `pip install -r requirements` to upgrade django.
- It may be necessary to reactivate the virtual environment: `source ../bin/activate`
- Compare `settings_local.py` with `settings_local.template.py` and make appropriate change.
- Fake the initial migrations: `python manage.py migrate --fake-initial`
- Migrate any other changes in 2.0.0: `python manage.py migrate`

Development
-------
- Make sure an up to date version of node is installed
- Pull down the repo and `cd` into it.  Run `npm install` to install node packages in package.json, including gulp and bower.  Node packages will save to a `node_modules` directory in the root of the repo.
- Install all front-end components and compile static assets by running `gulp default`.  During development, run `gulp watch` to detect static file changes automatically and run minification and compilation commands on the fly.
- Make sure up-to-date concatenated/minified files are pushed up to the repo when making changes to static files.
- Create a config.json from from config.template.json and update based on your preferences.

Testing
-------
1. Be sure the TEST_EMAIL_RECIPIENT, TEST_EMAIL_SOURCE_HTML_URI, and TEXT_EMAIL_SOURCE_TEXT_URI variables are set appropriately
2. Be sure the application's database credentials have CREATE DATABASE privileges. This is needed because separate test databases are created during the testing process.
3. Be sure the application can connect out to Amazon Web Services.
4. From the command line, run `python manage.py test manager` in the project's root directory.

Upgrading
---------
- To v1.0.27
	- Modify `manager_previewinstance.requested_start` to have the following defintion: `DATETIME NOT NULL`
	- Modify `manager_instance.requested_start` to have the following defintion: `DATETIME NOT NULL`
- To v1.0.21
	- Remove `manager_instance.in_progress` column
	- Create `manager_instance.requested_start` column with the following definition: `TIME NOT NULL AFTER sent_html`
	- Run the following SQL query: `UPDATE manager_instance JOIN manager_email ON manager_instance.email_id = manager_email.id SET manager_instance.requested_start = manager_email.send_time`
	- Remove `manager_instance.sent` column
	- Create `manager_instance.success` column with the followign definition: `TINYINT(1) NULL DEFAULT NULL AFTER end`
	- Run the following SQL query: `UPDATE manager_instance SET success = 1;`
	- Remove `manager_instancerecipientdetails.exception_type` column
	- Modify `manager_instancerecipientdetails.when` to the following definition `DATETIME NULL DEFAULT NULL`
	- Run `python manage.py syncdb` to create the `manager_previewinstance` table
- To v1.0.11
	- Rename `manager_email.source_uri` column to `manager_email.source_html_uri`
	- Create `manager_email.source_text_uri` column with the following definition: `VARCHAR(200) NULL DEFAULT NULL AFTER source_html_uri`
	- Rename `TEST_EMAIL_SOURCE_URI` to `TEST_EMAIL_SOURCE_HTML_URI` in settings_local.py
	- Add `TEST_EMAIL_SOURCE_TEXT_URI` setting to settings_local.py (see settings_local.template.py)

Windows Event Logger
--------------------
To utilize the Windows event logger log handler, the win32 Python extensions must be installed. They can be downloaded here: http://sourceforge.net/projects/pywin32/
