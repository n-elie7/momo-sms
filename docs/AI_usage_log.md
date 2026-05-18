# AI Usage Log — Team ASTRO
**Project:** MoMo SMS Database | **AI Usage Policy Compliance Record**

> **Transparency Notice:** We used AI tools only for permitted purposes syntax checking, grammar proofreading, and MySQL best-practice research with citations. All ERD design, SQL schema logic, entity relationships, business rules, and written explanations were produced entirely by our team. MySQL Workbench was used for testing and validating our schema.

## Interaction Log

| # | Tool | Category | What AI Did | How the Team Used It |
|---|------|----------|-------------|----------------------|
| 1 | Claude | Code Syntax Verification | Checked the syntax of our `CREATE TABLE` statements for errors. | Fixed only the flagged syntax issues. All table designs and column decisions were ours. |
| 2 | Claude | Code Syntax Verification | Verified `FOREIGN KEY ... REFERENCES` clause syntax was correct. | Confirmed syntax only. The relationships were designed by our team from the ERD. |
| 3 | Claude | Code Syntax Verification | Identified a bracket error in a `CHECK` constraint causing a MySQL error. | Fixed the bracket. The business rule itself was our own decision. |
| 4 | Claude | Code Syntax Verification | Confirmed table options (`ENGINE=InnoDB`, `CHARSET=utf8mb4`) were correctly placed. | Confirmation only; no logic was involved. |
| 5 | Claude | Code Syntax Verification | Validated our `INSERT INTO` sample data rows for column/value count mismatches. | Corrected mismatched rows. All sample data values were created by our team. |
| 6 | Claude | Code Syntax Verification | Confirmed our `CREATE INDEX` syntax on transaction columns was valid. | No change needed. The choice of which columns to index was our own. |
| 7 | Claude | MySQL Best-Practice Research | Confirmed `DECIMAL` is preferred over `FLOAT` for storing monetary values. [↗](https://dev.mysql.com/doc/refman/8.0/en/fixed-point-types.html) | Validated our use of `DECIMAL(12,2)` for amount fields; the precision was chosen by our team. |
| 8 | Claude | MySQL Best-Practice Research | Explained the difference between `TIMESTAMP` and `DATETIME` in MySQL 8.0. [↗](https://dev.mysql.com/doc/refman/8.0/en/datetime.html) | Informed our choice of `TIMESTAMP` for `created_at`; the final decision was ours. |
| 9 | Claude | MySQL Best-Practice Research | Summarised best practices for indexing foreign key columns. [↗](https://dev.mysql.com/doc/refman/8.0/en/optimization-indexes.html) | Background reading only. Actual indexes were chosen by our team based on our own queries. |
| 10 | Claude | Grammar / Doc Proofread | Fixed minor typos and punctuation in our README documentation. | Accepted formatting fixes only. All written content and explanations were authored by our team. |

---

*All AI interactions stayed within permitted boundaries. The ERD, schema logic, business rules, Markdown files, and all written content are entirely team-authored. Schema was tested and validated using MySQL Workbench.*
