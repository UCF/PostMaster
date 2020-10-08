# Postmaster Emailer System

An application for sending emails with remote content to arbitrary recipients. Utilizes the Amazon Web Service's Simple Email Service.


## Requirements

### Installation requirements
- Python 3.8+
- [python-ldap build prerequisites](https://www.python-ldap.org/en/latest/installing.html#build-prerequisites)
	- via Homebrew: `brew install openldap`
- pip

### Development requirements
- node
- gulp-cli


## Installation and Setup

1. Create a new virtual environment and `cd` to it (replace `ENV` below with the path to the directory you're installing your virtual environment in):

        python3 -m venv ENV
		cd ENV
3. Clone the repo to a subdirectory `src`:

		git clone git@github.com:UCF/PostMaster.git src
4. Activate the virtual environment:

        source bin/activate
5. `cd` to the new `src` directory and install requirements:

        cd src
        pip install -r requirements.txt

    **NOTE:** if `pip install` returns a block of error text including `fatal error: 'sasl.h' file not found` upon installing `python-ldap`, do the following:

    1. In requirements.txt, comment out the `python-ldap` requirement.
    2. Re-run `pip install -r requirements.txt`.  It should complete successfully.
    3. Run the following, replacing "VERSION" with the version number specified for the `python-ldap` package in requirements.txt:

            pip install python-ldap==VERSION \
            --global-option=build_ext \
            --global-option="-I$(xcrun --show-sdk-path)/usr/include/sasl"

    4. Un-comment the `python-ldap` requirement in requirements.txt and save the file.
6. Create a local settings file:

		cp settings_local.template.py settings_local.py
7. Configure `settings_local.py` as necessary for your environment:
	- When developing locally, set `LOCAL_DEBUG` to `True` to ensure static files are properly served up.
8. Run the deployment command:

		python manage.py deploy

	This command runs migrations and any other general setup steps.
9. Set the default value for `manager_recipient.disable` in your `default` database to `False` (https://code.djangoproject.com/ticket/470)
10. **Production only:** Schedule management commands to run on regular intervals via automation/cron:
	- Schedule the `mailer-process` management command to run based on the `PROCESSING_INTERVAL_DURATION` setting
	- Schedule the `recipient-importers` management command to run based on the availability of their external data sources
10. **Optional**: Create new Setting objects, which are used for setting global value across the application (start server > log in > Settings > Add New):
	- `office_hours_contact_info`: displays next to the office hours section on the home page when logged in
	- `after_hours_contact_info`: displays next to the after hours section on the home page when logged in


## Development

1. If you haven't yet already, follow the [Installation steps](#installation-and-setup) above to install and set up the project on your development environment.
2. From the root directory of the repo, create a new `gulp-config.json`:

		cp gulp-config.template.json gulp-config.json

	and update settings in `gulp-config.json` as desired.  Setting `sync` to `true` will enable automatic browser refreshing when changes to files are made while `gulp watch` is running (see below).
3. Install required npm packages:

		npm install
4. Use gulp to process and minify source scss and js files in `src/scss` and `src/js`:
	- Run everything: `gulp default`
	- Watch changes, with optional browser reloading: `gulp watch`

	gulp will save processed files to `static`.  Files in `static` should be committed with git, but should never be modified directly.


## Testing

1. Be sure the `TEST_EMAIL_RECIPIENT`, `TEST_EMAIL_SOURCE_HTML_URI`, and `TEXT_EMAIL_SOURCE_TEXT_URI` variables are set appropriately
2. Be sure the application's database credentials have CREATE DATABASE privileges. This is needed because separate test databases are created during the testing process.
3. Be sure the application can connect out to Amazon Web Services.
4. From the command line, run `python manage.py test manager` in the project's root directory.


## Upgrading

- To **v3.0.0**
	- If you have an existing virtual environment created using python 2.7, delete this environment - `rm -rf virtualenv-directory/` - and run through the installation instructions above.
- To **v2.0.0**
	- Ensure virtual environment is using python 2.7+
	- Pull down 2.0.0 code
	- `pip install -r requirements` to upgrade django.
	- It may be necessary to reactivate the virtual environment: `source ../bin/activate`
	- Compare `settings_local.py` with `settings_local.template.py` and make appropriate change.
	- Fake the initial migrations: `python manage.py migrate --fake-initial`
	- Migrate any other changes in 2.0.0: `python manage.py migrate`
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
