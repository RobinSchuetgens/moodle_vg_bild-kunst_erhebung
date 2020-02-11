import sys
import os
import pymysql.cursors
import random
import time
import json
import distutils
import math
import re
from pathlib import Path
from os.path import join, dirname
from shutil import copy
from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

# Accessing variables.
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASS = os.getenv('DB_PASS')
DB_PREF = os.getenv('DB_PREF')
BASE_URL = os.getenv('BASE_URL')
FILE_DIR = os.getenv('FILE_DIR')
SAMPLE_SIZE = int(os.getenv('SAMPLE_SIZE'))
RANDOM_SAMPLE = distutils.util.strtobool(os.getenv('RANDOM_SAMPLE'))
COPY_FILES = distutils.util.strtobool(os.getenv('COPY_FILES'))
MAX_FILE_SIZE_IN_MB = int(os.getenv('MAX_FILE_SIZE_IN_MB'))
OUTFILE_PATH = os.getenv('OUTFILE_PATH')
OUTFILE_NAME = os.getenv('OUTFILE_NAME')
EXCLUDE_CATEGORY_IDS = os.getenv('EXCLUDE_CATEGORY_IDS') if os.getenv('EXCLUDE_CATEGORY_IDS') != '' else ''
COURSE_IDS = os.getenv('COURSE_IDS') if os.getenv('COURSE_IDS') != '' else []
COURSE_IDS_STR = os.getenv('COURSE_IDS') if os.getenv('COURSE_IDS') == '' else ''

# SQL Queries
SQL_GET_COURSES = """SELECT c.id as CourseId, c.fullname as Coursename, cat.name as Categoryname, COUNT(ra.roleid) as ActiveUsers
                  FROM course c
                  LEFT OUTER JOIN context cx ON c.id = cx.instanceid
                  LEFT OUTER JOIN role_assignments ra ON cx.id = ra.contextid AND ra.roleid = '5'
                  INNER JOIN course_categories cat ON cat.id = c.category
                  WHERE c.visible = 1 AND cat.id NOT IN ({EXCLUDE_CATEGORY_IDS})
                  GROUP BY c.id
                  HAVING activeusers > 0;"""
