# moodle_vg_bild-kunst_erhebung
This script can be used to get a list of files provided by teachers in moodle courses that meet the following criteria:

course ids:
- course has at least 1 user with roleid '5' (student)
- is not contained in one of the excluded category ids

files:
- file is of resource: forum, book, resource, url, quiz, page, lesson, wiki, label or file
- filename is not '.'
- file is contained in course ids from above

## Queries
There are basically two sql queries. The first retrieves the target course ids and the second retrieves
the corresponding files provided by teachers in those courses ins specific resources:

First query:
```
SELECT c.id as CourseId, c.fullname as Coursename, cat.name as Categoryname, COUNT(ra.roleid) as ActiveUsers 
FROM course c
LEFT OUTER JOIN context cx ON c.id = cx.instanceid
LEFT OUTER JOIN role_assignments ra ON cx.id = ra.contextid AND ra.roleid = '5'
INNER JOIN course_categories cat ON cat.id = c.category
WHERE c.visible = 1 AND cat.id NOT IN ({EXCLUDE_CATEGORY_IDS})
GROUP BY c.id
HAVING activeusers > 0;
```

Second query:
```
SELECT cm.id AS ModuleID, cm.course AS CourseID, cm.module AS Module, mdl.name AS ModuleType,
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
END AS Link, f.id AS FileID, f.filepath AS FilePath, f.filename as FileName, CONCAT('{FILE_DIR}/', SUBSTRING(f.contenthash, 1, 2), '/', SUBSTRING(f.contenthash, 3, 2), '/', f.contenthash) AS FileSystemPath, f.userid AS FileUserID, f.filesize as FileSize, f.mimetype as FileMimeType, f.author AS FileAuthor, f.timecreated as TimeCreated, f.timemodified AS TimeModified
FROM {DB_PREF}course_modules AS cm
INNER JOIN {DB_PREF}context AS ctx ON ctx.contextlevel = 70 AND ctx.instanceid = cm.id
INNER JOIN {DB_PREF}modules AS mdl ON cm.module = mdl.id
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
WHERE (f.id IS NOT NULL AND f.filename <> '.') AND mdl.name IN ('forum', 'book', 'resource', 'url', 'quiz', 'page', 'lesson', 'label', 'wiki') AND cm.course IN ({COURSE_IDS_STR}) ORDER BY CourseID ASC;
```

Corresponding variables ``{VAR}`` will get populated with ``.env`` variables.

## Copying
This script gets all files (or a specified random sample) and copies them into the working 
directory sorted by author and course name. The script can select a random sample size 
as well as a max_file_size that should get copied.
```
──export
  ├──author name
  │  ├──course name
  │  │  ├──file 1
  │  │  └──file 2
  │  └──course name
  │     └──file 1
  ├──author name
  │  └──course name
  │     └──file 1
  ...
```

## Statistics
Moreover this script provides some statistics about mime-types and file, author and course counts.

## Usage
This script is used in a python virtualenv. Inside the virtual environment all
requirements can be installed via ``pip install -r requirements.txt``.
Afterwards the ``.env-sample`` has to be copied to ``.env`` and at least 
provide the following environment variables:
- DB_HOST
- DB_NAME
- DB_USER
- DB_PASS
- FILE_DIR (This is the corresponding filedir on the server e.g. "/data/moodledata/filedir" without trailing slash)
Finally run ``python moodle_vg-bild-kunst_erhebung.py``

Optionally you can select a random sample of size x in percent or stop the script from copying any
files at all.
- RANDOM_SAMPLE
- SAMPLE_SIZE
- COPY_FILES
- MAX_FILE_SIZE_IN_MB

Be aware that this script requires permissions for the moodle data directory to copy files! Moreover the script
can potentially slow down server performance dramatically during the copy process.

## Use at your own risk
This script is provided without any guarantee to work. It works for me and it's certainly not 
perfect but it got the job done for me. So please use at own risk.