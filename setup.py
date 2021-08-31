from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

long_description = (here / 'README.markdown').read_text(encoding='utf-8')

setup(
    name='PostMaster',
    version='3.2.1',
    description='An application for sending emails with remote content to arbitrary recipients.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/UCF/PostMaster/',
    author='UCF Web Communications',
    author_email='webcom@ucf.edu',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: UCF Community',
        'Topic :: UCF Communications :: Utility',
        'License :: MIT',
        'Programming Language :: Python :: 3 :: Only'
    ],
    packages=find_packages('.'),
    install_requires=[
        'Django==3.1.12',
        'django-widget-tweaks',
        'gunicorn',
        'mysqlclient',
        'python-ldap',
        'requests==2.25.1',
        'tqdm',
        'unicodecsv',
        'Unidecode',
        'urllib3>=1.26',
        'beautifulsoup4',
        'boto'
    ]
)