SQL_GET_FILES = """SELECT cm.id AS ModuleID, cm.course AS CourseID, c.shortname AS CourseName, cm.module AS Module, mdl.name AS ModuleType,
                CASE
                    WHEN mf.name IS NOT NULL THEN mf.name
                    WHEN mb.name IS NOT NULL THEN mb.name
                    WHEN mr.name IS NOT NULL THEN mr.name
                    WHEN mu.name IS NOT NULL THEN mu.name
                    WHEN mq.name IS NOT NULL THEN mq.name
                    WHEN mp.name IS NOT NULL THEN mp.name
                    WHEN ml.name IS NOT NULL THEN ml.name
                    WHEN mw.name IS NOT NULL THEN mw.name
                    WHEN mla.name IS NOT NULL THEN mla.name
                    ELSE NULL
                END AS ActivityName,
                CASE
                    WHEN mf.name IS NOT NULL THEN CONCAT('{BASE_URL}/mod/forum/view.php?id=', cm.id)
                    WHEN mb.name IS NOT NULL THEN CONCAT('{BASE_URL}/mod/book/view.php?id=', cm.id)
                    WHEN mr.name IS NOT NULL THEN CONCAT('{BASE_URL}/mod/resource/view.php?id=', cm.id)
                    WHEN mu.name IS NOT NULL THEN CONCAT('{BASE_URL}/mod/url/view.php?id=', cm.id)
                    WHEN mq.name IS NOT NULL THEN CONCAT('{BASE_URL}/mod/quiz/view.php?id=', cm.id)
                    WHEN mp.name IS NOT NULL THEN CONCAT('{BASE_URL}/mod/page/view.php?id=', cm.id)
                    WHEN ml.name IS NOT NULL THEN CONCAT('{BASE_URL}/mod/lesson/view.php?id=', cm.id)
                    WHEN mw.name IS NOT NULL THEN CONCAT('{BASE_URL}/mod/wiki/view.php?id=', cm.id)
                    WHEN mla.name IS NOT NULL THEN CONCAT('{BASE_URL}/mod/label/view.php?id=', cm.id)
                    ELSE NULL
                END AS Link, f.id AS FileID, f.filepath AS FilePath, f.filename as FileName, CONCAT('{FILE_DIR}/', SUBSTRING(f.contenthash, 1, 2), '/', SUBSTRING(f.contenthash, 3, 2), '/', f.contenthash) AS FileSystemPath, f.userid AS FileAuthorID, f.filesize as FileSize, f.mimetype as FileMimeType, f.author AS FileAuthor, f.timecreated as TimeCreated, f.timemodified AS TimeModified
            FROM {DB_PREF}course_modules AS cm
            INNER JOIN {DB_PREF}context AS ctx ON ctx.contextlevel = 70 AND ctx.instanceid = cm.id
            INNER JOIN {DB_PREF}modules AS mdl ON cm.module = mdl.id
            INNER JOIN {DB_PREF}course AS c ON c.id = cm.course
            LEFT JOIN {DB_PREF}forum AS mf ON mdl.name = 'forum' AND cm.instance = mf.id
            LEFT JOIN {DB_PREF}book AS mb ON mdl.name = 'book' AND cm.instance = mb.id
            LEFT JOIN {DB_PREF}resource AS mr ON mdl.name = 'resource' AND cm.instance = mr.id
            LEFT JOIN {DB_PREF}url AS mu ON mdl.name = 'url' AND cm.instance = mu.id
            LEFT JOIN {DB_PREF}quiz AS mq ON mdl.name = 'quiz' AND cm.instance = mq.id
            LEFT JOIN {DB_PREF}page AS mp ON mdl.name = 'page' AND cm.instance = mp.id
            LEFT JOIN {DB_PREF}lesson AS ml ON mdl.name = 'lesson' AND cm.instance = ml.id
            LEFT JOIN {DB_PREF}wiki AS mw ON mdl.name = 'wiki' AND cm.instance = mw.id 
            LEFT JOIN {DB_PREF}label AS mla ON mdl.name = 'label' AND cm.instance = mla.id
            LEFT JOIN {DB_PREF}files AS f ON f.contextid = ctx.id
            WHERE (f.id IS NOT NULL AND f.filename <> '.') AND mdl.name IN ('forum', 'book', 'resource', 'url', 'quiz', 'page', 'lesson', 'label', 'wiki') AND cm.course IN ({COURSE_IDS_STR}) ORDER BY CourseID ASC;"""

def get_courses(connection):
  print('\nFetching course ids from database:')
  global EXCLUDE_CATEGORY_IDS
  course_ids = []

  with connection.cursor() as cursor:
    if EXCLUDE_CATEGORY_IDS != None:
      EXCLUDE_CATEGORY_IDS = "''"
    cursor.execute(SQL_GET_COURSES.format(**globals()))
    result = cursor.fetchall()
    for course in result:
      course_ids.append(course['CourseId'])
    print('Working on the following course ids: ' + ','.join(map(str, course_ids)))

  return course_ids

