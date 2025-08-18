# Database Migrations

This directory contains database migration scripts for the Cash Flow Application.

## Overview

Migrations help manage database schema changes over time, ensuring that all environments (development, staging, production) have consistent database structures.

## Migration Files

- `001_initial_schema.py` - Creates all core tables and indexes
- `002_add_audit_fields.py` - Adds audit fields and constraints
- `migrate.py` - Migration runner and CLI tool

## Usage

### Apply All Pending Migrations
```bash
cd migrations
python migrate.py up
```

### Check Migration Status
```bash
python migrate.py status
```

### Rollback Last Migration
```bash
python migrate.py down
```

### Rollback Specific Migration
```bash
python migrate.py down 002_add_audit_fields
```

## Migration Structure

Each migration file should have:
- `up()` function - Applies the migration
- `down()` function - Rolls back the migration (optional)
- Descriptive docstring explaining the changes

## Creating New Migrations

1. Create a new file with format: `XXX_description.py`
2. Implement `up()` and `down()` functions
3. Test the migration thoroughly
4. Run `python migrate.py up` to apply

## Best Practices

- Always backup your database before running migrations
- Test migrations on a copy of production data
- Keep migrations small and focused
- Include rollback logic when possible
- Use descriptive names and comments

## Database Schema

The current schema includes:
- `users` - User authentication
- `settings` - Application configuration
- `sales_orders` - Sales order data
- `cash_out` - Cash outflow transactions
- `costs` - One-time costs
- `recurring_costs` - Recurring cost items
- `payment_schedule` - Payment scheduling
- `integrations` - External integrations
- `audit_log` - Change tracking
- `migrations` - Migration tracking
