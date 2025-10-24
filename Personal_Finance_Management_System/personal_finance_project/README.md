# Personal Finance Management System

A web-based application designed to help users manage their finances by tracking income, expenses, setting savings goals, and analyzing financial data through graphical representations. Admins have the ability to manage users and oversee system-wide analytics.

---

## Features

### User Features:
- **User Login**: Users can log into their personal accounts.
- **Dashboard**: Displays an overview of income vs. expenses.
- **Set Savings Goals**: Users can set and track personal savings goals (e.g., saving ₹10,000 for a phone).
- **Upload Bank Statements**: Users can upload CSV bank statements, which are parsed and stored in the system.
- **Graphical Analysis**: Visual representation of income and expenses using bar charts and pie charts.

### Admin Features:
- **Admin Login**: Admins can log into the system to access administrative tools.
- **User Management**: Admins can manage user accounts (e.g., view, delete, or modify users).
- **System-wide Analytics**: Admins can view financial statistics for all users, including pie charts for spending categories.

### Reminder System:
- **Email Notifications**: The system sends email reminders for upcoming bills or savings milestones.

---

## Tech Stack
- **Backend**: Python (Flask)
- **Database**: MySQL
- **Frontend**: HTML, CSS, JavaScript (Chart.js)
- **File Parsing**: `pdfplumber` (for PDF bank statement parsing)
- **Emailing**: SMTP (via Flask)

---

## Setup Instructions

### Prerequisites:
- Python 3.x
- MySQL
- A Google email account (for email notifications)

### 1. Clone the Repository
Clone the project to your local machine:

```bash
git clone https://github.com/yourusername/personal-finance-management.git
cd personal-finance-management