def get_files(connection, course_ids):
  print('\nFetching files for course ids and getting the corresponding file authors:')
  global COURSE_IDS_STR
  global RANDOM_SAMPLE
  COURSE_IDS_STR = ','.join(map(str, course_ids))
  result = {}
  stats = {}
  with connection.cursor() as cursor:
    cursor.execute(SQL_GET_FILES.format(**globals()))
    rows = cursor.fetchall()
    stats['file_count'] = len(rows)
    stats['mimetypes'] = {}
    stats['authors'] = 0
    stats['courses'] = 0
    stats['exceeds_file_size_limit_count'] = 0
    stats['exceeds_file_size_limit'] = []
    if RANDOM_SAMPLE == True:
      sample = int(round(len(rows) * ( SAMPLE_SIZE / 100 ),0))
      print('\nUsing random sample of size: ' + str(sample))
      rows = [
          rows[i] for i in sorted(random.sample(range(len(rows)), sample))
      ]
      stats['file_count_after_sample'] = len(rows)
    print('\nCopying '+ str(len(rows)) + ' files to "export/"')
    for row in rows:
      author_id = row['FileAuthorID']
      author_name = slugify_str(row['FileAuthor'])
      course_id = int(row['CourseID'])
      course_name = row['CourseName']
      file_name = row['FileName']
      file_path = row['FileSystemPath']
      file_size = row['FileSize']
      mimetype = row['FileMimeType']
      link = row['Link']
      print("{course_id}, {file_path}, {file_size}, {author_name}, {file_name}".format(**locals()))

      file_dict = {
        'filepath': file_path,
        'filesize': file_size,
        'filename': file_name,
        'mimetype': mimetype,
        'link': link
      }

      if not author_name in result:
        result[author_name] = {
          'name' : row['FileAuthor'],
          'courses': {}
        }
        stats['authors'] += 1

      if not course_id in result[author_name]['courses']:
        result[author_name]['courses'] = {
          course_id: {
            'name': course_name,
            'files': [file_dict]
          }
        }
        stats['courses'] += 1
      else:
        courses = result[author_name]['courses']
        files = result[author_name]['courses'][course_id]['files']
        files.append(file_dict)
        courses[course_id] = {
          'name': course_name,
          'files': files
        }

      if mimetype in stats['mimetypes']:
        stats['mimetypes'][mimetype] += 1
      else:
        stats['mimetypes'][mimetype] = 1

      if file_size > int((math.pow(1024, 2) * MAX_FILE_SIZE_IN_MB)):
        file_dict['file_author'] = author_name
        file_dict['file_id'] = row['FileID']
        stats['exceeds_file_size_limit_count'] += 1
        stats['exceeds_file_size_limit'].append(file_dict)

  statistics = json.dumps(stats, indent=4)
  file = open("export/statistics.json","w")
  file.write(statistics)
  file.close()
  return result

def copy_files(data):
  global MAX_FILE_SIZE_IN_MB
  print('\nCopying files from moodle data dir to working directory export:')
  for author_key in data:
    for course_id, course_value in data[author_key]['courses'].items():
      if author_key == None:
        author_key = "unknown"

      try:
        print('Creating export directory for ' + author_key)
        Path("export/" + author_key + "/" + slugify_str(course_value['name'])).mkdir(parents=True)
      except:
        print('There was an error creating the export directory for ' + author_key + '.\n')

      for single_file in course_value['files']:
        filepath = single_file['filepath']
        if single_file['filesize'] <= int((math.pow(1024, 2) * MAX_FILE_SIZE_IN_MB)) or MAX_FILE_SIZE_IN_MB == 0:
          try:
            dest = "export/" + author_key + "/" + slugify_str(course_value['name']) + "/" + single_file['filename']
            print('Copying: ' + filepath + ' to ' + dest)
            copy(filepath, dest)
            time.sleep(2)
          except:
            print('There was an error copying file: ' + filepath + '\n')
        else:
          print('File "' + single_file['filename'] + '" exceeds max file size of: ' + str(MAX_FILE_SIZE_IN_MB) + 'MB')

def slugify_str(name):
  return str(re.sub(r"[^a-zA-Z0-9_-]","_", str(name)))

if __name__ == '__main__':
  try:
    Path("export/").mkdir()
  except:
    print("There already is a folder called 'export'")

  try:
    connection = pymysql.connect(host=DB_HOST,
                                user=DB_USER,
                                password=DB_PASS,
                                db=DB_NAME,
                                charset='utf8mb4',
                                cursorclass=pymysql.cursors.DictCursor)
  except:
    print('\nAn error occured while trying to connect to database. Please check credentials.\n')

  if COURSE_IDS != None:
    COURSE_IDS = get_courses(connection)

  filelist = get_files(connection, COURSE_IDS)
  json_file_data = json.dumps(filelist, indent=4)
  file = open("export/file_export.json","w")
  file.write(json_file_data)
  file.close()
  if COPY_FILES == True:
    copy_files(filelist)

  if 'connection' in vars():
    connection.close()

