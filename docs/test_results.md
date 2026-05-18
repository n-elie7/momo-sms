# MySQL CRUD Test Results

## Setup
Loaded db_setup.sql via MySQL Workbench. All tables created and seed data
inserted without errors.

Row counts after setup:
- users: 8
- transaction_categories: 9
- raw_sms: 6
- transactions: 6
- transaction_participants: 9
- system_logs: 6

<img src="./screenshots/db-setup_sql_test.jpeg">

## CREATE
Inserted a new airtime transaction with reference 99999000111.

<img src="./screenshots/quick_row_counts_proves_data_is_there.png" />

## READ
Queried all transactions joined with category and participants.

<img src="./screenshots/read_test_screenshot.png" />

## UPDATE
Marked the cash power transaction (ref 14103506143) as reversed.

<img src="./screenshots/update_test_screenshot.png" />

## DELETE
Removed the test airtime transaction. SELECT confirms it's gone.

<img src="./screenshots/delete_test_result.png" />

## Conclusion
All CRUD operations succeeded. Foreign keys, CHECK constraints, and indexes
are working as designed. The schema is ready for the ETL pipeline.
