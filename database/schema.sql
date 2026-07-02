-- ============================================================================
-- database/schema.sql
-- ----------------------------------------------------------------------------
-- DATABASE SCHEMA (DDL) for the Library Management System — Microsoft SQL Server.
--
-- Run this ONCE (e.g. in SSMS or Azure Data Studio) to create the database
-- and its three tables. The script is RE-RUNNABLE: it drops existing tables
-- first, so you can reset the schema during development without errors.
--
-- Tables:
--   Books        - the catalog of books you own
--   Borrowers    - friends who borrow books
--   Transactions - the borrowing log (the heart of the system).
--                  ReturnDate IS NULL => the book is currently out.
--                  Rows are never deleted -> preserves complete history.
--
-- Relationships:
--   Books (1) --< Transactions >-- (1) Borrowers
--   Foreign keys guarantee you cannot record a transaction for a
--   non-existent book or borrower.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1. CREATE THE DATABASE (only if it does not already exist)
-- ----------------------------------------------------------------------------
IF NOT EXISTS (SELECT 1 FROM sys.databases WHERE name = N'LibraryDB')
BEGIN
    CREATE DATABASE LibraryDB;
END;
GO

USE LibraryDB;
GO


-- ----------------------------------------------------------------------------
-- 2. DROP EXISTING TABLES (child first, because of the foreign keys)
--    Lets the script be run repeatedly during development.
-- ----------------------------------------------------------------------------
IF OBJECT_ID('dbo.Transactions', 'U') IS NOT NULL DROP TABLE dbo.Transactions;
IF OBJECT_ID('dbo.Books',        'U') IS NOT NULL DROP TABLE dbo.Books;
IF OBJECT_ID('dbo.Borrowers',    'U') IS NOT NULL DROP TABLE dbo.Borrowers;
GO


-- ----------------------------------------------------------------------------
-- 3. BOOKS TABLE
--    The catalog of books you own.
-- ----------------------------------------------------------------------------
CREATE TABLE dbo.Books
(
    -- BookID is a HIDDEN internal primary key: auto-generated, never entered
    -- by the user and never shown in the UI. It exists so the Transactions
    -- table can reliably reference a specific book (titles are not unique).
    BookID        INT            IDENTITY(1,1) NOT NULL,   -- auto-incrementing PK
    Title         NVARCHAR(200)  NOT NULL,                 -- required
    Author        NVARCHAR(150)  NULL,
    Category      NVARCHAR(50)   NULL,
    -- (ISBN intentionally omitted — not needed for a domestic library.)
    PurchaseDate  DATE           NULL,
    Status        NVARCHAR(20)   NOT NULL
                                 CONSTRAINT DF_Books_Status DEFAULT ('Available'),
    Remarks       NVARCHAR(500)  NULL,

    -- Primary key ------------------------------------------------------------
    CONSTRAINT PK_Books PRIMARY KEY (BookID),

    -- A book can only be in one of these known states -----------------------
    CONSTRAINT CK_Books_Status
        CHECK (Status IN ('Available', 'Issued', 'Lost', 'Removed'))
);
GO


-- ----------------------------------------------------------------------------
-- 4. BORROWERS TABLE
--    Friends who borrow your books.
-- ----------------------------------------------------------------------------
CREATE TABLE dbo.Borrowers
(
    -- BorrowerID is a HIDDEN internal primary key (auto-generated, never shown
    -- in the UI) so Transactions can reference a specific borrower.
    BorrowerID  INT            IDENTITY(1,1) NOT NULL,     -- auto-incrementing PK
    Name        NVARCHAR(100)  NOT NULL,                   -- required
    Phone       NVARCHAR(20)   NULL,
    Email       NVARCHAR(100)  NULL,
    Address     NVARCHAR(250)  NULL,
    -- Soft-delete flag: removing a borrower sets this to 0 instead of deleting
    -- the row, so borrowing history (in Transactions) is never lost.
    IsActive    BIT            NOT NULL
                               CONSTRAINT DF_Borrowers_IsActive DEFAULT (1),

    -- Primary key ------------------------------------------------------------
    CONSTRAINT PK_Borrowers PRIMARY KEY (BorrowerID),

    -- Light sanity check on email format (only when an email is supplied) ----
    CONSTRAINT CK_Borrowers_Email
        CHECK (Email IS NULL OR Email LIKE '%_@_%._%')
);
GO


-- ----------------------------------------------------------------------------
-- 5. TRANSACTIONS TABLE
--    One row per issue event; updated (not deleted) on return.
--    This is the core record that answers "who has which book, since when?".
-- ----------------------------------------------------------------------------
CREATE TABLE dbo.Transactions
(
    TransactionID       INT            IDENTITY(1,1) NOT NULL,  -- auto-incrementing PK
    BookID              INT            NOT NULL,                -- FK -> Books
    BorrowerID          INT            NOT NULL,                -- FK -> Borrowers
    IssueDate           DATE           NOT NULL
                                       CONSTRAINT DF_Trans_IssueDate DEFAULT (CAST(GETDATE() AS DATE)),
    ExpectedReturnDate  DATE           NOT NULL,                -- due date
    ReturnDate          DATE           NULL,                    -- NULL => still out
    Status              NVARCHAR(20)   NOT NULL
                                       CONSTRAINT DF_Trans_Status DEFAULT ('Issued'),
    Remarks             NVARCHAR(500)  NULL,

    -- Primary key ------------------------------------------------------------
    CONSTRAINT PK_Transactions PRIMARY KEY (TransactionID),

    -- Foreign keys: cannot reference a non-existent book or borrower --------
    -- NO ACTION on delete: preserves history and prevents accidental loss of
    -- transaction records if someone tries to delete a book/borrower.
    CONSTRAINT FK_Trans_Book
        FOREIGN KEY (BookID)     REFERENCES dbo.Books (BookID)
        ON UPDATE NO ACTION ON DELETE NO ACTION,
    CONSTRAINT FK_Trans_Borrower
        FOREIGN KEY (BorrowerID) REFERENCES dbo.Borrowers (BorrowerID)
        ON UPDATE NO ACTION ON DELETE NO ACTION,

    -- A transaction can only be in one of these known states ----------------
    CONSTRAINT CK_Trans_Status
        CHECK (Status IN ('Issued', 'Returned', 'Overdue')),

    -- The due date can't be earlier than the issue date ---------------------
    CONSTRAINT CK_Trans_ExpectedDate
        CHECK (ExpectedReturnDate >= IssueDate),

    -- If returned, the return date can't be earlier than the issue date -----
    CONSTRAINT CK_Trans_ReturnDate
        CHECK (ReturnDate IS NULL OR ReturnDate >= IssueDate)
);
GO


-- ----------------------------------------------------------------------------
-- 6. HELPER INDEXES
--    Speed up the most common lookups: joins on the foreign keys and the
--    "which books are currently out?" query (ReturnDate IS NULL).
-- ----------------------------------------------------------------------------
CREATE INDEX IX_Transactions_BookID     ON dbo.Transactions (BookID);
CREATE INDEX IX_Transactions_BorrowerID ON dbo.Transactions (BorrowerID);
CREATE INDEX IX_Transactions_Active     ON dbo.Transactions (ReturnDate) WHERE ReturnDate IS NULL;
GO

-- ============================================================================
-- End of schema. Next: repositories in database/ will run INSERT/SELECT/UPDATE
-- statements against these tables.
-- ============================================================================
