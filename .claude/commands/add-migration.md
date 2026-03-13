Create a new numbered SQL migration for Sahayakan. Description: "$ARGUMENTS"

Steps:

1. List existing migrations in `infrastructure/db/migrations/` to determine the next number.
2. Convert the description to a filename-safe format (lowercase, underscores, no special chars). For example, "Add user preferences" becomes "add_user_preferences".
3. Create the migration file at `infrastructure/db/migrations/{NNN}_{description}.sql` where NNN is the zero-padded next number.
4. Add a header comment and placeholder SQL:
   ```sql
   -- Migration: {NNN} - {description}
   -- Created: {date}

   BEGIN;

   -- TODO: Add your migration SQL here

   COMMIT;
   ```
5. Report the created file path and remind the user to:
   - Fill in the SQL
   - Apply it with: `psql -h localhost -p 5433 -U sahayakan -d sahayakan -f infrastructure/db/migrations/{filename}`
