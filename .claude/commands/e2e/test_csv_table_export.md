# E2E Test: CSV Table & Query Result Export

Test one-click CSV export of tables and query results in the Natural Language SQL Interface application.

## User Story

As a data analyst
I want to download tables and query results as CSV files with one click
So that I can analyze, share, or archive my data outside the application

## Test Steps

1. Navigate to the `Application URL`
2. Take a screenshot of the initial state
3. **Verify** the page title is "Natural Language SQL Interface"
4. Click the "Upload Data" button to open the upload modal
5. Click the "Users Data" sample button to load sample users data
6. **Verify** a table named `users` appears in the Available Tables section
7. **Verify** a download button (download icon) appears in the `users` table header directly to the left of the `×` (remove) icon
8. Take a screenshot showing the table download button
9. Start waiting for a browser download event, then click the `users` table download button
10. **Verify** a CSV download is initiated (a download event fires; suggested filename is `users.csv`) with no error shown
11. Enter the query: "Show me all users from the users table"
12. Click the Query button
13. **Verify** the query results appear and the SQL translation is displayed
14. **Verify** a download button (download icon) appears in the Query Results header directly to the left of the "Hide" button
15. Take a screenshot showing the results download button
16. Start waiting for a browser download event, then click the results download button
17. **Verify** a CSV download is initiated (a download event fires; suggested filename is `query_results.csv`) with no error shown

## Success Criteria
- The `users` table header shows a download button directly to the left of the `×` icon
- Clicking the table download button initiates a `users.csv` download
- The Query Results header shows a download button directly to the left of the "Hide" button
- Clicking the results download button initiates a `query_results.csv` download
- No errors are displayed during either download
- 3 screenshots are taken (initial state, table download button, results download button)
