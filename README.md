# Momo-SMS-API

Scrum Board: [Scrum Board](https://aluteam-6.atlassian.net/jira/software/projects/SCRUM/boards/1?atlOrigin=eyJpIjoiZDBkNDVlMmU5ZDk4NDAxY2EzMTU3ZmRmZWE5YTdjY2UiLCJwIjoiaiJ9)

## Overview

In MoMo SMS API data will be processed in XML format, clean and categorize the data, store it in a relational database, and build a frontend interface to analyze and visualize the data.

## Team Astro

### Members:

- Niyubwayo Irakoze Elie
- Iradukunda Suwafa
- Kaliza Sabrina

## Architecture Diagram
<img src="./architecture.JPG">

## AI Usage Log
This section lists how we used AI through out this project

We used AI to:

- Analyze XML data structure to get the big picture of database we are about to design
- Write comments on columns we specified in the schema
- To research on MySQL best practices like InnoDB, there was no need to specify it explicitly. That nowadays it comes as pre-configured engine ready to use
- check grammar and syntax checking in documentation file like README and erd_design_justification markdown file


## DATABASE DOCUMENTATION
This section explains the entities and relationships between them.


The MoMo SMS pipeline database is built on six relational tables in MySQL: users, transaction_categories, raw_sms, transactions, transaction_participants, and system_logs. The schema captures every stage of SMS processing, from raw ingestion to parsed financial records. Foreign key constraints enforce referential integrity across tables, while the transaction_participants junction table resolves the many-to-many relationship between users and transactions. All monetary values use DECIMAL(15,2) to prevent floating-point errors, and timestamps are stored in UTC DATETIME. The JSON representation mirrors this structure for API responses, replacing foreign key integers with nested objects and junction table rows with arrays, ensuring clients receive complete, readable data in a single request. 