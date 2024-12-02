import sqlite3

DB_PATH="codebaseschema.db"

def setUpDataBase(dbpath):
    conn=sqlite3.connect(dbpath)
    cursor=conn.cursor()
    fileQuery="""
                create table if not exists files(
                id integer primary key autoincrement,
                filename text,
                filepath text,
                filetype text
                )        
"""

    metadataQuery="""
        create table if not exists metadata(
        id integer primary key autoincrement,
        fileId integer,
        name text,
        type text,
        codecontent text,
        docstatus integer,
        docContent text,
        foreign key (fileId) references files(id)
        )        
"""

    referencesQuery="""
            create table if not exists referencesTable(
            id1 integer,
            id2 integer,
            primary key (id1,id2),
            foreign key (id1) references metadata(id),
            foreign key (id2) references metadata(id)
            )        
"""
    cursor.execute(fileQuery)
    cursor.execute(metadataQuery)
    cursor.execute(referencesQuery)
    conn.commit()
    conn.close()

def connect_db(db_name='codebaseschema.db'):
    return sqlite3.connect(db_name)

def insert_file(conn, filename, filepath, filetype):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO files (filename, filepath, filetype)
        VALUES (?, ?, ?)
    ''', (filename, filepath, filetype))
    conn.commit()
    return cursor.lastrowid  # Return the ID of the newly inserted file

def insert_metadata(conn, fileId, name, type, codecontent, docstatus, docContent):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO metadata (fileId, name, type, codecontent, docstatus, docContent)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (fileId, name, type, codecontent, docstatus, docContent))
    conn.commit()
    return cursor.lastrowid  # Return the ID of the newly inserted metadata

def insert_reference(conn, id1, id2):
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO referencesTable (id1, id2)
        VALUES (?, ?)
    ''', (id1, id2))
    conn.commit()

def get_file_id(conn, filepath):
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM files WHERE filepath = ?', (filepath,))
    result = cursor.fetchone()
    return result[0] if result else None