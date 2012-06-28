__author__ = 'jeffrey'

import sqlite3
from bottle import route, run, debug, static_file, jinja2_view as view, request, redirect
import os.path
from datetime import datetime

from main import Scraper
from utils import *

WEB_ROOT = os.path.abspath(os.path.dirname(__file__))

@route('/static/<filename:path>')
def send_static(filename):
    return static_file(filename, root=os.path.join(WEB_ROOT, 'static'))

@route('/')
@view('index')
def index(error_message=None, success_message=None):
    company_name = request.GET.get('company_name', None)
    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    companies = c.execute('SELECT DISTINCT COMPANY_NAME FROM COMPANY').fetchall()
    company_list = []
    for company in companies:
        company_list.append(company[0])

    if company_name and company_name != 'ALL':
        items = c.execute('SELECT * FROM COMPANY WHERE COMPANY_NAME = ? ORDER BY TIME_TAKEN DESC',
            (company_name, )).fetchall()
    else:
        items = c.execute('SELECT * FROM COMPANY ORDER BY TIME_TAKEN DESC').fetchall()
    c.close()
    conn.close()
    return dict(items=items, error_message=error_message, success_message=success_message, companies=company_list,
        company_name=company_name)


@route('/upload', method='GET')
@view('upload')
def upload(success_message=None, error_message=None):
    conn = sqlite3.connect('data/setting.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS CSV_DB
                 (
                 CSV_FILE_NAME TEXT,
                 CSV_FILE_PATH TEXT,
                 DB_FILE_NAME TEXT,
                 DB_FILE_PATH TEXT,
                 LAST_MODIFIED_TIME TIMESTAMP
                 )''')

    csv_db_list = c.execute('SELECT * FROM CSV_DB').fetchall()
    c.close()
    conn.close()
    return dict(error_message=error_message, csv_db_list = csv_db_list)

@route('/upload', method='POST')
@view('upload')
def do_upload():
    csvfile = request.files.get('csvfile', None)
    s = Scraper()
    try:
        if csvfile.file == None:
            raise Exception('The file is None')
        company_list = s.read_csv(csvfile.file)
        if len(company_list) > 0:
            # Save the file
            f = open('%s/data/%s' % (WEB_ROOT, csvfile.filename), 'w')
            f.write(csvfile.value)
            # Save to CSV_FILE db
            csv_file_path, db_file_path = save_csv_db(csvfile)
            # Run the scrape process in background
            f = open('%s/%s' % (WEB_ROOT, csvfile.filename), 'r')
            # TODO just upload, not scrape
            do_scrape_async(s, csv_file_path, db_file_path)
        else:
            raise Exception('The file is not format as company list')
    except Exception as e:
        print e
        return upload(error_message='Error: %s' % e.message)
        #return redirect('/')
    return upload(
        success_message='The file updated success and will do scrape in background. Please refrush page later to view the new data.')


@route('/settings', method='GET')
@view('settings')
def settings(error_message=None, success_message=None):
    setting = get_setting()
    return dict(setting=setting, error_message=error_message, success_message=success_message)

@route('/settings', method='POST')
@view('settings')
def do_settings():
    schedule_interval = request.forms.schedule_interval
    try:
        schedule_interval = int(schedule_interval)
        if schedule_interval < 300:
            raise Exception('The min schedule interval should be more than 300 seconds')
        conn = sqlite3.connect('data.db')
        c = conn.cursor()
        c.execute('UPDATE SETTINGS SET SCHEDULE_INTERVAL = ?, LAST_MODIFIED_TIME = ?',
            (schedule_interval, datetime.now()))
        conn.commit()
        c.close()
        conn.close()
        # Re schedule with new interval seconds
        cron.reSchedule(seconds=schedule_interval)
    except Exception as e:
        return settings(error_message=e.message)
    return settings(success_message='Settings has been updated!')


@route('/company_chart')
@view('company_chart')
def company_chart(error_message=None, success_message=None):
    company_name = request.GET.get('company_name', None)
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    companies = c.execute('SELECT DISTINCT COMPANY_NAME FROM COMPANY').fetchall()
    company_list = []
    for company in companies:
        company_list.append(company[0])

    if company_name == None or company_name == 'ALL':
        company_name = company_list[0]
    items = c.execute(
        'SELECT TSSH_PWR_REDUCED, TIME_TAKEN FROM COMPANY WHERE COMPANY_NAME = ? ORDER BY TIME_TAKEN ASC'
        , (company_name,)).fetchall()
    c.close()
    conn.close()
    return dict(items=items, error_message=error_message, success_message=success_message, companies=company_list,
        company_name=company_name)

@route('/macro_level_chart')
@view('macro_level_chart')
def macro_level_chart(error_message=None, success_message=None):
    company_name = request.GET.get('company_name', None)
    conn = sqlite3.connect('data.db')
    c = conn.cursor()

    companies = c.execute('SELECT DISTINCT COMPANY_NAME FROM COMPANY').fetchall()
    company_list = []
    for company in companies:
        company_list.append(company[0])

    if company_name and company_name != 'ALL':
        items = c.execute('SELECT * FROM COMPANY WHERE COMPANY_NAME = ? ORDER BY TIME_TAKEN DESC',
            (company_name, )).fetchall()
    else:
        items = c.execute('SELECT * FROM COMPANY ORDER BY TIME_TAKEN DESC').fetchall()
    c.close()
    conn.close()
    return dict(items=items, error_message=error_message, success_message=success_message, companies=company_list,
        company_name=company_name)

# Call cron.reSchedule to schedule the job with default interval(86400, 1 day) when start the webapp
import cron

schedule_interval = get_setting()[0]
cron.reSchedule(seconds=schedule_interval)

debug(True)
run(host='0.0.0.0', port=8880, reloader=True)
