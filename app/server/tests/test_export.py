"""
Tests for CSV export functionality (table export and query results export).
"""

import csv
import io
import sqlite3
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import server
from server import app, rows_to_csv


@pytest.fixture
def test_db():
    """Create an in-memory test database with sample data and patch connections.

    Both ``server.sqlite3.connect`` (used by the table-export endpoint) and
    ``core.sql_processor.sqlite3.connect`` (used by the results-export endpoint)
    are patched to return the same in-memory connection.
    """
    # check_same_thread=False because TestClient runs handlers in a worker thread
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            email TEXT
        )
    ''')

    cursor.execute("INSERT INTO users (name, age, email) VALUES ('John', 25, 'john@example.com')")
    cursor.execute("INSERT INTO users (name, age, email) VALUES ('Jane', 30, NULL)")
    # A value containing a comma, quote and newline to exercise CSV quoting
    cursor.execute("INSERT INTO users (name, age, email) VALUES ('O''Brien, Jr.\nII', 40, 'a@b.co')")

    cursor.execute('CREATE TABLE empty_table (id INTEGER PRIMARY KEY, label TEXT)')

    conn.commit()

    with patch('server.sqlite3.connect', return_value=conn), \
         patch('core.sql_processor.sqlite3.connect', return_value=conn):
        yield conn

    conn.close()


@pytest.fixture
def client():
    return TestClient(app)


class TestRowsToCsv:

    def test_header_and_rows(self):
        columns = ['id', 'name']
        rows = [{'id': 1, 'name': 'John'}, {'id': 2, 'name': 'Jane'}]
        result = rows_to_csv(columns, rows)

        parsed = list(csv.reader(io.StringIO(result)))
        assert parsed[0] == ['id', 'name']
        assert parsed[1] == ['1', 'John']
        assert parsed[2] == ['2', 'Jane']

    def test_none_rendered_as_empty(self):
        result = rows_to_csv(['a', 'b'], [{'a': None, 'b': 'x'}])
        parsed = list(csv.reader(io.StringIO(result)))
        assert parsed[1] == ['', 'x']

    def test_special_characters_quoted(self):
        result = rows_to_csv(['v'], [{'v': 'a,b"c\nd'}])
        parsed = list(csv.reader(io.StringIO(result)))
        # csv.reader round-trips the quoted value back to the original
        assert parsed[1] == ['a,b"c\nd']

    def test_empty_rows_header_only(self):
        result = rows_to_csv(['a', 'b'], [])
        parsed = list(csv.reader(io.StringIO(result)))
        assert parsed == [['a', 'b']]


class TestExportTable:

    def test_export_existing_table(self, client, test_db):
        response = client.get('/api/export/table/users')

        assert response.status_code == 200
        assert response.headers['content-type'].startswith('text/csv')
        assert response.headers['content-disposition'] == 'attachment; filename="users.csv"'

        parsed = list(csv.reader(io.StringIO(response.text)))
        assert parsed[0] == ['id', 'name', 'age', 'email']
        assert len(parsed) == 4  # header + 3 rows
        # NULL email rendered as empty string
        assert parsed[2] == ['2', 'Jane', '30', '']

    def test_export_empty_table_header_only(self, client, test_db):
        response = client.get('/api/export/table/empty_table')

        assert response.status_code == 200
        parsed = list(csv.reader(io.StringIO(response.text)))
        assert parsed == [['id', 'label']]

    def test_export_missing_table_returns_404(self, client, test_db):
        response = client.get('/api/export/table/nonexistent')
        assert response.status_code == 404

    def test_export_invalid_identifier_returns_400(self, client, test_db):
        # A SQL-injection style identifier is rejected before any query runs
        response = client.get('/api/export/table/users;DROP')
        assert response.status_code == 400


class TestExportResults:

    def test_export_valid_select(self, client, test_db):
        response = client.post('/api/export/results', json={'sql': 'SELECT id, name FROM users WHERE age > 25'})

        assert response.status_code == 200
        assert response.headers['content-type'].startswith('text/csv')
        assert response.headers['content-disposition'] == 'attachment; filename="query_results.csv"'

        parsed = list(csv.reader(io.StringIO(response.text)))
        assert parsed[0] == ['id', 'name']
        names = [row[1] for row in parsed[1:]]
        assert 'Jane' in names
        assert 'John' not in names  # John is 25, not > 25

    def test_export_dangerous_sql_returns_400(self, client, test_db):
        response = client.post('/api/export/results', json={'sql': 'DROP TABLE users'})
        assert response.status_code == 400

    def test_export_invalid_sql_returns_400(self, client, test_db):
        response = client.post('/api/export/results', json={'sql': 'SELECT * FROM nonexistent_table'})
        assert response.status_code == 400
